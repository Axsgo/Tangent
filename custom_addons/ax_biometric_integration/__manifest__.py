# -*- coding: utf-8 -*-
{
    'name': 'Biometric Integration v14',
    'version': '1.0',
    'category': 'Company',
    'summary': 'This module integrate Timeinline Biometric to Odoo',
    'description': """This module integrate Timeinline Biometric to Odoo""",
    'depends': ['base','hr_attendance'],
    'data': [
        'data/fetch_attendance_scheduler.xml',
        'views/hr_employee_view.xml',
        'views/res_company_view.xml',
    ],
    'demo': [ ],
    'installable'   : True,
    'application'   : True,
    'auto_install'  : False,
}
