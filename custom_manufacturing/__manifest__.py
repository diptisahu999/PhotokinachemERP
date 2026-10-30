# -*- coding: utf-8 -*-
{
    'name': 'Custom Manufacturing',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing/Manufacturing',
    'summary': 'Manufacturing Orders Components Unit Price, Total Price, Available Quantity, Total Overall Price & BoM Cost Calculation',
    'description': """
Custom Manufacturing Enhancements
==================================
* Shows current available quantity (physical on-hand stock at source location) for each component.
* Shows unit price (smart fallback: Cost > Vendor Price > Sales Price, editable) and total line price.
* Shows total overall component price summary at the bottom right of the Components tab.
* Displays total price column sum in the components table footer.
* Enhances 'Compute Price from BoM' on products to calculate finished goods cost using component prices.
    """,
    'author': 'Techvizor',
    'depends': [
        'mrp',
        'stock',
        'mrp_account',
    ],
    'data': [
        'views/mrp_production_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
