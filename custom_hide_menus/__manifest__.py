# -*- coding: utf-8 -*-
{
    'name': 'Hide Unwanted Menus & App Module Access Control',
    'version': '19.0.1.0.3',
    'category': 'Extra Tools',
    'summary': 'Hides Project, Link Tracker, Surveys, and adds Apps Module Access control toggle/button on User form',
    'description': """
Hide Unwanted Menus & App Module Access Control
================================================
This module customizes navigation and application visibility for Photokina Chemicals ERP:

1. **Hide Unused Modules from Sidebar/Navigation**:
   - Hides **Project** (`project.menu_main_pm`)
   - Hides **Link Tracker** (`utm.menu_link_tracker_root`)
   - Hides **Surveys** (`survey.menu_surveys`)

2. **Per-User Apps Module Access Control**:
   - Adds **Apps Module Access** toggle (`has_apps_access`) under **Access Rights** tab on the User form (`res.users`).
   - Adds a **Toggle Apps Access** action button in the User form header.
   - Hides the **Apps** icon from the sidebar for standard users unless granted access.
   - System Administrators retain full Apps access by default.
    """,
    'author': 'Photokina Chemicals Pvt. Ltd.',
    'website': 'https://www.photokinachem.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'project',
        'utm',
        'survey',
        'custom_ticket_monitoring',
    ],
    'data': [
        'security/security.xml',
        'views/hide_menus.xml',
        'views/res_users_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
