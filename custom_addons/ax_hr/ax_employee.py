from odoo import fields,api,models

class HREmployee(models.Model):
	_inherit = "hr.employee"

	passport_expire =  fields.Date("Passport Expire Date",copy=False)
	permit_expire = fields.Date("Labour Card Expire",copy=False)
	emergency_mobile = fields.Char("Emergency Mobile")

class HREmployeePublic(models.Model):
	_inherit = "hr.employee.public"

	passport_expire =  fields.Date("Passport Expire Date",copy=False)
	permit_expire = fields.Date("Labour Card Expire",copy=False)
	emergency_mobile = fields.Char("Emergency Mobile")