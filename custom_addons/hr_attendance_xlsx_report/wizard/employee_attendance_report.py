# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author:  LAJINA KV (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import io
import json
from datetime import datetime, date, time, timedelta
from dateutil.rrule import rrule, DAILY
from pytz import UTC
from odoo import fields, models, _, api
from odoo.exceptions import ValidationError
from odoo.tools import date_utils

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class HrAttendanceReport(models.TransientModel):
    """ Wizard for Employee Attendance Report """
    _name = 'employee.attendance.report'
    _description = 'Employee Attendance Report Wizard'

    from_date = fields.Date('From Date', help="Starting date for Report")
    to_date = fields.Date('To Date', help='Ending date for Report')
    employee_ids = fields.Many2many('hr.employee', string='Employees', help='Name of Employee')
    
    def float_to_time(self,float_value):
        hours = int(float_value)
        minutes = int(round((float_value - hours) * 60))
        return f"{hours:02d}:{minutes:02d}"
    
    def float_to_time1(self,float_value):
        hours = int(float_value)
        minutes = int(round((float_value - hours) * 60))
        return f"{hours:02d}.{minutes:02d}"

    def action_print_xlsx(self):
        """
        Returns report action for the XLSX Attendance report
        Raises: ValidationError: if From Date > To Date
        Raises: ValidationError: if there is no attendance records
        Returns:
            dict:  the XLSX report action
        """
        if not self.from_date:
            self.from_date = date.today()
        if not self.to_date:
            self.to_date = date.today()
        if self.from_date > self.to_date:
            raise ValidationError(_('From Date must be earlier than To Date.'))
        attendances = self.env['hr.attendance'].search(
            [('employee_id', 'in', self.employee_ids.ids)])
        data = {
            'from_date': self.from_date,
            'to_date': self.to_date,
            'employee_ids': self.employee_ids.ids
        }
        if self.employee_ids and not attendances:
            raise ValidationError(
                _("There is no attendance records for the employee"))
        if self.from_date and self.to_date:
            return {
                'type': 'ir.actions.report',
                'data': {'model': 'employee.attendance.report',
                         'options': json.dumps(
                             data, default=date_utils.json_default),
                         'output_format': 'xlsx',
                         'report_name': 'Attendance Report',
                         },
                'report_type': 'xlsx',
            }

    def get_xlsx_report(self, data, response):
        """
        Print the XLSX report
        Returns: None
        """
        query = """select hr_e.name,date(hr_at.check_in),
               SUM(hr_at.worked_hours) from hr_attendance hr_at LEFT JOIN
               hr_employee hr_e ON hr_at.employee_id = hr_e.id"""

        if not data['employee_ids']:
            query += """ GROUP BY date(check_in), hr_e.name"""

        else:
            query += """ WHERE hr_e.id in (%s) GROUP BY date(check_in),
               hr_e.name""" % (', '.join(str(employee_id)
                                         for employee_id in
                                         data['employee_ids']))
        self.env.cr.execute(query)
        docs = self.env.cr.dictfetchall()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Average Report')
        start_date = datetime.strptime(data['from_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['to_date'], '%Y-%m-%d').date()
        date_range = rrule(DAILY, dtstart=start_date, until=end_date)
        sheet.set_column(1, 1, 15)
        sheet.set_column(2, 2, 15)
        text_format = workbook.add_format({'text_wrap': True,'border': 1})
        border = workbook.add_format({'border': 1})
        green = workbook.add_format({'bg_color': '#28A828', 'border': 1})
        red = workbook.add_format({'bg_color': '#ff3333', 'border': 1})
        rose = workbook.add_format({'bg_color': '#DA70D6', 'border': 1})
        yellow = workbook.add_format({'bg_color': '#FFC300', 'border': 1})
        head = workbook.add_format(
            {'bold': True, 'font_size': 30, 'align': 'center'})
        date_size = workbook.add_format(
            {'font_size': 12, 'bold': True, 'align': 'center'})
        sheet.merge_range('C3:K6', 'Attendance Report', head)
        sheet.merge_range('C8:E9', 'From Date: ' + data['from_date'], date_size)
        sheet.merge_range('C10:E11', 'To Date: ' + data['to_date'], date_size)
        sheet.write(2, 11, '', green)
        sheet.write(2, 12, 'Present')
        sheet.write(4, 11, '', red)
        sheet.write(4, 12, 'Absent')
        sheet.write(6, 11, '', rose)
        sheet.write(6, 12, 'Below Work Hours')
        sheet.write(8, 11, '', yellow)
        sheet.write(8, 12, 'Below Average Hours')
        sheet.merge_range('B16:B17', 'Sl.No', border)
        sheet.merge_range('C16:C17', 'Employee', border)
        row = 15
        col = 2
        for date_data in date_range:
            col += 1
            sheet.write(row, col, date_data.strftime('%Y-%m-%d'), text_format)
        row = 16
        col = 2
        for date_data in date_range:
            col += 1
            sheet.write(row, col, date_data.strftime('%a'), text_format)
        col += 1
        sheet.write(row, col, 'Total Hours', border)
        col += 1
        sheet.write(row, col, 'Average Hours', border)
        employee_names = []
        attendance_list = []
        for doc in docs:
            if doc['name'] not in employee_names:
                date_sum_list = []
                employee_names.append(doc['name'])
                for date_data in date_range:
                    date_out = date_data.strftime('%Y-%m-%d')
                    record_list = list(
                        filter(
                            lambda x: x['name'] == doc['name'] and x[
                                'date'].strftime(
                                '%Y-%m-%d') == date_out, docs))
                    if record_list:
                        date_sum_list.append(record_list[0])
                    else:
                        date_sum_list.append({
                            'name': '',
                            'date': '',
                            'sum': 0
                        })
                attendance_list.append(
                    {'name': doc['name'], 'items': date_sum_list})
        work = self.env.ref('resource.resource_calendar_std')
        row = 17
        i = 0
        for rec in attendance_list:
            row += 1;col = 1;i += 1;tot = 0;avg = 0
            sheet.write(row, col, i, border)
            col += 1
            sheet.write(row, col, rec['name'], border)
            for item in rec['items']:
                col += 1
                if item['sum'] >= work.hours_per_day:
                    sheet.write(row, col, self.float_to_time(item['sum']), green)
                    tot+=item['sum']
                elif 0 < item['sum'] < self.env.company.attend_work_hrs:
                    sheet.write(row, col, self.float_to_time(item['sum']), rose)
                    tot+=item['sum']
                else:
                    sheet.write(row, col, self.float_to_time(item['sum']), red)
            col += 1
            leave_count = 0
            leave_days = self.get_unusual_days(start_date,end_date)
            leave_count += list(leave_days.values()).count(False)
            avg=tot/leave_count
            sheet.write(row, col, self.float_to_time(tot), border)
            col += 1
            if self.env.company.attend_work_hrs > avg:
                sheet.write(row, col, self.float_to_time(avg), yellow)
            else:
                sheet.write(row, col, self.float_to_time(avg), border)
            
        sheet1 = workbook.add_worksheet('Late attendance')
        sheet1.write(0, 0, 'Employee Name')
        sheet1.write(0, 1, 'S.No')
        sheet1.write(0, 2, 'Late Check In')
        row = 1
        employee_ids = self.env['hr.attendance'].search([('employee_id','in',data['employee_ids']),('fetch_date','<=',end_date),('fetch_date','>=',start_date)]).filtered(lambda a: float((a.check_in+timedelta(hours=5.5)).strftime("%H.%M")) > float(self.float_to_time1(self.env.company.company_start_time))).mapped('employee_id')
        for emp in employee_ids:
            sno = 1 
            sheet1.write(row, 0, emp.name, border)
            attendance_ids = self.env['hr.attendance'].search([('employee_id','=',emp.id),('fetch_date','<=',end_date),('fetch_date','>=',start_date)]).filtered(lambda a: float((a.check_in+timedelta(hours=5.5)).strftime("%H.%M")) > float(self.float_to_time1(self.env.company.company_start_time)))
            for att in attendance_ids:
                sheet1.write(row, 1, sno, border)
                sheet1.write(row, 2, (att.check_in+timedelta(hours=5.5)).strftime("%d-%m-%Y %H:%M:%S"), border)
                row += 1
                sno += 1
            
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    @api.model
    def get_unusual_days(self, from_date, to_date=None):
        # Checking the calendar directly allows to not grey out the leaves taken
        # by the employee
        calendar = self.env.user.employee_id.resource_calendar_id
        if not calendar:
            return {}
        dfrom = datetime.combine(fields.Date.from_string(from_date), time.min).replace(tzinfo=UTC)
        dto = datetime.combine(fields.Date.from_string(to_date), time.max).replace(tzinfo=UTC)

        works = {d[0].date() for d in calendar._work_intervals_batch(dfrom, dto)[False]}
        return {fields.Date.to_string(day.date()): (day.date() not in works) for day in rrule(DAILY, dfrom, until=dto)}
