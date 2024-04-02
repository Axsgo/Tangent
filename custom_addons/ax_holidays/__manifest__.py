{
    'name': 'Axsgo Time Off',
    'version': '0.1',
    'Summary': ' Time Off/Leaves',
    'author': 'Prashanna',
    'description': 'Time Off/Leaves',
    'website': '',
    'category': 'hr_holidays',
    'data': [
    'ir.model.access.csv',
    'ax_leave_form_view.xml',
    'ax_employee_view.xml',
    'ex_leave_report.xml'
    ],
    'depends': ['base','hr','hr_holidays','ax_groups','ax_base','sttl_timesheet_calendar'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
