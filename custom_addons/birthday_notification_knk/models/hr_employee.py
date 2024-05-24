# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>)

from odoo import api, fields, models


class HrEmployee(models.Model):
	_inherit = "hr.employee"

	@api.model
	def send_birthday_notification(self):
		today = fields.Date.context_today(self)
		for employee in self.env['hr.employee'].search([('birthday', '!=', False), ('work_email', '!=', False)]):
			if employee.company_id.send_employee_birthday_notification and (today.day == employee.birthday.day) and (today.month == employee.birthday.month):
				employee_ids = self.env['hr.employee'].search([('id','!=',employee.id)])
				ctx = {'email_cc':','.join([x.work_email for x in employee_ids if x.work_email])}
				template_id = self.env.ref('birthday_notification_knk.employee_birthday_notification_template')
				template_id.with_context(ctx).send_mail(employee.id, force_send=True)
