from odoo import fields, api, models
from datetime import datetime,date
from dateutil.relativedelta import relativedelta


class HREmployee(models.Model):
	_inherit = "hr.employee"
	
	not_required = fields.Boolean('Timesheet Not Required')
	
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

	# def _entry_manager_timesheet_alert(self):
	# 	if datetime.now().date() ==  self.env.company.timesheet_manager_nxt_date:
	# 		from_date = datetime.now().date() - relativedelta(days=self.env.company.timesheet_manager_alert)
	# 		to_date = datetime.now().date()
	# 		parent_ids = self.env["hr.employee"].search([('active','=',True)]).mapped('parent_id')
	# 		if parent_ids:
	# 			for parent in parent_ids:
	# 				employee_ids = self.env["hr.employee"].search([('parent_id','child_of',parent.id)])
	# 				emp_ids = []
	# 				if employee_ids:
	# 					for emp in employee_ids:
	# 						for x in range(from_date,to_date):
	# 							timesheet_ids = self.env['account.analytic.line'].search([('date','>=',x),('date','<=',x),
	# 								('employee_id','=',emp.id)])
	# 							if not timesheet_ids:
	# 								emp_ids.append(emp)
	# 							elif timesheet_ids and sum([x.unit_amount for x in timesheet_ids]) < self.env.company.timesheet_working_hrs:
	# 								emp_ids.append(emp)
	# 							else:
	# 								pass

class HREmployeePublic(models.Model):
	_inherit = "hr.employee.public"
	
	not_required = fields.Boolean('Timesheet Not Required')
	