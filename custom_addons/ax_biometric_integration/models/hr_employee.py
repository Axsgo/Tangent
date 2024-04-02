from odoo import fields, models


class HREmployee(models.Model):
	_inherit = "hr.employee"
	
	bio_code = fields.Char('Biometric Code')
	missing_count = fields.Integer('Missing Count', default=0)
	

class HREmployeePublic(models.Model):
	_inherit = "hr.employee.public"
	
	bio_code = fields.Char('Biometric Code')
	missing_count = fields.Integer('Missing Count', default=0)
	