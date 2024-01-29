# -*- coding: utf-8 -*-
from odoo import fields, models, api

class ProjectProject(models.Model):
	_inherit = 'project.project'

	def _domain_stages(self):
		if self.user_has_groups('ax_groups.admin_user_group'):
			return [('for_admin', '=', True)]
		else:
			return [('for_admin', '!=', True)]
		return []

	stage_id = fields.Many2one("hr.timesheet.status",'Stages',order='sequence asc', domain=_domain_stages)
	timesheet_count = fields.Integer("Timesheet Count",compute="_get_timesheet_count")

	@api.depends('timesheet_ids')
	def _get_timesheet_count(self):
		for rec in self:
			if rec.timesheet_ids:
				rec.timesheet_count = len(rec.timesheet_ids)
			else:
				rec.timesheet_count = 0