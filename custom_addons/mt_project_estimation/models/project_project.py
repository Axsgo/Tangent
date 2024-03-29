# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError

class ProjectProject(models.Model):
    _inherit = 'project.project'
    
    project_no = fields.Char(string="Project Number", required=True, size=10)
    parent_id = fields.Many2one("project.project",'Parent Project')
    is_sub_project = fields.Boolean("Is Sub Project",compute='_get_sub_project')
    manual_estimation_hrs = fields.Float(string="Project Estimation Hours")
    estimation_hrs = fields.Float(compute='_compute_est_wrk_hours', string="Estimation Hours")
    worked_hrs = fields.Float(compute='_compute_est_wrk_hours', string="Worked Hours")
    remaining_hrs = fields.Float(compute='_compute_est_wrk_hours', string="Remaining Hours")
    deviation_hrs = fields.Float(compute='_compute_est_wrk_hours', string="Deviation Hours")
    
    _sql_constraints = [('project_no_uniq', 'unique(project_no)', 'Project Number should be unique!')]
    
    def _compute_est_wrk_hours(self):
        estimation_hrs=sum(self.tasks.mapped('planned_hours')) or 0
        worked_hrs=sum(self.tasks.mapped('effective_hours')) or 0
        self.estimation_hrs = estimation_hrs
        self.worked_hrs = worked_hrs
        est_rem_hrs = estimation_hrs-worked_hrs
        if est_rem_hrs<0:
            self.remaining_hrs = 0
            self.deviation_hrs = abs(est_rem_hrs)
        else:
            self.remaining_hrs = est_rem_hrs
            self.deviation_hrs = 0

    @api.depends('parent_id')
    def _get_sub_project(self):
        for rec in self:
            if rec.parent_id:
                rec.is_sub_project = True
            else:
                rec.is_sub_project = False

    @api.constrains('parent_id')
    def project_constrains(self):
        if self.id and self.parent_id and self.parent_id.id == self.id:
            raise UserError("Parent Project should not be same as Current Project.")
            
    def name_get(self):
        result = []
        for project in self:
            if project.project_no:
                name = project.project_no  + ' - ' + project.name
            else:
                name = project.name
            result.append((project.id, name))
        return result
    
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if args is None:
            args = []
        domain = args + ['|', ('project_no', operator, name), ('name', operator, name)]
        return self._search(domain, limit=limit, access_rights_uid=name_get_uid)
        