# -*- coding: utf-8 -*-
{
    'name': 'Contact Sales & Purchase Classification',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Add Sales and Purchase checkbox buttons to Contact form to filter contacts across CRM, Sales, and Purchase',
    'description': """
Contact Sales & Purchase Classification
=======================================
- Adds Sales and Purchase checkbox buttons on the Contact form.
- When 'Sales' is checked, the contact is available in CRM and Sales modules.
- When 'Purchase' is checked, the contact is available in the Purchase module.
- If both are checked, the contact is available in Sales, CRM, and Purchase.
- Strict isolation: Contacts checked only for Sales will never show in Purchase; contacts checked only for Purchase will never show in Sales or CRM.
    """,
    'author': 'Photokina Chemicals',
    'depends': ['base', 'sale', 'purchase', 'crm'],
    'data': [
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/crm_lead_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

