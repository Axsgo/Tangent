# -*- coding: utf-8 -*-

{
    'name': 'Axsgo Database Auto Backup',
    'author': 'Prashanna',
    'summary': 'Axsgo Database auto backup application',
    'version': '1.0',
    'license': 'OPL-1',
    'category': 'Tools',
    'description': """
Database Auto Backup

Install Curl -- sudo apt install curl
========
""",
    'depends': ['web'],
    'data': [
        'security/ir.model.access.csv',
        'data/autobackup_cron.xml',
        'data/autobackup_data.xml',
        'views/autobackup_config_settings_views.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
