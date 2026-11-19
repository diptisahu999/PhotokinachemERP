# -*- coding: utf-8 -*-
{
    'name': 'Purchase Approval',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'User-Level Purchase Approval permission and workflow for RFQs and POs',
    'description': """
Purchase Approval Workflow
==========================
This module introduces user-level permission and an approval workflow for Purchases:

Key Features:
-------------
1. **User-Level Purchase Approval Permission**:
   * Add 'Purchase Approval' boolean toggle directly on User accounts (Settings -> Users).
   * Only users with 'Purchase Approval' allowed can approve or reject purchase requests.

2. **Simplified Purchase Page**:
   * Clean RFQ / Purchase page without cluttered individual approver selection.
   * Purchasers simply click "Send for Purchase Approval".

3. **Approval & Rejection Actions**:
   * Authorized users see "Approve Purchase" and "Reject" buttons.
   * Approving confirms the order into an active Purchase Order (PO).
   * Rejecting opens a wizard to record a mandatory reason.

4. **Sidebar Navigation**:
   * "Purchase Approval" appears directly in the sidebar for rapid access.
    """,
    'author': 'Techvizor',
    'depends': [
        'base',
        'purchase',
        'mail',
    ],
    'data': [
        'security/purchase_approval_security.xml',
        'security/ir.model.access.csv',
        'data/mail_activity_type_data.xml',
        'wizard/purchase_approval_reject_wizard_views.xml',
        'views/res_users_views.xml',
        'views/purchase_order_views.xml',
        'views/purchase_approval_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
