# Part of Ventor modules. See LICENSE file for full copyright and licensing details.

{
    'name': 'Timesheet Calendar',
    'version': '14.0.1.0',
    'author': 'Silver Touch Technologies Limited',
    'website': 'https://www.silvertouch.com',
    'license': 'LGPL-3',
    'support': 'service@silvertouch.com',
    'category': 'Analytic',
    'summary': 'Allows to Fill timesheet from calender view',
    'price': 00,
    'currency': 'EUR',
    'depends': [
        'base','resource','hr_timesheet','ax_base','mt_project_estimation','web'
    ],
    'data': [
        'data/timesheet_submission_scheduler.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/hr_timesheet_view.xml',
        'views/hr_timesheet_submit_view.xml',
        'views/project_project_view.xml',
        'views/hr_timesheet_submit_report_view.xml',
        'views/project_profit_report_view.xml',
        'views/hr_employee_view.xml',
    ],
    'qweb': [
        "static/src/xml/web_calendar.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/banner.gif'],
}