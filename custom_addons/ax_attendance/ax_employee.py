from odoo import fields,models,api
from dateutil.relativedelta import relativedelta
from datetime import datetime
import calendar
from odoo.tools import date_utils


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
