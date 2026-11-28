# -*- coding: utf-8 -*-
{
    'name': 'Photokina Dispatch Dashboard',
    'version': '19.0.1.0.0',
    'summary': 'Real-time Dispatch & Delivery Performance Dashboard',
    'description': """
        Photokina Dispatch Dashboard:
        - 5 Clickable KPI Cards (Total Orders, On-Time, Late, On-Time %, Late %)
        - Delivery Performance Donut Chart
        - Delay Buckets Bar Chart
        - On-Time Delivery detailed table with filters and CSV export
        - Full-width modern responsive layout with in-header tabs
    """,
    'author': 'Photokina Chemicals',
    'category': 'Sales/Logistics',
    'depends': ['base', 'sale', 'stock', 'web'],
    'data': [
        'views/dispatch_dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'photokina_dispatch/static/src/css/dispatch_dashboard.css',
            'photokina_dispatch/static/src/xml/dispatch_dashboard.xml',
            'photokina_dispatch/static/src/js/dispatch_dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
