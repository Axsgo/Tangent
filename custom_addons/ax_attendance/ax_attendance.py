from odoo import fields,api,models,_
from odoo.tools import format_datetime
from datetime import datetime,time,timedelta
from pytz import UTC
from dateutil.rrule import rrule, DAILY
import xlwt
import base64
from io import BytesIO
from dateutil.relativedelta import relativedelta


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
		today = datetime.now().date()
		sterday = today - relativedelta(days=1)
		for attendance in self.env['hr.attendance'].search([('fetch_date','=',sterday)]).filtered(lambda a: a.actual_hours < self.env.company.attend_work_hrs):
			workbook = xlwt.Workbook(encoding="UTF-8")
			format1 = xlwt.easyxf('font:bold True,name Calibri;align: horiz left;')
			format2 = xlwt.easyxf('font:name Calibri;align: horiz right;')
			format3 = xlwt.easyxf('font:bold True,name Calibri;align: horiz right;')
			sheet = workbook.add_sheet('Employee attendance report')
			sheet.col(0).width = int(40*260)
			for r in range(1,5):
				sheet.col(r).width = int(25*260)
			i=1;k=len(attendance.line_ids)
			sheet.write(0, 3, 'Counted', format1)
			sheet.write(0, 4, 'Non-Counted', format1)
			sheet.write(1, 0, 'First Check-in & Last Check-out', format1)
			sheet.write(1, 1, (attendance.check_in+timedelta(hours=5.5)).strftime("%d-%m-%Y %H:%M:%S"), format3)
			sheet.write(1, 2, (attendance.check_out+timedelta(hours=5.5)).strftime("%d-%m-%Y %H:%M:%S"), format3)
			sheet.write(1, 3, self.float_to_time(attendance.actual_hours), format3)
			check_out = False;non_count = timedelta(days=0);count = timedelta(days=0)
			for line in attendance.line_ids:
				if i!=1:
					sheet.write(i, 2, (line.check_in+timedelta(hours=5.5)).strftime("%d-%m-%Y %H:%M:%S"), format2)
					dif = (line.check_in+timedelta(hours=5.5)) - check_out
					hours = int(dif.seconds / 3600)
					minutes = (dif.seconds % 3600) / 60 
					if hours == 0 and minutes <= 15:
						sheet.write(i, 4, str(dif), format2)
						non_count += dif
					else:
						sheet.write(i, 3, str(dif), format2)
						count += dif
				if k!=i:
					sheet.write(i+1, 0, 'Break '+str(i), format1)
					sheet.write(i+1, 1, (line.check_out+timedelta(hours=5.5)).strftime("%d-%m-%Y %H:%M:%S"), format2)
					check_out = line.check_out+timedelta(hours=5.5)
				i+=1
			sheet.write(i, 4, str(non_count), format3)
			sheet.write(i, 3, str(count), format3)
			fp = BytesIO()
			workbook.save(fp)     
			report_id = self.env['ir.attachment'].create({'name': sterday.strftime("%d/%b/%Y")+' - Employee attendance Report.xls','type': 'binary',
                'datas': base64.encodestring(fp.getvalue()),'res_model': 'hr.attendance','res_id': self.id})
			context = {
    # 'email_to':attendance.employee_id.work_email,
    			'email_to':'rajeev@tangentlandscape.com,savitha.dileep@tangentlandscape.com',
				'email_from':self.env.company.erp_email,
				'sterday':sterday
				}
			template = self.env.ref('ax_attendance.email_template_employee_daily_attendance_alert')
			template.write({'attachment_ids': [(6,0,[report_id.id])]})
			template.with_context(context).send_mail(attendance.id, force_send=True)
   # report_id.unlink()

 # def _employee_weekly_alert_timesheet_attendance(self):	
 # 	today = datetime.now().date()
 # 	group_id = self.env.ref('ax_groups.admin_user_group')
 # 	for user in group_id.users:
 # 		if today.weekday() == 0:
 # 			workbook = xlwt.Workbook(encoding="UTF-8")
 # 			format1 = xlwt.easyxf('font:bold True,name Calibri;align: horiz center;borders: left thin, right thin, top thin, bottom thin;')
 # 			format2 = xlwt.easyxf('font:name Calibri;align: horiz right;borders: left thin, right thin, top thin, bottom thin;')
 # 			format3 = xlwt.easyxf('pattern: pattern solid,fore-colour pink;font:name Calibri;align: horiz right;borders: left thin, right thin, top thin, bottom thin;')
 # 			format4 = xlwt.easyxf('font:name Calibri;align: horiz left;borders: left thin, right thin, top thin, bottom thin;')
 # 			sheet = workbook.add_sheet('Employee attendance report')
 # 			sheet.col(0).width = int(15*260)
 # 			sheet.col(1).width = int(50*260)
 # 			sheet.col(2).width = int(20*260)
 # 			sheet.col(3).width = int(20*260)
 # 			sheet.write(0, 0, 'Date', format1)
 # 			sheet.write(0, 1, 'Employee Name', format1)
 # 			sheet.write(0, 2, 'Attendance Hours', format1)
 # 			sheet.write(0, 3, 'Timesheet Hours', format1)
 # 			emp_ids = self.env['hr.employee'].search([])
 # 			i=1
 # 			for emp in emp_ids:
 # 				for l in range(1,7):
 # 					date = today - relativedelta(days=l)
 # 					attendance_id = self.env['hr.attendance'].search([('employee_id','=',emp.id),('fetch_date','=',date)])
 # 					timesheet_ids = self.env['account.analytic.line'].search([('employee_id','=',emp.id),('date','=',date)])
 # 					sheet.write(i, 0, date.strftime("%d/%b/%Y"), format2)
 # 					sheet.write(i, 1, emp.name, format4)
 # 					atten = attendance_id.actual_hours if attendance_id else 0
 # 					time = sum(timesheet_ids.mapped('unit_amount')) if timesheet_ids else 0
 # 					if atten != time:
 # 						sheet.write(i, 2, self.float_to_time(atten), format3)
 # 						sheet.write(i, 3, self.float_to_time(time), format3)
 # 					else:
 # 						sheet.write(i, 2, self.float_to_time(atten), format2)
 # 						sheet.write(i, 3, self.float_to_time(time), format2)
 # 					i+=1
 # 			fp = BytesIO()
 # 			workbook.save(fp)     
 # 			report_id = self.env['ir.attachment'].create({'name': 'Employee attendance and timesheet hours difference report.xls','type': 'binary',
 #                 'datas': base64.encodestring(fp.getvalue()),'res_model': 'hr.attendance','res_id': self.id})
 # 			context = {
 # 				'email_to':user.email,
 # 				'email_from':self.env.company.erp_email,
 # 				}
 # 			template = self.env.ref('ax_attendance.email_template_admin_weekly_attendance_timesheet_alert')
 # 			template.write({'attachment_ids': [(6,0,[report_id.id])]})
 # 			template.with_context(context).send_mail(self.id, force_send=True)
 #   # report_id.unlink()


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
	