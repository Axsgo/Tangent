from odoo import api, fields, models, registry, _
from dateutil.relativedelta import relativedelta
import datetime
from datetime import timedelta
from odoo.exceptions import ValidationError


class EmployeeAttendanceRegister(models.TransientModel):
    _name = 'employee.attendance.register'
    _description = 'Employee Attendance Register'

    @api.model
    def default_get(self, default_fields):
        res = super(EmployeeAttendanceRegister, self).default_get(default_fields)
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
    employee_ids = fields.Many2many('hr.employee', 'employee_rel', 'category_id', string='Employee Wise', required=True)
    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)
    absent = fields.Char('Absent', default='A')

    def get_data(self):
        date_list = []
        start_date = self.start_date
        end_date = self.end_date
        delta = relativedelta(days=1)
        while start_date <= end_date:
            date_list.append({
                "date_list": start_date.day,
            })
            start_date += delta
        return date_list

    def check_attendance(self):
        data = []
        report = self.env['hr.attendance'].search(
            [('employee_id', 'in', self.employee_ids.ids), ('check_in', '>=', self.start_date),
             ('check_in', '<=', self.end_date)])
        for rec in report:
            val = rec.check_in.date()
            if rec.check_in:
                data.append({
                    'date': val.day,
                    'state': 'P',
                    'employee': rec.employee_id.id,
                    'department': rec.employee_id.department_id.id,
                })
        res_list = [i for n, i in enumerate(data)
                    if i not in data[n + 1:]]
        return res_list

    def print_pdf(self):
        return {
            'type': 'ir.actions.report',
            'report_name': 'bi_hr_attendance_leave_report.report_attendance_register',
            'report_type': 'qweb-pdf'
        }


class EmployeeLeaveRegister(models.TransientModel):
    _name = 'employee.leave.register'
    _description = 'Employee Leave Register'

    @api.model
    def default_get(self, default_fields):
        res = super(EmployeeLeaveRegister, self).default_get(default_fields)
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
    leave_type_count = fields.Integer('Leave Type Count')
    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        for leave in self:
            if leave.start_date > leave.end_date:
                raise ValidationError(_('The start date of the time off must be earlier than the end date.'))

    @api.onchange('dept_id')
    def onchange_leave_types(self):
        leave_type = self.env['hr.leave.type'].search([('active', '=', True)])
        self.leave_type_count = len(leave_type)

    def get_leave_types(self):
        data_leave_type = []
        leave_type = self.env['hr.leave.type'].search([('active', '=', True)])
        for l_type in leave_type:
            data_leave_type.append({'leave_type': l_type.name, 'leave_type_id': l_type.id})
        return data_leave_type

    def get_leave_allocation(self):
        data_leave_allocation = []
        for employee in self.employee_ids:
            for leave_type in self.env['hr.leave.type'].search([('active', '=', True)]):
                allocate_count = 0
                for leave_allocate in self.env['hr.leave.allocation'].search(
                        [('employee_id', '=', employee.id), ('state', '=', 'validate'),
                         ('holiday_status_id', '=', leave_type.id)]):
                    allocate_count = allocate_count + leave_allocate.number_of_days_display
                data_leave_allocation.append({
                    'leave_type': leave_type.id,
                    'employee': employee.id,
                    'duration': "{0:.2f}".format(allocate_count),
                })
        return data_leave_allocation

    def get_leave(self):
        data_leave = []
        for employee in self.employee_ids:
            for leave_type in self.env['hr.leave.type'].search([('active', '=', True)]):
                leave_count = 0
                for leave_allocate in self.env['hr.leave'].search(
                        [('employee_id', '=', employee.id), ('state', '=', 'validate'),
                         ('holiday_status_id', '=', leave_type.id)]):
                    if (leave_allocate.request_date_from <= self.start_date and leave_allocate.request_date_to >= self.start_date) or (leave_allocate.request_date_from <= self.start_date and leave_allocate.request_date_to >= self.end_date) or (leave_allocate.request_date_from >= self.start_date and leave_allocate.request_date_to <= self.end_date)or (leave_allocate.request_date_from <= self.end_date and leave_allocate.request_date_to >= self.end_date):
                        leave_count = leave_count + leave_allocate.number_of_days_display
                data_leave.append({
                    'leave_type': leave_type.id,
                    'employee': employee.id,
                    'duration': "{0:.2f}".format(leave_count),
                })
        return data_leave

    def get_remain_leave(self):
        remain_leave = []
        for employee in self.employee_ids:
            for leave_type in self.env['hr.leave.type'].search([('active', '=', True)]):
                leave_count = 0
                for leave_allocate in self.env['hr.leave'].search(
                        [('employee_id', '=', employee.id), ('state', '=', 'validate'),
                         ('holiday_status_id', '=', leave_type.id)]):
                    if (leave_allocate.request_date_from <= self.start_date and leave_allocate.request_date_to >= self.start_date) or (leave_allocate.request_date_from <= self.start_date and leave_allocate.request_date_to >= self.end_date) or (leave_allocate.request_date_from >= self.start_date and leave_allocate.request_date_to <= self.end_date)or (leave_allocate.request_date_from <= self.end_date and leave_allocate.request_date_to >= self.end_date):
                        leave_count = leave_count + leave_allocate.number_of_days_display
                leave_alloc = 0
                for leave_allocate in self.env['hr.leave.allocation'].search(
                        [('employee_id', '=', employee.id), ('state', '=', 'validate'),
                         ('holiday_status_id', '=', leave_type.id)]):
                    leave_alloc = leave_alloc + leave_allocate.number_of_days_display
                leave = leave_alloc - leave_count
                remain_leave.append({
                    'leave_type': leave_type.id,
                    'employee': employee.id,
                    'duration': "{0:.2f}".format(leave),
                })
        return remain_leave

    def get_total_leave(self):
        remain_leave = []
        for employee in self.employee_ids:
            total_leave = 0
            leave = 0
            for leave_type in self.env['hr.leave.type'].search([('active', '=', True)]):
                leave_count = 0
                for leave_allocate in self.env['hr.leave'].search(
                        [('employee_id', '=', employee.id), ('state', '=', 'validate'),
                         ('holiday_status_id', '=', leave_type.id)]):
                    if (leave_allocate.request_date_from <= self.start_date and leave_allocate.request_date_to >= self.start_date) or (leave_allocate.request_date_from <= self.start_date and leave_allocate.request_date_to >= self.end_date) or (leave_allocate.request_date_from >= self.start_date and leave_allocate.request_date_to <= self.end_date)or (leave_allocate.request_date_from <= self.end_date and leave_allocate.request_date_to >= self.end_date):
                        leave_count = leave_count + leave_allocate.number_of_days_display
                leave_alloc = 0
                for leave_allocate in self.env['hr.leave.allocation'].search(
                        [('employee_id', '=', employee.id), ('state', '=', 'validate'),
                         ('holiday_status_id', '=', leave_type.id)]):
                    leave_alloc = leave_alloc + leave_allocate.number_of_days_display
                leave_remain = leave_alloc - leave_count
                leave = leave + leave_remain
            total_leave = total_leave + leave
            remain_leave.append({
                'employee': employee.id,
                'duration': "{0:.2f}".format(total_leave),
            })
        return remain_leave

    def print_pdf(self):
        return {
            'type': 'ir.actions.report',
            'report_name': 'bi_hr_attendance_leave_report.report_leave_register',
            'report_type': 'qweb-pdf'
        }
