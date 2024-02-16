from odoo import fields,api,models,_
from odoo.tools import format_datetime
from dateutil import parser
from dateutil.relativedelta import relativedelta
from datetime import datetime,time
from pytz import UTC
from dateutil.rrule import rrule, DAILY
from calendar import monthrange

class AxAttendance(models.Model):
	_inherit = "hr.attendance"

	line_ids = fields.One2many("hr.attendance.line",'header_id')
	timesheet_hours = fields.Float("Break Hours",compute='_compute_timesheet_hours',store=True)
	actual_hours = fields.Float("Logged Hours",compute='_compute_actual_hours',store=True)
	check_in = fields.Datetime(string="Check In", required=True)
	check_out = fields.Datetime(string="Check Out", required=True)
	fetch_date = fields.Date(string='Attendance Date', required=True, tracking=True)

	@api.depends('line_ids','line_ids.worked_hours')
	def _compute_actual_hours(self):
		for rec in self:
			if rec.line_ids:
				rec.actual_hours = sum([x.worked_hours for x in rec.line_ids])
			else:
				rec.actual_hours = 0

	@api.depends('actual_hours','timesheet_hours')
	def  _compute_timesheet_hours(self):
		for rec in self:
			if rec.actual_hours > 0 and rec.worked_hours > 0:
				rec.timesheet_hours = rec.worked_hours - rec.actual_hours

	@api.model
	def get_unusual_days(self, check_in, check_out=None):
		# Checking the calendar directly allows to not grey out the leaves taken
		# by the employee
		calendar = self.env.user.employee_id.resource_calendar_id
		if not calendar:
			return {}
		dfrom = datetime.combine(fields.Date.from_string(check_in), time.min).replace(tzinfo=UTC)
		dto = datetime.combine(fields.Date.from_string(check_out), time.max).replace(tzinfo=UTC)

		works = {d[0].date() for d in calendar._work_intervals_batch(dfrom, dto)[False]}
		return {fields.Date.to_string(day.date()): (day.date() not in works) for day in rrule(DAILY, dfrom, until=dto)}

	def float_to_time(self,float_value):
		hours = int(float_value)
		minutes = int((float_value - hours) * 60)
		return f"{hours:02d}:{minutes:02d}"

	def _alert_daily_attendance(self):
		today = datetime.now().date()
		sterday = today - relativedelta(days=1)
		emp_ids = self.env['hr.employee'].search([('active','=',True)])
		if emp_ids:
			for emp in emp_ids:
				attend_id = self.env['hr.attendance'].search([('employee_id','=',emp.id),('check_in','>=',sterday),
					('check_out','<',today)])
				if attend_id and attend_id.worked_hours < 9:
					context = {
						'email_to':emp.work_email,
						'email_cc':emp.parent_id.work_email if emp.parent_id else '',
						'email_from':self.env.company.erp_email,
						'float_time':self.float_to_time(attend_id.worked_hours),
					}
					template = self.env['ir.model.data'].get_object('ax_attendance', 'email_template_daily_attendance_alert')
					self.env['mail.template'].browse(template.id).with_context(context).send_mail(attend_id.id,force_send=True)

	def _alert_weekly_attendance(self):
		today = datetime.now().date()
		if today.weekday() == 6:
			start_date = today - relativedelta(days=6)
			emp_ids = self.env['hr.employee'].search([('active','=',True)])
			if emp_ids:
				for emp in emp_ids:
					attend_ids = self.env['hr.attendance'].search([('employee_id','=',emp.id),('check_in','>=',start_date),
					('check_out','<',today)])
					if attend_ids:
						avg_hrs = sum([x.worked_hours for x in attend_ids])/len(attend_ids)
						if avg_hrs < 9:
							context = {
								'email_to':emp.work_email,
								'email_cc':emp.parent_id.work_email if emp.parent_id else '',
								'email_from':self.env.company.erp_email,
								'float_time':self.float_to_time(avg_hrs),
								'start_date':start_date.strftime("%A, %B %d, %Y"),
								'end_date':today.strftime("%A, %B %d, %Y")
							}
							template = self.env['ir.model.data'].get_object('ax_attendance', 'email_template_weekly_attendance_alert')
							self.env['mail.template'].browse(template.id).with_context(context).send_mail(emp.id,force_send=True)

	def _alert_monthly_attendance(self):
		today = datetime.now().date()
		last_day = monthrange(today.year,today.month)[1]
		if today.day == last_day:
			start_date = today - relativedelta(days=(last_day-1))
			emp_ids = self.env['hr.employee'].search([('active','=',True)])
			if emp_ids:
				for emp in emp_ids:
					attend_ids = self.env['hr.attendance'].search([('employee_id','=',emp.id),('check_in','>=',start_date),
					('check_out','<',today)])
					if attend_ids:
						avg_hrs = sum([x.worked_hours for x in attend_ids])/len(attend_ids)
						if avg_hrs < 9:
							context = {
								'email_to':emp.work_email,
								'email_cc':emp.parent_id.work_email if emp.parent_id else '',
								'email_from':self.env.company.erp_email,
								'float_time':self.float_to_time(avg_hrs),
								'start_date':start_date.strftime("%A, %B %d, %Y"),
								'end_date':today.strftime("%A, %B %d, %Y")
							}
							template = self.env['ir.model.data'].get_object('ax_attendance', 'email_template_monthly_attendance_alert')
							self.env['mail.template'].browse(template.id).with_context(context).send_mail(emp.id,force_send=True)

class AxAttendanceLine(models.Model):
	_name = "hr.attendance.line"
	_description = "Attendance Timesheet"
	_order = "check_out desc"

	header_id = fields.Many2one("hr.attendance")
	employee_id = fields.Many2one("hr.employee",'Employee',related='header_id.employee_id',store=True)
	check_in = fields.Datetime("Check In")
	check_out = fields.Datetime("Check Out")
	worked_hours = fields.Float("Logged Hours",compute='_compute_worked_hours',store=True)

	def name_get(self):
		result = []
		for attendance in self:
			if not attendance.check_out:
				result.append((attendance.id, _("%(empl_name)s from %(check_out)s") % {
					'empl_name': attendance.employee_id.name,
					'check_out': format_datetime(self.env, attendance.check_out, dt_format=False),
				}))
			else:
				result.append((attendance.id, _("%(empl_name)s from %(check_out)s to %(check_in)s") % {
					'empl_name': attendance.employee_id.name,
					'check_out': format_datetime(self.env, attendance.check_out, dt_format=False),
					'check_in': format_datetime(self.env, attendance.check_in, dt_format=False),
				}))
		return result

	@api.depends('check_in', 'check_out')
	def _compute_worked_hours(self):
		for attendance in self:
			if attendance.check_out and attendance.check_in:
				delta = attendance.check_out - attendance.check_in
				attendance.worked_hours = delta.total_seconds() / 3600.0
			else:
				attendance.worked_hours = False

	@api.model
	def get_unusual_days(self, check_in, check_out=None):
		# Checking the calendar directly allows to not grey out the leaves taken
		# by the employee
		calendar = self.env.user.employee_id.resource_calendar_id
		if not calendar:
			return {}
		dfrom = datetime.combine(fields.Date.from_string(check_in), time.min).replace(tzinfo=UTC)
		dto = datetime.combine(fields.Date.from_string(check_out), time.max).replace(tzinfo=UTC)

		works = {d[0].date() for d in calendar._work_intervals_batch(dfrom, dto)[False]}
		return {fields.Date.to_string(day.date()): (day.date() not in works) for day in rrule(DAILY, dfrom, until=dto)}