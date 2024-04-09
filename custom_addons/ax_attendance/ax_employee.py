from odoo import fields,models,api
from dateutil.relativedelta import relativedelta
from datetime import datetime
import calendar
from odoo.tools import date_utils
import xlwt
import base64
from io import BytesIO

class Employee(models.Model):
	_inherit = "hr.employee"

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
				leave_day = emp.get_unusual_days_emp(emp.resource_calendar_id,sterday,sterday)
				if attend_id and attend_id.worked_hours < attend_id.company_id.attend_work_hrs:
					context = {
						'email_to':emp.work_email,
						'email_cc':emp.parent_id.work_email if emp.parent_id else '',
						'email_from':self.env.company.erp_email,
						'float_time':self.float_to_time(attend_id.worked_hours),
						'actual_time':self.float_to_time(attend_id.company_id.attend_work_hrs),
						'sterday':sterday.strftime("%d/%m/%Y"),
					}
					template = self.env['ir.model.data'].get_object('ax_attendance', 'email_template_daily_attendance_alert')
					self.env['mail.template'].browse(template.id).with_context(context).send_mail(emp.id,force_send=True)
				elif not attend_id and leave_day[sterday.strftime("%Y-%m-%d")] == False:
					context = {
						'email_to':emp.work_email,
						'email_cc':emp.parent_id.work_email if emp.parent_id else '',
						'email_from':self.env.company.erp_email,
						'float_time':self.float_to_time(0),
						'actual_time':self.float_to_time(emp.company_id.attend_work_hrs),
						'sterday':sterday.strftime("%d/%m/%Y"),
					}
					template = self.env['ir.model.data'].get_object('ax_attendance', 'email_template_daily_attendance_alert')
					self.env['mail.template'].browse(template.id).with_context(context).send_mail(emp.id,force_send=True)

	def _alert_weekly_attendance(self):
		today = datetime.now().date()
		if today.weekday() == 3:
			start_date = today - relativedelta(days=6)
			date_difference = (today - start_date).days + 1
			emp_ids = self.env['hr.employee'].search([('active','=',True)])
			for emp in emp_ids:
				avg_len = 7
				attend_ids = self.env['hr.attendance'].search([('employee_id','=',emp.id),('check_in','>=',start_date),
				('check_out','<',today)])
				leave_day = emp.get_unusual_days_emp(emp.resource_calendar_id,start_date,today)
				current_date = start_date
				for x in range(1,date_difference + 1):
					if leave_day[current_date.strftime("%Y-%m-%d")] == True:
						avg_len -= 1
					current_date = start_date + relativedelta(days=x)
				if attend_ids:
					avg_hrs = sum([x.worked_hours for x in attend_ids])/avg_len
					if avg_hrs < emp.company_id.attend_work_hrs:
						context = {
							'email_to':emp.work_email,
							'email_cc':emp.parent_id.work_email if emp.parent_id else '',
							'email_from':self.env.company.erp_email,
							'float_time':self.float_to_time(avg_hrs),
							'actual_time':self.float_to_time(emp.company_id.attend_work_hrs),
							'start_date':start_date.strftime("%A, %B %d, %Y"),
							'end_date':today.strftime("%A, %B %d, %Y")
						}
						template = self.env['ir.model.data'].get_object('ax_attendance', 'email_template_weekly_attendance_alert')
						self.env['mail.template'].browse(template.id).with_context(context).send_mail(emp.id,force_send=True)

	def _alert_monthly_attendance(self):
		today = fields.date.today()
		previous_month = date_utils.subtract(today, months=1)
		last_day = calendar.monthrange(previous_month.year,previous_month.month)[1]
		start_date = previous_month.replace(day=1, month=previous_month.month, year=previous_month.year)
		last_date = previous_month.replace(day=last_day, month=previous_month.month, year=previous_month.year)
		parent_ids = self.env['hr.employee'].search([]).mapped('parent_id')
		for parent in parent_ids:
			emp_list = []
			employee_ids = self.env['hr.employee'].search([('parent_id','=',parent.id)])
			for emp in employee_ids:
				emp_dict = {};att_list = []
				attend_ids = self.env['hr.attendance'].search([('employee_id','=',emp.id),('check_in','>=',start_date),
							('check_out','<',last_date)]).filtered(lambda a: a.actual_hours < emp.company_id.attend_work_hrs)
				for att in attend_ids:
					att_dict = {'date': att.check_in.date(),'hour': self.float_to_time(att.actual_hours)}
					att_list.append(att_dict)
				if att_list:
					emp_dict['emp'] = emp.name
					emp_dict['less_avg'] = att_list
					emp_list.append(emp_dict)
			if emp_list:
				context = {
					'name':parent.name,
					'actual_time':self.float_to_time(emp.company_id.attend_work_hrs),
					'email_to':parent.work_email,
					'email_from':self.env.company.erp_email,
					'emp_list':emp_list
				}
				template = self.env['ir.model.data'].get_object('ax_attendance', 'email_template_monthly_attendance_alert')
				self.env['mail.template'].browse(template.id).with_context(context).send_mail(emp.id,force_send=True)

	def _employee_weekly_alert_timesheet_attendance(self):	
		today = datetime.now().date()
		group_id = self.env.ref('ax_groups.admin_user_group')
		for user in group_id.users:
			if today.weekday() == 0:
				workbook = xlwt.Workbook(encoding="UTF-8")
				format1 = xlwt.easyxf('font:bold True,name Calibri;align: horiz center;borders: left thin, right thin, top thin, bottom thin;')
				format2 = xlwt.easyxf('font:name Calibri;align: horiz right;borders: left thin, right thin, top thin, bottom thin;')
				format3 = xlwt.easyxf('pattern: pattern solid,fore-colour pink;font:name Calibri;align: horiz right;borders: left thin, right thin, top thin, bottom thin;')
				format4 = xlwt.easyxf('font:name Calibri;align: horiz left;borders: left thin, right thin, top thin, bottom thin;')
				sheet = workbook.add_sheet('Employee attendance report')
				sheet.col(0).width = int(15*260)
				sheet.col(1).width = int(50*260)
				sheet.col(2).width = int(20*260)
				sheet.col(3).width = int(20*260)
				sheet.write(0, 0, 'Date', format1)
				sheet.write(0, 1, 'Employee Name', format1)
				sheet.write(0, 2, 'Attendance Hours', format1)
				sheet.write(0, 3, 'Timesheet Hours', format1)
				emp_ids = self.env['hr.employee'].search([])
				i=1
				for emp in emp_ids:
					for l in range(1,7):
						date = today - relativedelta(days=l)
						attendance_id = self.env['hr.attendance'].search([('employee_id','=',emp.id),('fetch_date','=',date)])
						timesheet_ids = self.env['account.analytic.line'].search([('employee_id','=',emp.id),('date','=',date)])
						sheet.write(i, 0, date.strftime("%d/%b/%Y"), format2)
						sheet.write(i, 1, emp.name, format4)
						atten = attendance_id.actual_hours if attendance_id else 0
						time = sum(timesheet_ids.mapped('unit_amount')) if timesheet_ids else 0
						if atten != time:
							sheet.write(i, 2, self.float_to_time(atten), format3)
							sheet.write(i, 3, self.float_to_time(time), format3)
						else:
							sheet.write(i, 2, self.float_to_time(atten), format2)
							sheet.write(i, 3, self.float_to_time(time), format2)
						i+=1
				fp = BytesIO()
				workbook.save(fp)     
				report_id = self.env['ir.attachment'].create({'name': 'Employee attendance and timesheet hours difference report.xls','type': 'binary',
	                'datas': base64.encodestring(fp.getvalue()),'res_model': 'hr.attendance','res_id': self.id})
				context = {
					'email_to':user.email,
					'email_from':self.env.company.erp_email,
					}
				template = self.env.ref('ax_attendance.email_template_admin_weekly_attendance_timesheet_alert')
				template.write({'attachment_ids': [(6,0,[report_id.id])]})
				template.with_context(context).send_mail(self.id, force_send=True)
				report_id.unlink()
				
	def _entry_employee_timesheet_daily_alert(self):
		employee_ids = self.env["hr.employee"].search([('active','=',True)])
		sterday = datetime.now().date() - relativedelta(days=1)
		for emp in employee_ids:
			leave_day = emp.get_unusual_days_emp(emp.resource_calendar_id,sterday,sterday)
			leave_id = self.env['hr.leave'].search([('request_date_from','<=',sterday),('request_date_to','>=',sterday),('employee_id','=',emp.id),('state','=','validate')])
			if leave_day[sterday.strftime("%Y-%m-%d")] == False and not leave_id:
				timesheet_ids = self.env['account.analytic.line'].search([('date','>=',sterday),('date','<=',sterday),
					('employee_id','=',emp.id)])
				if timesheet_ids:
					if sum([x.unit_amount for x in timesheet_ids]) < self.env.company.timesheet_working_hrs:
						context = {
							'email_to':emp.user_id.email,
							'email_from':self.env.company.erp_email,
							'float_time':self.float_to_time(sum([x.unit_amount for x in timesheet_ids])),
							'subject': "System Notification: Timesheet Update Required for %s"%(sterday.strftime("%d/%m/%Y")),
							'sterday':sterday.strftime("%d/%m/%Y"),
							'template':'less',
							'work_hrs':self.float_to_time(self.env.company.timesheet_working_hrs)
						}
						template = self.env['ir.model.data'].get_object('sttl_timesheet_calendar', 'email_template_daily_timesheet_less_hrs_alert')
						self.env['mail.template'].browse(template.id).with_context(context).send_mail(emp.id,force_send=True)
					else:
						context = {
							'email_to':emp.user_id.email,
							'email_from':self.env.company.erp_email,
							'subject': "System Notification: Timesheet Update Required for %s"%(sterday.strftime("%d/%m/%Y")),
							'sterday':sterday.strftime("%d/%m/%Y"),
							'template':'not-created',
						}
						template = self.env['ir.model.data'].get_object('sttl_timesheet_calendar', 'email_template_daily_timesheet_alert')
						self.env['mail.template'].browse(template.id).with_context(context).send_mail(emp.id,force_send=True)

	def _entry_manager_timesheet_alert(self):
		nxt_date = self.env.company.timesheet_manager_nxt_date
		if datetime.now().date() ==  nxt_date:
			from_date = nxt_date - relativedelta(days=self.env.company.timesheet_manager_alert)
			to_date = nxt_date
			date_difference = (to_date - from_date).days
			parent_ids = self.env["hr.employee"].search([('active','=',True)]).mapped('parent_id')
			self.env.company.timesheet_manager_nxt_date = nxt_date + relativedelta(days=self.env.company.timesheet_manager_alert)
			if parent_ids:
				for parent in parent_ids:
					employee_ids = self.env["hr.employee"].search([('parent_id','child_of',parent.id)])
					emp_ids = []
					if employee_ids:
						for emp in employee_ids:
							for x in range(date_difference + 1):
								current_date = from_date + relativedelta(days=x)
								leave_day = emp.get_unusual_days_emp(emp.resource_calendar_id,current_date,current_date)
								leave_id = self.env['hr.leave'].search([('request_date_from','<=',current_date),('request_date_to','>=',current_date),('employee_id','=',emp.id),('state','=','validate')])
								if leave_day[current_date.strftime("%Y-%m-%d")] == False and not leave_id:
									timesheet_ids = self.env['account.analytic.line'].search([('date','>=',current_date),('date','<=',current_date),
										('employee_id','=',emp.id)])
									if emp not in emp_ids:
										if not timesheet_ids:
											emp_ids.append(emp)
										elif timesheet_ids and sum([x.unit_amount for x in timesheet_ids]) < self.env.company.timesheet_working_hrs:
											emp_ids.append(emp)
										else:
											pass
						context = {
							'email_to':parent.user_id.email,
							'email_from':self.env.company.erp_email,
							'subject': "System Notification: Timesheet Update Required for Employees",
							'emp_ids':emp_ids,
							'from_date':from_date,
							'to_date':to_date,
						}
						template = self.env['ir.model.data'].get_object('sttl_timesheet_calendar', 'email_template_manager_timesheet_alert')
						self.env['mail.template'].browse(template.id).with_context(context).send_mail(parent.id,force_send=True)
	
	def get_missed_timesheet_dates(self,emp,from_date,to_date):
		if emp and from_date and to_date:
			date_difference = (to_date - from_date).days
			dates = []
			for x in range(date_difference + 1):
				current_date = from_date + relativedelta(days=x)
				leave_day = emp.get_unusual_days_emp(emp.resource_calendar_id,current_date,current_date)
				if leave_day[current_date.strftime("%Y-%m-%d")] == False:
					timesheet_ids = self.env['account.analytic.line'].search([('date','>=',current_date),('date','<=',current_date),
						('employee_id','=',emp.id)])
					if not timesheet_ids:
						dates.append(current_date)
			return dates
