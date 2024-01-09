# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
import xlsxwriter
import io
import base64
import itertools
from odoo.exceptions import ValidationError




class timesheet_select(models.TransientModel):
    _name = 'timesheet.select'
    _description = "timesheet select"

    start_date = fields.Date(string="Start date",required=True)
    end_date = fields.Date(string="End Date",required=True)

    employee_ids = fields.Many2many('hr.employee',string="Select employee",required=True)



    def generate_pdf_report(self):

        if self.start_date > self.end_date:
            raise ValidationError(_("Invalid Date !! End date should be greater than the start date"))
        else:
            data_dict = {'id': self.id, 'start_date': self.start_date, 'end_date': self.end_date,
                         'employee_ids': self.employee_ids}
            return self.env.ref('bi_employee_timesheet_report.timesheet_report_id').report_action(self,
                                                                                                  data=data_dict)

    def generate_excel_report(self):

        if self.start_date > self.end_date:
            raise ValidationError(_("Invalid Date !! End date should be greater than the start date"))
        else:
            self.ensure_one()
            file_path = 'timesheet report' + '.xlsx'
            workbook = xlsxwriter.Workbook('/tmp/' + file_path)

            title_format = workbook.add_format(
                {'border': 1, 'bold': True, 'valign': 'vcenter', 'align': 'center', 'font_size': 11,
                 'bg_color': '#D8D8D8'})

            formate_1 = workbook.add_format({'bold': True, 'align': 'center', 'font_size': 11, 'font_color': 'red'})

            record = self.env['account.analytic.line'].search(
                [('employee_id', 'in', self.employee_ids.ids), ('date', '>=', self.start_date),
                 ('date', '<=', self.end_date)])

            sheet = workbook.add_worksheet('Timesheet Report')

            row = 8
            col = 2
            total = 0

            grouped_records = {}
            for rec in record:
                employee_id = rec['employee_id']
                if employee_id in grouped_records:
                    grouped_records[employee_id].append(rec)
                else:
                    grouped_records[employee_id] = [rec]

            sheet.set_column('C:C', 13)
            sheet.set_column('D:E', 25)
            sheet.set_column('E:F', 25)
            sheet.set_column('G:G', 18)

            row_t = 1
            col_t = 4
            sheet.merge_range(row_t, col_t - 1, row_t + 1, col_t + 1, "Timesheet Report", title_format)
            sheet.merge_range(row - 4, 3, row - 4, 5, f' Timesheet Period : From {self.start_date} To {self.end_date}',
                              title_format)

            store_list = []
            for rec in self.env['hr.employee'].search(
                    [('name', 'in', [i.name for i in self.employee_ids])]):
                if rec:
                    store_list.append({'id': rec.id, 'name': rec.name})

            for emp_name in store_list:
                sheet.merge_range(row - 2, 2, row - 2, 3, f" Employee Name : {emp_name['name']}", title_format)
                if emp_name['name'] in [i.name for i in grouped_records]:
                    for employee_id, employee_records in grouped_records.items():

                        if employee_id.name == emp_name['name']:

                            sheet.write(row, 2, 'Date', title_format)
                            sheet.write(row, 3, 'Project', title_format)
                            sheet.write(row, 4, 'Task', title_format)
                            sheet.write(row, 5, 'Description', title_format)
                            sheet.write(row, 6, 'Time Spent(Hours)', title_format)

                            for rec in employee_records:

                                row += 1

                                sheet.write(row, 2, rec.date.strftime("%Y-%m-%d"))
                                sheet.write(row, 3, rec.project_id.name)
                                sheet.write(row, 4, rec.task_id.name)
                                sheet.write(row, 5, rec.name)
                                sheet.write(row, 6, rec.unit_amount)
                                total += rec.unit_amount
                                sheet.write(row + 1, 6, total, title_format)


                            row += 4
                            total = 0
                else:
                    sheet.merge_range(row, 3, row, 5, "No Data Was Found For This Employee In Selected Date", formate_1)
                    row += 4

            workbook.close()
            ex_report = base64.b64encode(open('/tmp/' + file_path, 'rb+').read())

            excel_report_id = self.env['save.ex.report.wizard'].create({"document_frame": file_path,
                                                                        "file_name": ex_report})

            return {
                'res_id': excel_report_id.id,
                'name': 'Files to Download',
                'view_type': 'form',
                "view_mode": 'form',
                'view_id': False,
                'res_model': 'save.ex.report.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }



