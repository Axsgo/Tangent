# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.
{
    'name': 'HR Attendance and Leave Register Report in Odoo',
    'version': '14.0.0.0',
    'category': 'Human Resources',
    'summary': 'HR Employee attendance register report employee leave request Report Human Resource Attendance & Leave Report Human Resource Attendance Leave Report Employee attendance leave request hr attendance report print attendance report print leave register report',
    'description': """The HR Attendance and Leave Register Report Odoo App helps HR managers to keep track of employee attendance and leave requests. The attendance register report provides a detailed overview of employee attendance records, including selected dates and present and absences. The leave register report provides a detailed overview of employee leave records, including the number of days for allocated, utilized, and remaining leave by leave types. User can also generate attendance and leave register report by department and specific employee for selected dates.""",
    'author': "BrowseInfo",
    "website" : "https://www.browseinfo.com",
    'depends': ['base', 'hr', 'hr_holidays', 'hr_attendance'],
    'data': [
            'security/ir.model.access.csv',
            'wizards/attendance_register_wizard.xml',
            'wizards/leave_register_wizard.xml',
            'report/attendance_register_report.xml',
            'report/attendance_register.xml',
            'report/leave_register.xml',
             ],
    'demo': [],
    'css': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'OPL-1',
    'live_test_url':'https://youtu.be/zRrtMOUfQog',
    "images":['static/description/Banner.gif'],
}
