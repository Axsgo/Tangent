from odoo import fields, api, models
from datetime import datetime,date,time
from dateutil.relativedelta import relativedelta
import pytz
from dateutil.rrule import rrule, DAILY


class HREmployee(models.Model):
	_inherit = "hr.employee"
	
	not_required = fields.Boolean('Timesheet Not Required')
	date_of_join = fields.Date("Date of Joining", required=True)
	
	@api.model
	def create(self, vals):
		lines = super(HREmployee, self).create(vals)
		if vals.get('not_required')==False:
			submit_ids = self.env['hr.timesheet.submit'].search([('to_date','>=',date.today())])
			for submit_id in submit_ids:
				self.env['hr.timesheet.submit.line'].sudo().create({'employee_id':lines.id,'submit_id':submit_id.id})
		return lines
	
	def write(self, vals):
		res = super(HREmployee, self).write(vals)
		if vals.get('not_required')==False:
			submit_ids = self.env['hr.timesheet.submit'].search([('to_date','>=',date.today())])
			for submit_id in submit_ids:
				if not self.env['hr.timesheet.submit.line'].search([('employee_id','=',self.id),('submit_id','=',submit_id.id)]):
					self.env['hr.timesheet.submit.line'].sudo().create({'employee_id':self.id,'submit_id':submit_id.id})
		return res

	def float_to_time(self,float_value):
		hours = int(float_value)
		minutes = int((float_value - hours) * 60)
		return f"{hours:02d}:{minutes:02d}"

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

	@api.model
	def get_unusual_days_emp(self, calendar_id, date_from, date_to=None):
		calendar = calendar_id
		if not calendar:
			return {}
		tz = pytz.timezone('UTC')
		dfrom = pytz.utc.localize(datetime.combine(fields.Date.from_string(date_from), time.min)).astimezone(tz)
		dto = pytz.utc.localize(datetime.combine(fields.Date.from_string(date_to), time.max)).astimezone(tz)
		works = {d[0].date() for d in calendar._work_intervals_batch(dfrom, dto)[False]}
		return {fields.Date.to_string(day.date()): (day.date() not in works) for day in rrule(DAILY, dfrom, until=dto)}


class HREmployeePublic(models.Model):
	_inherit = "hr.employee.public"
	
	not_required = fields.Boolean('Timesheet Not Required')
	date_of_join = fields.Date("Date of Joining")
	