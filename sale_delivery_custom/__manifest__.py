# -*- coding: utf-8 -*-
{
    'name': 'Sale Delivery Terms, Address, Transporter & Bank Customization',
    'version': '19.0.1.1.0',
    'category': 'Sales/Sales',
    'summary': 'Delivery Address, Delivery Terms, Transporter Details (Part B) and Company Bank Details on Quotation and Reports',
    'description': """
Sale Delivery & Quotation Customization
========================================
1. Delivery Address:
   - Positioned directly below the Customer field.
   - Filtered to strictly show only the selected customer and its sub-contacts.

2. Delivery Terms:
   - Dynamic Many2one field positioned directly below Payment Terms.
   - Updates and syncs with Shipping Policy in the Delivery section.

3. Transporter & Transportation Details (Part B):
   - Transporter details and full Part B logistics details (Mode, Vehicle Type, Vehicle Number, Distance, Transporter Doc No/Date).
   - Positioned under the 'Other Info' tab in the quotation/sales order.
   - Synced to delivery transfers (stock.picking) and e-Waybill on confirmation.
   - Displayed clearly in the Quotation PDF report.

4. Company Bank Details:
   - Company bank account selection on the Quotation ('Other Info' -> Invoicing).
   - Automatically defaults to the company's registered bank account.
   - Shows Bank Name, Account Number, IFSC/BIC, and Beneficiary Name in the Quotation PDF report.
    """,
    'author': 'Photokina Chemicals',
    'depends': ['sale', 'sale_stock', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/delivery_term_data.xml',
        'views/delivery_term_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'report/sale_report_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
