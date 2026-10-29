# -*- coding: utf-8 -*-
{
    'name': 'Sale Delivery Terms & Address Customization',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Add Delivery Address under Customer and Delivery Terms under Payment Terms with dropdown create option',
    'description': """
Sale Delivery Customization
===========================
1. Delivery Address:
   - Positioned directly below the Customer field.
   - Filtered to strictly show only the selected customer and its sub-contacts (delivery, invoice, contact, etc.).
   - No unrelated contacts or other customers are shown.

2. Delivery Terms:
   - Dynamic Many2one field allowing selection and on-the-fly creation of new delivery terms.
   - Positioned on the main quotation/order page directly below Payment Terms.
   - Updates and syncs with the underlying Shipping Policy in the Delivery section.
   - Preloaded with standard terms (As soon as possible, When all products are ready, Ex-Works, Door Delivery, etc.).
   - Accessible and manageable under Sales -> Configuration -> Delivery Terms.
    """,
    'author': 'Photokina Chemicals',
    'depends': ['sale', 'sale_stock', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/delivery_term_data.xml',
        'views/delivery_term_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

