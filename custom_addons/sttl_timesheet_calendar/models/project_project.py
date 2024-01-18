# -*- coding: utf-8 -*-
from odoo import fields, models

class ProjectProject(models.Model):
    _inherit = 'project.project'
    
    stage_id = fields.Many2one("project.task.type",'Stages', copy=False, tracking=True)
        