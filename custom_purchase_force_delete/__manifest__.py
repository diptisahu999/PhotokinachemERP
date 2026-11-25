# -*- coding: utf-8 -*-
{
    'name': 'Force Delete Purchase Orders',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Forcefully delete confirmed, approved, or draft Purchase Orders and cascade clean up dependencies',
    'description': """
Force Delete Purchase Orders
============================
Allows authorized administrators and managers to forcefully and permanently delete Purchase Orders:
* Bypasses standard restrictions ('In order to delete a purchase order, you must cancel it first').
* Bypasses PO Line restrictions ('Cannot delete a purchase order line which is in state Purchase Order').
* Provides 'Force Delete Purchase Order(s)' in the Actions (⚙) dropdown on the list view.
* Provides a 'Force Delete' button on the Purchase Order form view header.
* Confirmation wizard shows summary of selected orders and linked Receipts, Stock Moves, Quality Checks, and Vendor Bills.
* Safely cascades cleanup of dependencies before deleting.
* Dedicated Security Group: 'Allow Force Delete Purchase Orders' with user toggle in Settings -> Users.
    """,
    'author': 'Techvizor',
    'depends': [
        'base',
        'purchase',
        'stock',
        'purchase_approval',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/purchase_force_delete_wizard_views.xml',
        'views/purchase_order_actions.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
