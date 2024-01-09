# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Project Estimation',
    'version' : '14.0',
    'sequence': 2,
    'category': 'Project',
    'summary':"""This module customized project form""",
    'description': """Project Estimation Calculation""",
    'depends' : ['base', 'project'],
    'data': [
        'views/project_project_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
