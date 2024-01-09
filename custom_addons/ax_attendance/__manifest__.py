{
    'name': 'Axsgo Attendance Timesheet',
    'version': '0.1',
    'Summary': 'Attendance Timesheet',
    'author': 'Prashanna',
    'description': 'Attendance Timesheet',
    'website': '',
    'category': 'hr_attendance',
    'data': [
    'ir.model.access.csv',
    'ax_attendance_view.xml',
    ],
    'depends': ['base','hr','hr_attendance','ax_base','ax_groups'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
