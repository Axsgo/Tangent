from odoo import fields,api,models

class Company(models.Model):
	_inherit = "res.company"

	erp_email = fields.Char("ERP Email")
	company_seal = fields.Binary("Company Seal")
	# company_footer = fields.Binary("Company Footer")