# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, time
import pytz
from dateutil.rrule import rrule, DAILY
from dateutil.relativedelta import relativedelta


class HrTimesheetSubmit(models.Model):
    _name = "hr.timesheet.submit"
    _description = "Submit Timesheet"
    _order = "id asc"
    
    name = fields.Char('Time sheet submission', default='/')
    from_date = fields.Date("From Date", required=True)
    to_date = fields.Date("To Date", required=True)
    total_hrs = fields.Float('Worked Hours (HH:MM)', compute='_compute_total_hours')
    avg_hrs = fields.Float('Average Hours (HH:MM)', compute='_compute_total_hours')
    line_ids = fields.One2many('hr.timesheet.submit.line','submit_id',string='Submission List')
    
    @api.depends('line_ids.total_hrs')
    def _compute_total_hours(self):
        for rec in self:
            if self.line_ids:
                rec.total_hrs = sum([x.total_hrs for x in self.line_ids])
                rec.avg_hrs = (rec.total_hrs/len(self.line_ids))
            else:
                rec.total_hrs = 0
                rec.avg_hrs = 0
    
    @api.model
    def create(self, vals):
        lines = super(HrTimesheetSubmit, self).create(vals)
        lines.name = lines.from_date.strftime("%d/%m/%Y")+' - '+lines.to_date.strftime("%d/%m/%Y")
        return lines
    
    def write(self, vals):
        res = super(HrTimesheetSubmit, self).write(vals)
        if 'from_date' in vals or 'to_date' in vals:
            self.name = self.from_date.strftime("%d/%m/%Y")+' - '+self.to_date.strftime("%d/%m/%Y")
        return res
        
    def lock(self):
        for rec in self.line_ids.filtered(lambda a: a.state=='unlock' and a.employee_id.not_required==False):
            if self.env['hr.employee'].search([('date_of_join','>=',self.from_date),('date_of_join','<=',self.to_date),('id','=',rec.employee_id.id)]):
                from_date = rec.employee_id.date_of_join
            else:
                from_date = self.from_date
            leave_days = rec.get_unusual_days(from_date,self.to_date)
            day_count = list(leave_days.values()).count(False)
            if rec.total_hrs < (day_count*self.env.company.timesheet_working_hrs):
                raise UserError(_("%s worked hours less-then %s, So you can't submit timesheets.")% (rec.employee_id.name,str(day_count*self.env.company.timesheet_working_hrs)))
            rec.state='lock'
        
    def unlock(self):
        for rec in self.line_ids:
            rec.state='unlock'
            rec.submit_status='not_submit'
            
    def monthly_submission_master(self):
        for i in range(1,6):
            submit_id = self.env['hr.timesheet.submit'].search([],order='id desc',limit=1)
            from_date = submit_id.to_date+relativedelta(days=1)
            to_date = submit_id.to_date+relativedelta(days=7)
            if from_date.day > 6  or i != 5:
                sub_id = self.env['hr.timesheet.submit'].sudo().create({'from_date':from_date,'to_date':to_date})
                for employee_id in self.env['hr.employee'].search([('not_required','=',False)]):
                    self.env['hr.timesheet.submit.line'].sudo().create({'employee_id': employee_id.id,'submit_id':sub_id.id})
            

class HrTimesheetSubmitLine(models.Model):
    _name = "hr.timesheet.submit.line"
    _description = "Submit Timesheet"
    _order = "employee_id asc,submit_id desc"
    
    employee_id = fields.Many2one('hr.employee', "Employee")
    submit_id = fields.Many2one('hr.timesheet.submit',string='Submission Duration')
    total_hrs = fields.Float('Worked Hours (HH:MM)', compute='_compute_total_hours')
    state = fields.Selection([('unlock','Open'),('lock','Close')],'Timesheet Open/Close',default='unlock')
    submit_status = fields.Selection([('not_submit','Not submitted'),('submit','Submitted')],'Submit Status',default='not_submit')
    
    @api.depends('employee_id','submit_id')
    def _compute_total_hours(self):
        for rec in self:
            worked_hours_ids = self.env['account.analytic.line'].search([('employee_id','=',rec.employee_id.id),('date','>=',rec.submit_id.from_date),('date','<=',rec.submit_id.to_date)])
            if worked_hours_ids:
                rec.total_hrs = sum([x.unit_amount for x in worked_hours_ids])
            else:
                rec.total_hrs = 0
        
    def lock(self):
        if not self.employee_id.not_required:
            if self.env['hr.employee'].search([('date_of_join','>=',self.submit_id.from_date),('date_of_join','<=',self.submit_id.to_date),('id','=',self.employee_id.id)]):
                from_date = self.employee_id.date_of_join
            else:
                from_date = self.submit_id.from_date
            leave_days = self.get_unusual_days(from_date,self.submit_id.to_date)
            day_count = list(leave_days.values()).count(False)
            if self.total_hrs < (day_count*self.env.company.timesheet_working_hrs):
                raise UserError(_("%s worked hours less-then %s, So you can't submit timesheets.")% (self.employee_id.name,str(day_count*self.env.company.timesheet_working_hrs)))
        self.state='lock'
        
    def unlock(self):
        self.state='unlock'
        self.submit_status='not_submit'
        
    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        # Checking the calendar directly allows to not grey out the leaves taken
        # by the employee
        calendar = self.env.user.employee_id.resource_calendar_id
        if not calendar:
            return {}
        tz = pytz.timezone('UTC')
        dfrom = pytz.utc.localize(datetime.combine(fields.Date.from_string(date_from), time.min)).astimezone(tz)
        dto = pytz.utc.localize(datetime.combine(fields.Date.from_string(date_to), time.max)).astimezone(tz)

        works = {d[0].date() for d in calendar._work_intervals_batch(dfrom, dto)[False]}
        return {fields.Date.to_string(day.date()): (day.date() not in works) for day in rrule(DAILY, dfrom, until=dto)}

            
class HrTimesheetSubmitWizard(models.TransientModel):
    _name = "hr.timesheet.submit.wizard"
    _description = "Submit Timesheet"

    @api.model
    def default_get(self, field_list):
        result = super(HrTimesheetSubmitWizard, self).default_get(field_list)
        if not self.env.context.get('default_employee_id') and 'employee_id' in field_list:
            result['employee_id'] = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1).id
        return result
    
    def _domain_employee_id(self):
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_approver'):
            return [('user_id', '=', self.env.user.id)]
        return []
    
    employee_id = fields.Many2one('hr.employee', "Employee", domain=_domain_employee_id)
    submit_id = fields.Many2one('hr.timesheet.submit',string='Submission Duration')
    total_hrs = fields.Float('Worked Hours (HH:MM)', compute='_compute_total_hours')
    
    @api.depends('employee_id','submit_id')
    def _compute_total_hours(self):
        for rec in self:
            worked_hours_ids = self.env['account.analytic.line'].search([('employee_id','=',rec.employee_id.id),('date','>=',rec.submit_id.from_date),('date','<=',rec.submit_id.to_date)])
            if worked_hours_ids:
                rec.total_hrs = sum([x.unit_amount for x in worked_hours_ids])
            else:
                rec.total_hrs = 0
                
    @api.onchange('employee_id')
    def onchange_employee_id(self):
        res = {'domain': {'submit_id': "[('id', 'not in', False)]"}}
        submit_ids = self.env['hr.timesheet.submit.line'].search([('employee_id','=',self.employee_id.id),('submit_status','!=','submit')]).mapped('submit_id') or False
        if self.employee_id and submit_ids:
            res['domain']['submit_id'] = "[('id', 'in', %s)]" % submit_ids.ids
        return res
                
    def lock(self):
        submit_id = self.env['hr.timesheet.submit.line'].search([('employee_id','=',self.employee_id.id),('submit_id','=',self.submit_id.id),('submit_status','=','not_submit')])
        if not submit_id:
            raise UserError(_("You are already submitted this week timesheets."))
        if not self.employee_id.not_required:
            if self.env['hr.employee'].search([('date_of_join','>=',self.submit_id.from_date),('date_of_join','<=',self.submit_id.to_date),('id','=',self.employee_id.id)]):
                from_date = self.employee_id.date_of_join
            else:
                from_date = self.submit_id.from_date
            leave_days = self.get_unusual_days(from_date,self.submit_id.to_date)
            day_count = list(leave_days.values()).count(False)
            if self.total_hrs < (day_count*self.env.company.timesheet_working_hrs):
                raise UserError(_("Your worked hours less-then %s in this week, So you can't submit timesheets.")% (day_count*self.env.company.timesheet_working_hrs))
        submit_id.state='lock'
        submit_id.submit_status='submit'
        
    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        # Checking the calendar directly allows to not grey out the leaves taken
        # by the employee
        calendar = self.env.user.employee_id.resource_calendar_id
        if not calendar:
            return {}
        tz = pytz.timezone('UTC')
        dfrom = pytz.utc.localize(datetime.combine(fields.Date.from_string(date_from), time.min)).astimezone(tz)
        dto = pytz.utc.localize(datetime.combine(fields.Date.from_string(date_to), time.max)).astimezone(tz)

        works = {d[0].date() for d in calendar._work_intervals_batch(dfrom, dto)[False]}
        return {fields.Date.to_string(day.date()): (day.date() not in works) for day in rrule(DAILY, dfrom, until=dto)}


class HrTimesheetStatus(models.Model):
    _name = "hr.timesheet.status"
    _description = "Timesheet Status"
    _order = "sequence asc"
    
    name = fields.Char('Name', required=True)
    sequence = fields.Integer('Sequence')
    project_ids = fields.Many2many("project.project",'allowed_stage_project_rel',string='Projects')
    
