# -*- coding: utf-8 -*-
{
    'name': 'Product Expiry Date',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Expiry date management across Products, Purchase Receipts, and Manufacturing Orders',
    'description': """
Product Expiry Date Management
==============================
1. Auto-enables expiration date tracking with 365 days default shelf life for all lot/serial tracked products.
2. Directly view and edit Expiration Date on Manufacturing Orders (MO) when producing finished goods.
3. Detailed Operations tab and auto-fill expiry date on Purchase Receipts / Stock Pickings.
4. Product Template & Variant Expiry Date fields and views.
    """,
    'author': 'Photokina Chemicals',
    'depends': ['product', 'stock', 'product_expiry', 'mrp', 'mrp_product_expiry'],
    'data': [
        'views/product_views.xml',
        'views/mrp_production_views.xml',
        'views/stock_picking_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
