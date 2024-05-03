from odoo import fields,api,models,_
from odoo.tools import format_datetime
from datetime import datetime,time,timedelta
from pytz import UTC
from dateutil.rrule import rrule, DAILY
import xlwt
import base64
from io import BytesIO
from dateutil.relativedelta import relativedelta
import calendar
from odoo.tools import date_utils

class LocationMaster(models.Model):
	_name = "hr.location.master"
	_description = "Location Master"
	_order = "id desc"

	name = fields.Char("Room No.")
	detect_lunch = fields.Boolean("Detect Lunch Break",
		help="Detect Lunch Break from break hrs else add default 1hr Lunch break.")

class HrEmployee(models.Model):
	_inherit = "hr.employee"

	location_id = fields.Many2one("hr.location.master",'Location')

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
		minutes = int(round((float_value - hours) * 60))
		return f"{hours:02d}:{minutes:02d}"
	
	def _employee_alert_daily_attendance(self):
		today = self.env.company.fetch_date
		sterday = today - relativedelta(days=1)
		for attendance in self.env['hr.attendance'].search([('fetch_date','=',sterday)]).filtered(lambda a: a.actual_hours < self.env.company.attend_work_hrs):
			workbook = xlwt.Workbook(encoding="UTF-8")
			format1 = xlwt.easyxf('font:bold True,name Calibri;align: horiz left;')
			format2 = xlwt.easyxf('font:name Calibri;align: horiz right;')
			format3 = xlwt.easyxf('font:bold True,name Calibri;align: horiz right;')
			format4 = xlwt.easyxf('font:bold True,name Calibri, color blue;align: horiz left;')
			format5 = xlwt.easyxf('font:bold True,name Calibri, color red;align: horiz left;')
			format6 = xlwt.easyxf('font:bold True,name Calibri, color red;align: horiz right;')
			format7 = xlwt.easyxf('font:name Calibri, color green;align: horiz right;')
			format8 = xlwt.easyxf('font:bold True,name Calibri, color green;align: horiz right;')
			sheet = workbook.add_sheet('Employee attendance report')
			sheet.col(0).width = int(50*260)
			for r in range(1,5):
				sheet.col(r).width = int(25*260)
			i=4;j=1;k=len(attendance.line_ids)
			sheet.write(1, 0, 'First Check-in & Last Check-out', format1)
			sheet.write(1, 1, (attendance.check_in+timedelta(hours=5.5)).strftime("%d-%m-%Y %H:%M:%S"), format3)
			sheet.write(1, 2, (attendance.check_out+timedelta(hours=5.5)).strftime("%d-%m-%Y %H:%M:%S"), format3)
			sheet.write(1, 3, self.float_to_time(attendance.worked_hours), format3)
			if attendance.employee_id.location_id.detect_lunch == True:
				if any(x.check_out.time() > time(13,0) and x.check_out.time() < time(14,0) for x in attendance.line_ids) and any(x.check_in.time() > time(13,0) and x.check_in.time() < time(14,0) for x in attendance.line_ids):
					pass
				else:
					sheet.write(2, 0, 'Less 1 hour for the lunch break', format1)
					sheet.write(2, 3, self.float_to_time(-1), format3)
			sheet.write(3, 0, 'Total time excluding break', format1)
			sheet.write(3, 3, self.float_to_time((attendance.worked_hours-1)), format3)
			sheet.write(4, 0, 'Breaks', format4)
			sheet.write(4, 3, 'Counted', format4)
			sheet.write(4, 4, 'Non-Counted', format4)
			check_out = False;non_count = timedelta(days=0);count = timedelta(days=0)
			for line in attendance.line_ids:
				if j!=1:
					sheet.write(i, 2, (line.check_in+timedelta(hours=5.5)).strftime("%d-%m-%Y %H:%M:%S"), format2)
					dif = (line.check_in+timedelta(hours=5.5)) - check_out
					hours = int(dif.seconds / 3600)
					minutes = (dif.seconds % 3600) / 60 
					if hours == 0 and minutes <= 15:
						sheet.write(i, 4, str(dif), format7)
						non_count += dif
					else:
						sheet.write(i, 3, str(dif), format2)
						count += dif
				if k!=j:
					sheet.write(i+1, 0, 'Break '+str(j), format1)
					sheet.write(i+1, 1, (line.check_out+timedelta(hours=5.5)).strftime("%d-%m-%Y %H:%M:%S"), format2)
					check_out = line.check_out+timedelta(hours=5.5)
				i+=1;j+=1
			sheet.write(i, 0, 'Total Breaks', format1)
			sheet.write(i, 4, str(non_count), format8)
			sheet.write(i, 3, str(count), format3)
			sheet.write(i+2, 0, 'Net total time inside the office ('+str(self.float_to_time(attendance.worked_hours))+' - '+str(count)+')', format5)
			wk_hr=timedelta(hours=attendance.worked_hours)
			bk_hr=count+timedelta(hours=1)
			sheet.write(i+2, 3, str(wk_hr-bk_hr), format6)
			fp = BytesIO()
			workbook.save(fp)     
			report_id = self.env['ir.attachment'].create({'name': sterday.strftime("%d/%b/%Y")+' - Employee attendance Report.xls','type': 'binary',
                'datas': base64.encodestring(fp.getvalue()),'res_model': 'hr.attendance','res_id': self.id})
			context = {
			    'email_to':attendance.employee_id.work_email,
				'email_from':self.env.company.erp_email,
				'sterday':sterday,
				'com_work_hrs':self.env.company.attend_work_hrs
				}
			template = self.env.ref('ax_attendance.email_template_employee_daily_attendance_alert')
			template.write({'attachment_ids': [(6,0,[report_id.id])]})
			template.with_context(context).send_mail(attendance.id, force_send=True)
			report_id.unlink()

class Employee(models.Model):
	_inherit = "hr.employee"

	def _employee_weekly_alert_timesheet_attendance(self):	
		today = datetime.now().date()
		if today.weekday() == 0:
			start_date = today - relativedelta(days=1)
			last_date = today - relativedelta(days=7)
			emp_ids = self.env['hr.employee'].search([])
			for emp in emp_ids:
				attendance_ids = self.env['hr.attendance'].search([('employee_id','=',emp.id),('fetch_date','>=',last_date),('fetch_date','<=',start_date)])
				if attendance_ids:
					if sum(attendance_ids.mapped('actual_hours')) < (7 * self.env.company.attend_work_hrs):
						context = {
			    			'email_to':emp.work_email,
							'email_from':self.env.company.erp_email,
							'today':start_date,
							'last_week':last_date,
							'com_work_hrs':self.env.company.attend_work_hrs
						}
						template = self.env.ref('ax_attendance.email_template_employee_weekly_attendance_timesheet_alert')
						template.with_context(context).send_mail(emp.id, force_send=True)
			
	def _employee_monthly_alert_timesheet_attendance(self):	
		today = fields.date.today()
		previous_month = date_utils.subtract(today, months=1)
		last_day = calendar.monthrange(previous_month.year,previous_month.month)[1]
		start_date = previous_month.replace(day=1, month=previous_month.month, year=previous_month.year)
		last_date = previous_month.replace(day=last_day, month=previous_month.month, year=previous_month.year)
		days = last_date-start_date
		emp_ids = self.env['hr.employee'].search([])
		for emp in emp_ids:
			attendance_ids = self.env['hr.attendance'].search([('employee_id','=',emp.id),('fetch_date','>=',start_date),('fetch_date','<=',last_date)])
			if attendance_ids:
				if sum(attendance_ids.mapped('actual_hours')) < (days.days * self.env.company.attend_work_hrs):
					context = {
		    			'email_to':emp.work_email,
						'email_from':self.env.company.erp_email,
						'month':previous_month.strftime("%B"),
						'com_work_hrs':self.env.company.attend_work_hrs
					}
					template = self.env.ref('ax_attendance.email_template_employee_monthly_attendance_timesheet_alert')
					template.with_context(context).send_mail(emp.id, force_send=True)
		

class AxAttendanceLine(models.Model):
	_name = "hr.attendance.line"
	_description = "Attendance Timesheet"
	_order = "id asc"

	header_id = fields.Many2one("hr.attendance")
	employee_id = fields.Many2one("hr.employee",'Employee',related='header_id.employee_id',store=True)
	check_in = fields.Datetime("Check In")
	check_out = fields.Datetime("Check Out")
	worked_hours = fields.Float("Logged Hours",compute='_compute_worked_hours',store=True)
	is_permission = fields.Boolean('Permission')

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
	