# -*- coding: utf-8 -*-
{
    'name': 'Product Expiry Date',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Add direct expiry date field on product template and variant, with lot expiry tracking',
    'description': """
Product Expiry Date Management
==============================
This module provides:
1. Direct 'Expiry Date' field on Product Template and Product Variant forms under the 'General Information' tab.
2. Expiry Date display in Product list/tree views.
3. Expiry Date grouping and search in Product views.
4. Full integration with Odoo standard lot-based expiration tracking (product_expiry).
    """,
    'author': 'Photokina Chemicals',
    'depends': ['product', 'stock', 'product_expiry'],
    'data': [
        'views/product_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
