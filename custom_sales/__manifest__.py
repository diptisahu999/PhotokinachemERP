# -*- coding: utf-8 -*-
{
    'name': 'Custom Sales',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Custom Sales Enhancements - Preview button in Quotations list view',
    'description': """
Custom Sales Enhancements
=========================
* Adds a Preview button to the Quotations / Sales Orders list view,
  matching the Preview button already available in the form view.
    """,
    'author': 'Techvizor',
    'depends': [
        'sale_management',
    ],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

