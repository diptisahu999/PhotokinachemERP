# -*- coding: utf-8 -*-
{
    'name': 'Custom User Credentials Mailer',
    'version': '19.0.1.0.0',
    'category': 'Administration',
    'summary': 'Send Project URL, Email, and Password directly to users via email with a single click',
    'description': """
Custom User Credentials Mailer
==============================
This module provides a convenient and secure feature to email login credentials
(Project URL, Login/Email, and Password) to users directly from their User profile.

Key Features:
-------------
1. **"Send Mail" Button on User Form**:
   - Prominently placed in the form header of User settings (`res.users`).
   - Opens an intuitive dialog wizard showing the Project URL, Login/Email, and Password.

2. **Automated Credential Generation**:
   - Auto-detects the Project / System URL from `web.base.url`.
   - Auto-fetches the user's Login and Email.
   - Automatically generates a strong, secure temporary password (with option to regenerate or manually customize).

3. **Instant Password Update & Login**:
   - Automatically updates the user's login password in Odoo when sent, so the user can immediately log in with the emailed credentials.

4. **One-Click Quick Send**:
   - "Quick Send Mail" button in the header and Action menu to immediately generate a password, set it, and send credentials in one click.

5. **Branded HTML Email Template**:
   - Clean, responsive email layout customized for Photokina Chemicals Pvt. Ltd.
   - Includes direct "Log In to ERP Portal" action button, credentials table, and login guidance.

6. **Full Audit Logging**:
   - Records the timestamp of when credentials were last emailed on the user form.
   - Logs an audit entry in the chatter.
    """,
    'author': 'Photokina Chemicals Pvt. Ltd.',
    'website': 'https://www.photokinachem.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'wizard/send_credentials_wizard_views.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
