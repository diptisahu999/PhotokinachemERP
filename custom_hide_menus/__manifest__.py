# -*- coding: utf-8 -*-
{
    'name': 'Hide Unwanted Menus (Project, Link Tracker, Surveys)',
    'version': '19.0.1.0.1',
    'category': 'Extra Tools',
    'summary': 'Hides Project, Link Tracker, and Surveys apps from the left sidebar and navigation menu',
    'description': """
Hide Unwanted Menus (Project, Link Tracker, Surveys)
====================================================
This module hides the **Project**, **Link Tracker**, and **Surveys** applications from the left sidebar
and navigation menu in Photokina Chemicals ERP:

- Hides **Project** (`project.menu_main_pm`)
- Hides **Link Tracker** (`utm.menu_link_tracker_root`)
- Hides **Surveys** (`survey.menu_surveys`)

All menus are deactivated and restricted to a dedicated internal hidden group.
All backend data, records, and Python APIs remain 100% intact.
    """,
    'author': 'Photokina Chemicals Pvt. Ltd.',
    'website': 'https://www.photokinachem.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'project',
        'utm',
        'survey',
    ],
    'data': [
        'security/security.xml',
        'views/hide_menus.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
