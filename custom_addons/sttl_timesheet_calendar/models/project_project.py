# -*- coding: utf-8 -*-
from odoo import fields, models

class ProjectProject(models.Model):
    _inherit = 'project.project'
    
    stage_id = fields.Many2one("hr.timesheet.status",'Stages',order='sequence asc')
        