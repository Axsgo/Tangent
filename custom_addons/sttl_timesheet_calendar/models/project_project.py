# -*- coding: utf-8 -*-
from odoo import fields, models, api, SUPERUSER_ID


class ProjectProject(models.Model):
	_inherit = 'project.project'
	
	stage_id = fields.Many2one("hr.timesheet.status",'Stages',order='sequence asc',domain="[('project_ids', '=', id)]")
	allowed_stage_ids = fields.Many2many("hr.timesheet.status",'allowed_stage_project_rel',string='Stages',order='sequence asc')
	timesheet_count = fields.Integer("Timesheet Count",compute="_get_timesheet_count")
	timesheet_duration = fields.Float("Timesheet Durations(HH:MM)",compute="_get_timesheet_duration")
	is_project_start_mail_sent = fields.Boolean("Project Start Mail Sent?",default=False,copy=False)
	
	@api.onchange('allowed_stage_ids')
	def onchange_project_id(self):
		self.stage_id = False
		res = {'domain': {'stage_id': "[('id', 'not in', False)]"}}
		res['domain']['stage_id'] = "[('id', 'in', %s)]" % self.allowed_stage_ids.ids
		return res

	@api.depends('timesheet_ids')
	def _get_timesheet_count(self):
		for rec in self:
			if rec.timesheet_ids:
				rec.timesheet_count = len(rec.timesheet_ids)
			else:
				rec.timesheet_count = 0
				
	@api.depends('timesheet_ids')
	def _get_timesheet_duration(self):
		for rec in self:
			if rec.timesheet_ids:
				rec.timesheet_duration = sum([x.unit_amount for x in rec.timesheet_ids])
			else:
				rec.timesheet_duration = 0
				
