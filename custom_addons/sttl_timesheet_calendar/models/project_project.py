# -*- coding: utf-8 -*-
from odoo import fields, models

class ProjectProject(models.Model):
    _inherit = 'project.project'
    
    def _domain_stages(self):
        if self.user_has_groups('ax_groups.admin_user_group'):
            return [('for_admin', '=', True)]
        else:
            return [('for_admin', '!=', True)]
        return []
    
    stage_id = fields.Many2one("hr.timesheet.status",'Stages',order='sequence asc', domain=_domain_stages, readonly=True)
        