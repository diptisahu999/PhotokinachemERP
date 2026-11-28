# -*- coding: utf-8 -*-
{
    'name': 'PCPL Ticket WhatsApp Notifications (InfiQ)',
    'version': '19.0.1.0.3',
    'category': 'Operations/Helpdesk',
    'summary': 'Automated 3-tier WhatsApp notifications via InfiQ API: Task Registration, WIP/Hold State Updates, and Completion',
    'description': """
PCPL Ticket WhatsApp Notifications (InfiQ)
===========================================
Integrates the PCPL Ticket Monitoring System with the InfiQ WhatsApp Business API (https://app.infiq.in/):

Key Capabilities:
-----------------

2. **2) State Changes Notification**:
   - Triggered on transition to **WIP (Work in Progress)** or **ON HOLD**.
   - Includes Task ID, Subject, New Status, Reason / Remarks, and Updating User.

3. **3) Completion of Task Notification**:
   - Triggered on **Resolved** and **Closed**.
   - Includes Task ID, Subject, From Date to To Date timeframe, and CAPA / Action Taken remarks.

4. **InfiQ API Gateway Integration**:
   - Configurable API Endpoint & X-INFIQ-API-KEY.
   - Mobile number auto-sanitization to E.164 (India 91-prefix).
   - Built-in Test Connection & Sample dispatch tool.
   - Real-time Chatter logging of WhatsApp delivery milestones.
    """,
    'author': 'Photokina Chemicals Pvt. Ltd.',
    'website': 'https://www.photokinachem.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'custom_ticket_monitoring',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/default_whatsapp_config_data.xml',
        'views/ticket_whatsapp_config_views.xml',
        'views/ticket_monitoring_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
