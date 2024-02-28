# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import xlwt
import base64
from io import BytesIO
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT


class HrTimesheetSubmitReport(models.TransientModel):
    _name = "hr.timesheet.submit.report"
    _description = "Submit Timesheet"
    _order = "employee_id asc"
    
    from_date = fields.Date("From Date", required=True)
    to_date = fields.Date("To Date", required=True)
    report_type = fields.Selection([('list','View Employee List'),('xl','Download Excel')],'Report type',default='list')
    submit_status = fields.Selection([('not_submit','Not submitted'),('submit','Submitted')],'Submit Status',default='not_submit')
    line_ids = fields.Many2many('hr.timesheet.submit.line',string='Employee List')
    excel_file = fields.Binary(string='Report File')
    
    @api.onchange('from_date','to_date','submit_status')
    def _onchange_submit_ids(self):
        if self.to_date and self.from_date and self.report_type=='list':
            if self.to_date < self.from_date:
                raise UserError(_("To date should be greater than From date."))
            self.line_ids = False
            # submit_line_ids = self.env['hr.timesheet.submit.line'].search([('submit_id','in',self.submit_ids.ids),('state','=',self.state)])
            submit_ids = []
            submit_ids = self.env['hr.timesheet.submit'].search([]).filtered(lambda a: a.from_date >= self.from_date and a.to_date <= self.to_date).ids
            submit_ids.append(self.env['hr.timesheet.submit'].search([('from_date','<=',self.from_date),('to_date','>=',self.from_date)],limit=1).id)
            submit_ids.append(self.env['hr.timesheet.submit'].search([('to_date','=',self.to_date)],limit=1).id)
            if submit_ids:
                submit_line_ids = self.env['hr.timesheet.submit.line'].search([('submit_id','in',submit_ids),('submit_status','=',self.submit_status)])
                self.line_ids = submit_line_ids.ids
    
    def action_xls_report(self):
        workbook = xlwt.Workbook(encoding="UTF-8")
        format3 = xlwt.easyxf('font:name Calibri;align: horiz center;borders: left thin, right thin, top thin, bottom thin;')
        format4 = xlwt.easyxf('font:name Calibri;align: horiz left;borders: left thin, right thin, top thin, bottom thin;')
        format5 = xlwt.easyxf('font:bold True,name Calibri, height 120;align: horiz left;borders: left thin, right thin, top thin, bottom thin;')
        format6 = xlwt.easyxf('font:bold True,name Calibri;align: horiz center;borders: left thin, right thin, top thin, bottom thin;')
        format7 = xlwt.easyxf('pattern: pattern solid,fore-colour green;borders: left thin, right thin, top thin, bottom thin;')
        format8 = xlwt.easyxf('pattern: pattern solid,fore-colour light_yellow;borders: left thin, right thin, top thin, bottom thin;')
        
        sheet = workbook.add_sheet('Employee timesheet submission report')
        sheet.write(1, 0, 'S NO', format6)
        sheet.write(1, 1, 'Employee Name', format6)
        sheet.col(1).width = int(45*260)
        i=2;j=2;submit_list = []
        submit_list = self.env['hr.timesheet.submit'].search([]).filtered(lambda a: a.from_date >= self.from_date and a.to_date <= self.to_date).ids
        submit_list.append(self.env['hr.timesheet.submit'].search([('from_date','<=',self.from_date),('to_date','>=',self.from_date)],limit=1).id)
        submit_list.append(self.env['hr.timesheet.submit'].search([('from_date','<=',self.to_date),('to_date','>=',self.to_date)],limit=1).id)
        submit_ids = self.env['hr.timesheet.submit'].search([('id','in',submit_list)],order='id asc')
        for sub in submit_ids:
            sheet.write(1, i, sub.name, format5)
            sheet.col(i).width = int(18*260)
            i+=1
        sheet.write_merge(0, 0, 0, i-1, 'Employee Timesheet Submission Report'+' - Week of('+str(self.from_date.strftime('%d-%m-%Y'))+' to '+str(self.to_date.strftime('%d-%m-%Y'))+')', format6)
        employee_ids = self.env['hr.timesheet.submit.line'].search([('submit_id','in',submit_ids.ids)]).mapped('employee_id')
        for employee in employee_ids:
            sheet.write(j, 0, j-1, format3)
            sheet.write(j, 1, employee.name, format4)
            i=2
            for sub in submit_ids:
                line_id = self.env['hr.timesheet.submit.line'].search([('employee_id','=',employee.id),('submit_id','=',sub.id)])
                if line_id.submit_status == 'submit':
                    sheet.write(j, i, '', format7)
                else:
                    sheet.write(j, i, '', format8)
                i+=1
            j+=1   
        fp = BytesIO()
        workbook.save(fp)     
        self.write({'excel_file': base64.encodestring(fp.getvalue())})
        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=hr.timesheet.submit.report&field=excel_file&download=true&id=%s&filename=%s' % (self.id, 'Employee timesheet submission report.xls'),
            'target': 'new',
        }
            