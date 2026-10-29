# -*- coding: utf-8 -*-
{
    'name': 'Custom Sales',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Custom Sales Enhancements - Preview button & Stock Availability in Order Lines',
    'description': """
Custom Sales Enhancements
=========================
* Adds a Preview button to the Quotations / Sales Orders list view.
* Adds On Hand and Forecasted stock availability columns directly
  in the Sale Order lines, with red/green color indicators.
    """,
    'author': 'Techvizor',
    'depends': [
        'sale_management',
        'stock',
    ],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
