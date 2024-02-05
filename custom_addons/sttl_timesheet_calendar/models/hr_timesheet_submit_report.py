# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrTimesheetSubmitReport(models.TransientModel):
    _name = "hr.timesheet.submit.report"
    _description = "Submit Timesheet"
    _order = "employee_id asc"
    
    from_date = fields.Date("From Date", required=True)
    to_date = fields.Date("To Date", required=True)
    # submit_ids = fields.Many2many('hr.timesheet.submit',string='Submission Duration')
    submit_status = fields.Selection([('not_submit','Not submitted'),('submit','Submitted')],'Submit Status',default='not_submit')
    line_ids = fields.Many2many('hr.timesheet.submit.line',string='Employee List')
    
    @api.onchange('from_date','to_date','submit_status')
    def _onchange_submit_ids(self):
        if self.to_date and self.from_date:
            if self.to_date < self.from_date:
                raise UserError(_("To date should be greater than From date."))
            self.line_ids = False
            # submit_line_ids = self.env['hr.timesheet.submit.line'].search([('submit_id','in',self.submit_ids.ids),('state','=',self.state)])
            submit_ids = []
            submit_ids = self.env['hr.timesheet.submit'].search([]).filtered(lambda a: a.from_date >= self.from_date and a.to_date <= self.to_date).ids
            submit_ids.append(self.env['hr.timesheet.submit'].search([('from_date','<=',self.from_date),('to_date','>=',self.from_date)],limit=1).id)
            submit_ids.append(self.env['hr.timesheet.submit'].search([('from_date','<=',self.to_date),('to_date','>=',self.to_date)],limit=1).id)
            if submit_ids:
                submit_line_ids = self.env['hr.timesheet.submit.line'].search([('submit_id','in',submit_ids),('submit_status','=',self.submit_status)])
                self.line_ids = submit_line_ids.ids
            