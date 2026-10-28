# -*- coding: utf-8 -*-
{
    'name': 'Pending Sales Dispatches',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Dedicated page for confirmed sales orders with pending deliveries (Waiting & Ready)',
    'description': """
Pending Sales Dispatches
========================
Provides a dedicated listing page for sales orders with remaining deliveries:
- Lists only outgoing Delivery Orders in Waiting or Ready state for confirmed Sale Orders.
- Excludes cancelled, completed, and draft orders.
- Accessible from both:
    1. Sales -> Orders -> Pending Dispatches
    2. Inventory -> Operations -> Transfers -> Pending Sales Dispatches
- Includes quick filters for Ready to Dispatch and Waiting (Pending Availability).
    """,
    'author': 'Photokina Chemicals',
    'depends': ['sale_management', 'stock', 'sale_stock'],
    'data': [
        'views/sales_dispatch_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

