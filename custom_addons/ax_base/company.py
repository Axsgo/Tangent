from odoo import fields,api,models
from datetime import datetime
from dateutil.relativedelta import relativedelta

class Company(models.Model):
	_inherit = "res.company"

	erp_email = fields.Char("ERP Email")
	company_seal = fields.Binary("Company Seal")
	## timesheet
	timesheet_working_hrs = fields.Float("Working Hours(HH:MM)",default=9)
	timesheet_manager_alert = fields.Integer("No of days interval for sending email notification to manager",default=15)
	timesheet_manager_nxt_date = fields.Date("Next Date")
	timesheet_admin_alert = fields.Integer("No of days interval for sending email notification to admin",default=30)
	timesheet_admin_nxt_date = fields.Date("Next Date")
	## leave
	absent_manager_alert = fields.Integer("No of days interval for sending email notification to manager",default=15)
	absent_manager_nxt_date = fields.Date("Next Date")
	#attendance
	attend_work_hrs = fields.Float("Login Hours(HH:MM)",default=0)

	@api.onchange("timesheet_manager_alert")
	def update_timesheet_manager_nxt_date(self):
		if self.timesheet_manager_alert > 0:
			self.timesheet_manager_nxt_date = datetime.now().date() + relativedelta(days=self.timesheet_manager_alert)
		else:
			self.timesheet_manager_nxt_date = datetime.now().date()

	@api.onchange("timesheet_admin_alert")
	def update_timesheet_admin_nxt_date(self):
		if self.timesheet_admin_alert > 0:
			self.timesheet_admin_nxt_date = datetime.now().date() + relativedelta(days=self.timesheet_admin_alert)
		else:
			self.timesheet_admin_nxt_date = datetime.now().date()

	@api.onchange("absent_manager_alert")
	def update_leave_manager_nxt_date(self):
		if self.absent_manager_alert > 0:
			self.absent_manager_nxt_date = datetime.now().date() + relativedelta(days=self.absent_manager_alert)
		else:
			self.absent_manager_nxt_date = datetime.now().date()