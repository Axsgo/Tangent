from odoo import api, fields, models
from datetime import datetime
from dateutil.relativedelta import relativedelta

class Employee(models.Model):
	_inherit = "hr.employee"

	def _entry_manager_absent_alert(self):
		nxt_date = self.env.company.absent_manager_nxt_date
		if datetime.now().date() ==  nxt_date:
			parent_ids = self.env["hr.employee"].search([('active','=',True)]).mapped('parent_id')
			self.env.company.absent_manager_nxt_date = nxt_date + relativedelta(days=self.env.company.absent_manager_alert)
			if parent_ids:
				for parent in parent_ids:
					employee_ids = self.env["hr.employee"].search([('parent_id','child_of',parent.id)])
					emp_ids = []
					if employee_ids:
						for emp in employee_ids:
							absent_ids = self.env['ax.leave'].search([('from_date','<=',datetime.now().date()),
								('state','=','confirm'),('is_leave_applied','=',False),('employee_id','=',emp.id)])
							for leave in absent_ids:
								leave_id = self.env['hr.leave'].search([('employee_id','=',leave.employee_id.id),
									('request_date_from','=',leave.from_date)])
								if leave_id:
									leave.is_leave_applied = True
								else:
									if emp not in emp_ids:
										emp_ids.append(emp)
						if emp_ids != []:
							context = {
								'email_to':parent.user_id.email,
								'email_from':self.env.company.erp_email,
								'subject': "System Notification: Leave Update Required for Employees",
								'emp_ids':emp_ids,
							}
							template = self.env['ir.model.data'].get_object('ax_holidays', 'email_template_manager_absent_alert')
							self.env['mail.template'].browse(template.id).with_context(context).send_mail(parent.id,force_send=True)

	def get_absent_dates(self,emp):
		if emp:
			dates = []
			absent_ids = self.env['ax.leave'].search([('from_date','<=',datetime.now().date()),
				('state','=','confirm'),('is_leave_applied','=',False),('employee_id','=',emp.id)])
			for leave in absent_ids:
				leave_id = self.env['hr.leave'].search([('employee_id','=',leave.employee_id.id),
					('request_date_from','=',leave.from_date)])
				if not leave_id:
					dates.append(leave.from_date)
			return dates
		
	@api.onchange('parent_id')
	def _onchange_manager_approver(self):
		self.leave_manager_id = self.parent_id.user_id.id
			