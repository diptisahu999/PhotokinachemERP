# -*- coding: utf-8 -*-
{
    'name': 'Lost Customer Management',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Auto-tag lost customers (no orders/deals in 6 months) and display warning in quotations',
    'description': """
Lost Customer Management
========================
1. Automatically identifies customers with no deals or confirmed sale orders in the last 6 months (180 days).
2. Automatically attaches a prominent 'Lost Customer' tag to the customer contact.
3. Daily automated scheduler (cron) scans and updates customer status.
4. On Quotations and Sales Orders, displays a prominent 'Lost Customer' alert banner and badge when creating an order for a lost customer.
5. Automatically reactivates the customer (clears the lost tag) once a new quotation is confirmed.
6. Search filters and grouping for Lost vs Active customers.
    """,
    'author': 'Photokina Chemicals',
    'depends': [
        'base',
        'sale_management',
        'crm',
    ],
    'data': [
        'data/lost_customer_data.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

