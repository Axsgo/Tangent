from odoo import fields, models


class HREmployee(models.Model):
	_inherit = "hr.employee"
	
	bio_code = fields.Char('Biometric Code')
	