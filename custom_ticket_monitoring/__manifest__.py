# -*- coding: utf-8 -*-
{
    'name': 'PCPL Task Delegation System',
    'version': '19.0.1.0.0',
    'category': 'Operations/Task Delegation',
    'summary': 'Centralized operational task delegation, issue tracking, SLA monitoring, L1-L4 escalation, and management dashboard across 13 departments for PCPL',
    'description': """
PCPL Task Delegation System
===========================
Department-wise task delegation, service levels, and management dashboard for Photokina Chemicals Pvt. Ltd.

Key Capabilities:
-----------------
1. Centralized Issue Management across 13 Departments (Sales, Production, QA/QC, Purchase, Stores, Dispatch, Finance, HR & Admin, Maintenance, IT, R&D, Management, MIS).
2. All 16 Mandatory Data Fields as per PCPL Operational Framework.
3. Automated Priority & SLA Target Engine (P1-Critical: 2h, P2-High: 4h, P3-Medium: 24h, P4-Low: 48h).
4. 4-Tier Escalation Hierarchy (L1 Assignee -> L2 HOD at 75% SLA -> L3 GM on breach -> L4 CEO/MD on critical impact).
5. 6-Tier Role-Based Access Control (Employee, Owner, HOD, GM, CEO/MD, Administrator).
6. 8-Step Lifecycle with mandatory Requester Verification, Reopen tracking, and 5-Star Satisfaction rating.
7. Dedicated MIS Department tracking (Tally, Google Sheets, ERP reconciliations, formula errors, KPI reporting).
8. 15 Core KPIs Management Dashboard & Departmental SLA Compliance Scorecards.
    """,
    'author': 'Photokina Chemicals Pvt. Ltd.',
    'website': 'https://www.photokinachem.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
    ],
    'data': [
        'security/ticket_security.xml',
        'security/ir.model.access.csv',
        'data/ticket_sequence_data.xml',
        'data/ticket_stage_data.xml',
        'data/ticket_department_data.xml',
        'data/ticket_category_data.xml',
        'data/ticket_cron_data.xml',
        'data/ticket_mail_data.xml',
        'views/ticket_stage_views.xml',
        'views/ticket_category_views.xml',
        'views/ticket_department_views.xml',
        'views/ticket_monitoring_views.xml',
        'views/ticket_dashboard_views.xml',
        'views/res_users_views.xml',
        'views/ticket_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_ticket_monitoring/static/src/dashboard/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
