# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name': "HR Employee Timesheet Excel and PDF Report in Odoo",
    'version': '14.0.0.1',
    'category': 'Human Resources',
    'summary': "Print Employee timesheet report print timesheet report download employee timesheet pdf report export timesheet excel employee timesheet excel report download timesheet report for employee attendance report daily timesheet report daily employee timesheets",
    'description': ''' 
		Human Resource Employee Timesheet PDF and Excel Report Odoo app helps you print PDF and Excel reports of employee timesheets for a specific time period. Users can choose to print timesheet reports for single or multiple employees within a particular date range as per their needs.
    ''',
    'author': 'BrowseInfo',
    "price": 00,
    "currency": 'EUR',
    'website': 'https://www.browseinfo.com',
    'depends': ['base','hr_timesheet'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/time_sheet_select_wizard_view.xml',
        'wizard/save_ex_report_wizard_view.xml',
        'views/timesheet.xml',
        'report/ir.timesheet_report_template.xml',
        'report/ir.timesheet_reoprt.xml',

    ],
    'license':'OPL-1',
    'installable': True,
    'auto_install': False,
    'live_test_url':'https://youtu.be/XbbMY3VBlng',
    "images":['static/description/Employee-Timesheet-Excel-and-PDF-Report-Banner.gif'],
}
