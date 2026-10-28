# -*- coding: utf-8 -*-
{
    'name': 'Zone-wise CRM & Sales Pipeline Segregation',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Segregate CRM Leads and Sales Orders by Geographical Zones using Sales Teams',
    'description': """
Zone-wise Segregation in Odoo CRM & Sales Pipeline
===================================================
This module implements geographical Zone-wise segregation across the CRM Pipeline and Sales Orders:
* Utilizes Odoo Sales Teams (crm.team) as Zones (e.g. North Zone, South Zone, East Zone, West Zone).
* Zone Managers & Sales Reps: Restrict users to viewing and managing Leads/Opportunities and Quotations/Orders within their assigned Zone(s).
* Pipeline-Only Segregation: CRM Leads and Sales Orders are segregated per Zone, while customer master records remain visible across all reps.
* Auto-Routing: Automatically suggest and assign Zone based on Customer State/Country or Customer Default Zone.
* Security Group: Adds 'User: Own Zone / Team Documents Only' between 'Own Documents Only' and 'All Documents'.
* Zone Dashboard & Filters: Quick filters and group-by options in CRM Kanban and Sales Orders for easy Zone tracking.
    """,
    'author': 'Techvizor',
    'depends': [
        'crm',
        'sale_management',
    ],
    'data': [
        'security/crm_sale_zone_security.xml',
        'security/ir.model.access.csv',
        'views/crm_team_views.xml',
        'views/crm_lead_views.xml',
        'views/sale_order_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
