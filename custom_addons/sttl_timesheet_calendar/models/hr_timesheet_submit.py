# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


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
        for rec in self.line_ids:
            if rec.total_hrs < 45:
                raise UserError(_("%s worked hours less-then 45, So you can't lock timesheets.")% rec.employee_id.name)
            rec.state='lock'
        
    def unlock(self):
        for rec in self.line_ids:
            rec.unlink()
            
        
class HrTimesheetSubmitLine(models.Model):
    _name = "hr.timesheet.submit.line"
    _description = "Submit Timesheet"
    _order = "id asc"
    
    @api.model
    def default_get(self, field_list):
        result = super(HrTimesheetSubmitLine, self).default_get(field_list)
        if not self.env.context.get('default_employee_id') and 'employee_id' in field_list:
            result['employee_id'] = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1).id
        return result
    
    def _domain_employee_id(self):
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_approver'):
            return [('user_id', '=', self.env.user.id)]
        return []
    
    # def _domain_submit_id(self):
    #     submit_ids = self.env['hr.timesheet.submit'].search([]).line_ids.filtered(lambda a: a.employee_id.id == self.employee_id.id)
    #     return [('id', 'not in', submit_ids.ids)]
    
    employee_id = fields.Many2one('hr.employee', "Employee", domain=_domain_employee_id)
    submit_id = fields.Many2one('hr.timesheet.submit',string='Submission Duration')
    total_hrs = fields.Float('Worked Hours (HH:MM)', compute='_compute_total_hours')
    state = fields.Selection([('unlock','Unlock'),('lock','Lock')],'Status',default='unlock')
    
    @api.depends('employee_id','submit_id')
    def _compute_total_hours(self):
        for rec in self:
            worked_hours_ids = self.env['account.analytic.line'].search([('employee_id','=',rec.employee_id.id),('date','>=',rec.submit_id.from_date),('date','<=',rec.submit_id.to_date)])
            if worked_hours_ids:
                rec.total_hrs = sum([x.unit_amount for x in worked_hours_ids])
            else:
                rec.total_hrs = 0
                
    @api.model
    def create(self, vals):
        lines = super(HrTimesheetSubmitLine, self).create(vals)
        submit_ids = self.env['hr.timesheet.submit'].search([]).line_ids.filtered(lambda a: a.employee_id.id == lines.employee_id.id and a.state=='lock')
        if submit_ids:
            raise UserError(_("You are already locked this week timesheets."))
        if lines.total_hrs < 45:
            raise UserError(_("Your worked hours less-then 45, So you can't lock timesheets."))
        return lines
        
    def lock(self):
        self.state='lock'
        
    def unlock(self):
        self.unlink()
        
class HrTimesheetStatus(models.Model):
    _name = "hr.timesheet.status"
    _description = "Timesheet Status"
    _order = "id asc"
    
    name = fields.Char('Name', required=True)
    sequence = fields.Integer('Sequence')
    
        