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
    ],
    'depends': ['base','hr','hr_holidays','ax_groups'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
