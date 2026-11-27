# -*- coding: utf-8 -*-
{
    'name': 'Custom User Designation & Department',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Master management for User Designations and Sub Departments with dropdown selection and quick creation',
    'description': """
Custom User Designation & Department
====================================
This module provides full master data management for User Designations and Sub Departments:

Key Features:
-------------
1. **Master Data Models (`user.designation` & `user.sub_department`)**:
   - Manage all Designations and Sub Departments with dedicated menus.
   - Includes full list and form views showing assigned users.
   - Pre-populated with standard PCPL company designations and sub-departments.

2. **Dropdown Selection & On-The-Fly Creation**:
   - Select existing designations and sub-departments from an autocomplete dropdown.
   - Directly type and click **"Create"** or **"Create and Edit..."** on the user page.

3. **Menus in Settings**:
   - **Settings → Users & Companies → Designations**
   - **Settings → Users & Companies → Sub Departments**

4. **User Views Integration**:
   - User form view, tree view, search view, kanban view, and quick create dialog.
    """,
    'author': 'Techvizor Pvt. Ltd.',
    'website': 'https://www.photokinachem.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/user_designation_data.xml',
        'views/user_designation_views.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
