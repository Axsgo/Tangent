# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import xlwt
import base64
from io import BytesIO
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT


class ProjectProfitReport(models.TransientModel):
    _name = "project.profit.report"
    _description = "Project Profit Report"
    
    project_ids = fields.Many2many('project.project',string='Project')
    excel_file = fields.Binary(string='Report File')
    report_type = fields.Selection([('hrs','Stage wise hours'),('cost','Stage wise cost')],'Report type',default='hrs')
    
    def action_xls_report(self):
        workbook = xlwt.Workbook(encoding="UTF-8")
        format1 = xlwt.easyxf('font:bold True,name Calibri;align: horiz center;borders: left thin, right thin, top thin, bottom thin;')
        format2 = xlwt.easyxf('font:bold True,name Calibri;align: horiz left;borders: left thin, right thin, top thin, bottom thin;')
        format3 = xlwt.easyxf('font:bold True,name Calibri;align: horiz right;borders: left thin, right thin, top thin, bottom thin;')
        format4 = xlwt.easyxf('font:name Calibri;align: horiz left;borders: left thin, right thin, top thin, bottom thin;')
        format5 = xlwt.easyxf('font:name Calibri;align: horiz right;borders: left thin, right thin, top thin, bottom thin;')
        format6 = xlwt.easyxf('font:bold True,name Calibri;align: horiz center;borders: left thin, right thin, top thin, bottom thin;')
        if self.report_type == 'hrs':
            sheet = workbook.add_sheet('Stage wise hours report')
            for r in range(20):
                sheet.col(r).width = int(20*260)
            i=0
            for project in self.project_ids:
                sheet.write_merge(i, i, 0, 7, project.name, format6)
                i+=1;k=i;l=2;x=i+1;y=2;tot_hrs=0
                sheet.write(k, 0, 'Stage', format1)
                sheet.write(k, 1, 'Total Hours', format1)
                k+=1
                timesheet_ids = self.env['account.analytic.line'].search([('project_id','=',project.id)])
                employee_ids = self.env['hr.employee'].search([('id','in',timesheet_ids.mapped('employee_id').ids)],order='name asc')
                for line in project.stage_cost_ids:
                    sheet.write(k, 0, line.stage_id.name, format2)
                    k+=1
                for employee in employee_ids:
                    sheet.write(i, l, employee.name, format4)
                    l+=1
                for line in project.stage_cost_ids:
                    z=y;tot=0
                    for employee in employee_ids:
                        time_id = self.env['account.analytic.line'].search([('project_id','=',project.id),('status_id','=',line.stage_id.id),('employee_id','=',employee.id)])    
                        sheet.write(x, z, time_id.unit_amount, format5)
                        tot += time_id.unit_amount
                        z+=1
                    tot_hrs += tot
                    sheet.write(x, 1, tot, format3)
                    x+=1
                sheet.write(x, 1, tot_hrs, format3)
                i=x+2
        else:
            sheet = workbook.add_sheet('Stage wise cost report')
            for r in range(20):
                sheet.col(r).width = int(20*260)
            i=0
            for project in self.project_ids:
                sheet.write_merge(i, i, 0, 7, project.name, format6)
                i+=1;k=i;l=3;x=i+1;y=3;tot_est=0;tot_amt=0
                sheet.write(k, 0, 'Stage', format1)
                sheet.write(k, 1, 'Est Amount', format1)
                sheet.write(k, 2, 'Total Amount', format1)
                k+=1
                timesheet_ids = self.env['account.analytic.line'].search([('project_id','=',project.id)])
                employee_ids = self.env['hr.employee'].search([('id','in',timesheet_ids.mapped('employee_id').ids)],order='name asc')
                for line in project.stage_cost_ids:
                    sheet.write(k, 0, line.stage_id.name, format2)
                    sheet.write(k, 1, line.amount, format3)
                    tot_est += line.amount
                    k+=1
                for employee in employee_ids:
                    sheet.write(i, l, employee.name, format4)
                    l+=1
                for line in project.stage_cost_ids:
                    z=y;tot=0
                    for employee in employee_ids:
                        time_id = self.env['account.analytic.line'].search([('project_id','=',project.id),('status_id','=',line.stage_id.id),('employee_id','=',employee.id)])    
                        sheet.write(x, z, time_id.unit_amount*employee.timesheet_cost, format5)
                        tot += time_id.unit_amount*employee.timesheet_cost
                        z+=1
                    tot_amt += tot
                    sheet.write(x, 2, tot, format3)
                    x+=1
                sheet.write(x, 1, tot_est, format3)
                sheet.write(x, 2, tot_amt, format3)
                i=x+2
        fp = BytesIO()
        workbook.save(fp)     
        self.write({'excel_file': base64.encodestring(fp.getvalue())})
        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=project.profit.report&field=excel_file&download=true&id=%s&filename=%s' % (self.id, 'Project hours/profit report.xls'),
            'target': 'new',
        }
            