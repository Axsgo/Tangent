# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, time
import pytz
from dateutil.rrule import rrule, DAILY
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    
    @api.model
    def default_get(self, field_list):
        result = super(AccountAnalyticLine, self).default_get(field_list)
        result['unit_amount'] = 0.0
        if 'date' in result:
            if not self.env['hr.timesheet.submit'].search([('from_date','<=',result.get('date')),('to_date','>=',result.get('date'))]):
                raise UserError(_("You can not create timesheet for future date"))
            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1).id
            if self.env['hr.timesheet.submit.line'].search([('employee_id','=',employee_id),('submit_id.from_date','<=',result.get('date')),('submit_id.to_date','>=',result.get('date')),('state','=','lock')]):
                result['message'] = "You can not create/update timesheet for this date"
        return result
    
    def _domain_stages(self):
        if self.user_has_groups('ax_groups.admin_user_group'):
            return [('for_admin', '=', True)]
        else:
            return [('for_admin', '!=', True)]
        return []

    # hours = fields.Integer("Duration (Hours)")
    # minutes = fields.Integer("Duration (Minutes)")
    # from_date = fields.Datetime("From Date", default=datetime.now())
    # to_date = fields.Datetime("To Date",readonly=True)
    status_id = fields.Many2one("hr.timesheet.status",'Stages',order='sequence asc', domain=_domain_stages)
    # status_id = fields.Many2one("project.task.type",'Stages',order='sequence asc')
    description = fields.Text('Description')
    message = fields.Text('Message')
    
    @api.onchange('project_id','unit_amount')
    def _onchange_project_unit_amount(self):
        self.name = str(self.project_id.project_no)+' - '+str(self.project_id.name)
        
    @api.onchange('project_id')
    def onchange_project_id(self):
        self.status_id = False
        res = {'domain': {'status_id': "[('id', 'not in', False)]"}}
        status_ids = []
        if self.user_has_groups('ax_groups.admin_user_group'):
            if self.project_id.stage_id:
                status_ids.append(self.env['hr.timesheet.status'].search([('sequence','=',(self.project_id.stage_id.sequence+1))],limit=1).id)
            else:
                status_ids.append(self.env['hr.timesheet.status'].search([('for_admin', '=', True)],order='sequence',limit=1).id)
            res['domain']['status_id'] = "[('id', 'in', %s)]" % status_ids
        else:
            if self.project_id.stage_id:
                status_ids.append(self.env['hr.timesheet.status'].search([('sequence','=',(self.project_id.stage_id.sequence+1))],limit=1).id)
            else:
                status_ids.append(self.env['hr.timesheet.status'].search([('for_admin', '!=', True)],order='sequence',limit=1).id)
            res['domain']['status_id'] = "[('id', 'in', %s)]" % status_ids
        return res
    
    # @api.onchange('hours','minutes')
    # def _onchange_time(self):
    #     hours, minutes = divmod(self.minutes, 60)
    #     self.unit_amount = self.hours+hours+(minutes/100)
    
    # @api.onchange('unit_amount')
    # def _onchange_unit_amount(self):
    #     if self.from_date:
    #         self.to_date = self.from_date+timedelta(hours=self.unit_amount)

    # @api.onchange('name')
    # def _onchange_date(self):
    #     if self.to_date:
    #         self.date = self.to_date.date()
            
    # def write(self, vals):
    #     if 'unit_amount' in vals:
    #         vals.update({'to_date': self.from_date+timedelta(hours=self.unit_amount)})
    #     return super(AccountAnalyticLine, self).write(vals)
    
    @api.model_create_multi
    def create(self, vals_list):
        lines = super(AccountAnalyticLine, self).create(vals_list)
        for res in lines:
            if self.env['hr.timesheet.submit.line'].search([('employee_id','=',res.employee_id.id),('submit_id.from_date','<=',res.date),('submit_id.to_date','>=',res.date),('state','=','lock')]):
                raise UserError(_("You can not create/update timesheet for this date"))
            if res.unit_amount <= 0:
                raise UserError(_("You can not update zero duration timesheet"))
            res.project_id.stage_id = res.status_id.id
        return lines

    def write(self, vals):
        for rec in self:
            if self.env['hr.timesheet.submit.line'].search([('employee_id','=',rec.employee_id.id),('submit_id.from_date','<=',rec.date),('submit_id.to_date','>=',rec.date),('state','=','lock')]):
                raise UserError(_("You can not create/update timesheet for this date"))
        res = super(AccountAnalyticLine, self).write(vals)
        rec.project_id.stage_id = rec.status_id.id
        if rec.unit_amount <= 0:
            raise UserError(_("You can not update zero duration timesheet"))
        return res
    
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
    