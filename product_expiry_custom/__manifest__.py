# -*- coding: utf-8 -*-
{
    'name': 'Product Expiry Date',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Expiry date management, FEFO/FIFO customer delivery, price and expiry filters',
    'description': """
Product Expiry Date Management
==============================
1. Auto-enables expiration date tracking with 365 days default shelf life for all lot/serial tracked products.
2. Direct Expiration Date display and edit on Manufacturing Orders (MO).
3. Detailed Operations on Purchase Receipts with auto-filled expiry dates.
4. Automatic FEFO (First Expiry First Out) removal strategy for customer deliveries.
5. Exact Purchase Order Line Unit Price and PO reference tracking on Lots / Serial Numbers.
6. Color-coded Expiration Dates (Red for expired, Orange for expiring soon).
7. List and search filters for Expiry Date and Price/Cost on Products, Lots/Serial Numbers, and Stock Quants.
    """,
    'author': 'Photokina Chemicals',
    'depends': ['product', 'stock', 'product_expiry', 'mrp', 'mrp_product_expiry', 'purchase', 'purchase_stock'],
    'data': [
        'views/product_views.xml',
        'views/mrp_production_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_lot_views.xml',
        'views/stock_quant_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
