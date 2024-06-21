from odoo import api, fields, models, registry, _
from dateutil.relativedelta import relativedelta
import datetime
from datetime import timedelta
from odoo.exceptions import ValidationError
import xlwt
import base64
from io import BytesIO


class AxLeaveRegister(models.TransientModel):
    _name = 'ax.leave.register'
    _description = 'Employee Leave Register'

    @api.model
    def default_get(self, default_fields):
        res = super(AxLeaveRegister, self).default_get(default_fields)
        today = datetime.date.today()
        first = today.replace(day=1)
        last_month_first = (today - timedelta(days=today.day)).replace(day=1)
        last_month = first - datetime.timedelta(days=1)
        res.update({
            'start_date': last_month_first or False,
            'end_date': last_month or False
        })
        return res

    @api.onchange('dept_id')
    def onchange_employee(self):
        for dept in self:
            emp = []
            for employee in self.env['hr.employee'].search([('department_id', '=', dept.dept_id.id)]):
                emp.append(employee.id)
            dept.employee_ids = emp

    dept_id = fields.Many2one('hr.department', 'Department Wise')
    employee_ids = fields.Many2many('hr.employee', string='Employee Wise', required=True)
    leave_type_ids = fields.Many2many('hr.leave.type', string='Leave Type', required=True)
    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)
    excel_file = fields.Binary(string='Report File')

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        for leave in self:
            if leave.start_date > leave.end_date:
                raise ValidationError(_('The start date of the time off must be earlier than the end date.'))

    def float_to_time(self,float_value):
        hours = int(float_value)
        minutes = int((float_value - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"
    
    def get_duration(self,duration):
        return duration*24
    
    def print_report(self):
        workbook = xlwt.Workbook(encoding="UTF-8")
        sheet = workbook.add_sheet('Employee leave report')
        format1 = xlwt.easyxf('font:bold True,name Calibri;align: horiz center;borders: left thin, right thin, top thin, bottom thin;')
        format2 = xlwt.easyxf('font:name Calibri;align: horiz right;borders: left thin, right thin, top thin, bottom thin;')
        format3 = xlwt.easyxf('font:bold True,name Calibri;align: horiz left;borders: left thin, right thin, top thin, bottom thin;')
        format4 = xlwt.easyxf('pattern: pattern solid,fore-colour pink;font:name Calibri;align: horiz right;borders: left thin, right thin, top thin, bottom thin;')
        col1=1;col2=3
        sheet.col(0).width = int(40*260)
        for lt in self.env['hr.leave.type'].search([('id','=',self.leave_type_ids.ids)],order='id asc'):
            sheet.write_merge(0, 0, col1, col2, lt.name, format1)
            sheet.write(1, col1, 'Days', format1)
            col1+=1
            sheet.write(1, col1, 'Half Day', format1)
            col1+=1
            sheet.write(1, col1, 'Permission(Hrs)', format1)
            sheet.col(col1).width = int(17*260)
            col1+=1;col2+=3
        row=2
        for emp in self.employee_ids:
            col1=1;col2=3
            sheet.write(row, 0, emp.name, format3)
            for leave_type in self.env['hr.leave.type'].search([('id','=',self.leave_type_ids.ids)],order='id asc'):
                leave_full = sum(self.env['hr.leave'].search([('employee_id','=',emp.id),('request_date_from','>=',self.start_date),('request_date_to','<=',self.end_date),('request_unit_half', '=', False),('request_unit_hours', '=', False),('state', '=', 'validate'),('holiday_status_id', '=', leave_type.id)]).mapped('number_of_days'))
                leave_half = sum(self.env['hr.leave'].search([('employee_id','=',emp.id),('request_date_from','>=',self.start_date),('request_date_to','<=',self.end_date),('request_unit_half', '=', True),('state', '=', 'validate'),('holiday_status_id', '=', leave_type.id)]).mapped('number_of_days'))
                leave_permission = sum(self.env['hr.leave'].search([('employee_id','=',emp.id),('request_date_from','>=',self.start_date),('request_date_to','<=',self.end_date),('request_unit_hours', '=', True),('state', '=', 'validate'),('holiday_status_id', '=', leave_type.id)]).mapped('number_of_hours_display'))
                if leave_full > 0:
                    sheet.write(row, col1, leave_full, format4)
                    col1+=1
                else:
                    sheet.write(row, col1, leave_full, format2)
                    col1+=1
                if leave_half > 0:
                    sheet.write(row, col1, leave_half, format4)
                    col1+=1
                else:
                    sheet.write(row, col1, leave_half, format2)
                    col1+=1
                if leave_permission > 0:
                    sheet.write(row, col1, leave_permission, format4)
                    col1+=1;col2+=3
                else:
                    sheet.write(row, col1, leave_permission, format2)
                    col1+=1;col2+=3
            row+=1
        fp = BytesIO()
        workbook.save(fp)
        self.write({'excel_file': base64.encodestring(fp.getvalue())})
        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=ax.leave.register&field=excel_file&download=true&id=%s&filename=%s' % (self.id, 'Employees leave report.xls'),
            'target': 'new',
        }
