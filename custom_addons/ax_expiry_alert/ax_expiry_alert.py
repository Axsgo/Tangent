from odoo import fields,models,api
import time

class AxExpiryAlerts(models.Model):
	_name = "ax.expiry.alert"
	_description = "Expiry Alerts"
	_inherit = ['mail.thread', 'mail.activity.mixin']

	name = fields.Char("Name")
	# date = fields.Date("Create Date")
	model_id = fields.Many2one("ir.model","Model/Form",tracking=True)
	model_name = fields.Char("Model Name",compute='_get_model_name')
	field_id = fields.Many2one("ir.model.fields","Date Field",tracking=True)
	alert_condition = fields.Selection([('before','Before'),('after','After'),('same','Same Day')],'Alert Condition',tracking=True)
	alert_on = fields.Integer("Alert On",default=0,tracking=True)
	alert_period = fields.Selection([('days','Days'),('weeks','Weeks'),('months','Months')],'Alert Period',tracking=True)
	alert_subject = fields.Char("Subject",tracking=True)
	alert_domain = fields.Char("Domain",tracking=True)
	doc_name = fields.Char("Document Name",tracking=True)
	# alert_msg = fields.Html("Alert Message")
	default_email_to = fields.Char("Default Email To",tracking=True)
	email_to_user_id = fields.Many2one("ir.model.fields","Email To User",tracking=True)
	default_email_cc = fields.Char("Default Email CC",tracking=True)
	notes = fields.Text("Notes")
	company_id = fields.Many2one('res.company','Company',default = lambda self: self.env.company.id)
	state = fields.Selection([('draft','Draft'),('approved','Approved'),('cancel','Cancelled')],'Status',default='draft',tracking=True)

	def unlink(self):
		""" Unlink """
		for rec in self:
			if rec.state != 'draft':
				raise UserError('Warning!, You can not delete this entry !!')
			else:
				return super(AccExpiryAlerts, self).unlink()

	@api.depends('model_id')
	def _get_model_name(self):
		for rec in self:
			if rec.model_id:
				rec.model_name = rec.model_id.model
			else:
				rec.model_name = ''

	def entry_draft(self):
		self.write({'state': 'draft'})

	def entry_approve(self):
		if self.state == 'draft':
			if self.alert_condition != 'same' and self.alert_on == 0:
				raise UserError("Warning!!, Alert On Days should be greater than 0.")
			self.write({'state': 'approved'})

	def entry_cancel(self):
		self.write({'state': 'cancel'})

	def _parse_alert_domain(self):
		from ast import literal_eval
		self.ensure_one()
		try:
			mailing_domain = literal_eval(self.alert_domain)
		except Exception:
			mailing_domain = [('id', 'in', [])]
		return mailing_domain

	def _entry_send_expiry_alerts(self):
		from datetime import datetime
		from dateutil.relativedelta import relativedelta
		alert_ids = self.env['ax.expiry.alert'].search([('state','=','approved'),('company_id','=',self.env.company.id)])
		if alert_ids:
			for res in alert_ids:
				alert_domain = res._parse_alert_domain()
				res_ids = self.env[res.model_name].search(alert_domain)
				for line in res_ids:
					data = line.read([res.field_id.name])
					if data[0][res.field_id.name] != False:
						alert_date = False
						if res.alert_condition == 'before':
							if res.alert_period == 'days':
								alert_date = data[0][res.field_id.name] - relativedelta(days=res.alert_on)
							elif res.alert_period == 'weeks':
								alert_date = data[0][res.field_id.name] - relativedelta(days=(res.alert_on*7))
							else:
								alert_date = data[0][res.field_id.name] - relativedelta(months=res.alert_on)
						elif res.alert_condition == 'after':
							if res.alert_period == 'days':
								alert_date = data[0][res.field_id.name] + relativedelta(days=res.alert_on)
							elif res.alert_period == 'weeks':
								alert_date = data[0][res.field_id.name] + relativedelta(days=(res.alert_on*7))
							else:
								alert_date = data[0][res.field_id.name] + relativedelta(months=res.alert_on)
						else:
							alert_date = data[0][res.field_id.name]
						if datetime.now().date() == alert_date:
							email_to = ''
							if res.email_to_user_id.model_id.model == 'hr.employee':
								emp_id = line.read([res.email_to_user_id.name])[0][res.email_to_user_id.name][0]
								emp_id = self.env['hr.employee'].browse(int(emp_id))
								user_id = emp_id.user_id
							else:
								user_id = line.read([res.email_to_user_id.name])[0][res.email_to_user_id.name][0]
								user_id = self.env['res.users'].browse(int(user_id))
							if user_id:
								email_to = str(user_id.email) if user_id.email else ''
								if res.default_email_to != '':
									if email_to != '':
										email_to += ','
									email_to += res.default_email_to
								context = {
									'email_to':email_to,
									'email_cc':res.default_email_cc,
									'alert_id':res,
									'res_id':line,
									'email_from':self.env.company.erp_email,
									'name':user_id.name,
									'expiry_date':data[0][res.field_id.name],
									'doc_no':line.name,
								}
								template = self.env['ir.model.data'].get_object('acc_masters', 'email_template_acc_expiry_alerts')
								self.env['mail.template'].browse(template.id).with_context(context).send_mail(res.id,force_send=True)