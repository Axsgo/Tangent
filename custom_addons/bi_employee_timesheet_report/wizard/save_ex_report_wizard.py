# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class save_ex_report_wizard(models.TransientModel):
    _name = 'save.ex.report.wizard'
    _description = "save_ex_report_wizard"

    file_name = fields.Binary('Excel Report File')
    document_frame = fields.Char('File To Download')
