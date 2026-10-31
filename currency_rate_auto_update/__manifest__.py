# -*- coding: utf-8 -*-
{
    'name': 'Automatic Daily Currency Rates Sync',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Currencies',
    'summary': 'Automatic daily live exchange rate sync for USD, EUR, etc. against company currency (INR)',
    'description': """
Automatic Daily Currency Rates Sync
===================================
* Automatically updates foreign exchange rates daily using European Central Bank / Live API.
* Keeps USD ➔ INR rates accurate and up-to-date every day.
* Provides manual 'Sync Live Rates Now' buttons in Settings and on the Currencies screen.
* Supports automatic fallback provider for 100% uptime reliability.
    """,
    'author': 'Photokina Chemicals',
    'depends': ['base', 'account'],
    'data': [
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
        'views/res_currency_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

