# -*- coding: utf-8 -*-
{
    'name': 'Force Delete Records',
    'version': '19.0.1.0.0',
    'category': 'Tools/Technical',
    'summary': 'Forced permanent deletion of locked records (Manufacturing Orders, Transfers, Invoices, Orders) with relational cleanup',
    'description': """
Force Delete Custom Module
==========================
Allows authorized users to safely and forcefully delete locked records (such as completed / done Manufacturing Orders,
validated stock transfers, cancelled orders, and journal entries) bypassing standard state restrictions.

Key Capabilities:
-----------------
1. **Actions Menu Integration**:
   * Appears directly under the 'Actions' dropdown menu on list and form views (e.g. Manufacturing Orders).
   * Restricted by default to authorized Administrators ('Allow Force Delete Records').

2. **Interactive Confirmation Wizard**:
   * Shows a clear breakdown of selected records, states, and counts.
   * Prompts for confirmation before permanent execution.
   * Optional toggle to revert physical inventory (quants) for done manufacturing orders or pickings.
   * Optional toggle to purge linked chatter messages, activities, and attachments.

3. **Complete Relational Cleanup**:
   * **Manufacturing Orders (`mrp.production`)**: Reverts finished goods and consumed components (optional), unlinks quality checks (`quality.check`), work orders (`mrp.workorder`), time productivity logs, scraps, stock move lines, and stock moves cleanly.
   * **Inventory Transfers (`stock.picking`)**: Unlinks move lines, moves, and resets associated documents.
   * **Purchase Orders (`purchase.order`)** & **Sales Orders (`sale.order`)**: Unlinks orders and linked delivery/receipt lines.
   * **Invoices / Journal Entries (`account.move`)**: Unlinks moves and lines.

4. **Audit Trail**:
   * Logs every force deletion with timestamp, responsible user, record identifiers, and action details in **Force Delete Audit Logs**.
    """,
    'author': 'Techvizor',
    'depends': [
        'base',
        'mail',
        'stock',
        'mrp',
        'purchase',
        'sale',
        'account',
    ],
    'data': [
        'security/force_delete_security.xml',
        'security/ir.model.access.csv',
        'wizard/force_delete_wizard_views.xml',
        'views/force_delete_actions.xml',
        'views/force_delete_views.xml',
        'views/res_users_views.xml',
        'views/force_delete_log_views.xml',
        'views/force_delete_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
