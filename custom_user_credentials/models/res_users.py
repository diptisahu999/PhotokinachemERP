# -*- coding: utf-8 -*-
import logging
import secrets
import string
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def generate_secure_password(length=10):
    """Generate a readable yet secure temporary password."""
    # Ensure a mix of uppercase, lowercase, numbers, and allowed punctuation
    upper = string.ascii_uppercase
    lower = string.ascii_lowercase
    digits = string.digits
    special = "@#$%"
    all_chars = upper + lower + digits + special

    password = [
        secrets.choice(upper),
        secrets.choice(lower),
        secrets.choice(digits),
        secrets.choice(special),
    ]
    password += [secrets.choice(all_chars) for _ in range(max(4, length) - 4)]
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)


class ResUsers(models.Model):
    _inherit = 'res.users'

    last_credentials_sent_date = fields.Datetime(
        string="Credentials Last Sent",
        readonly=True,
        copy=False,
        help="Date and time when login credentials were last sent via email to this user."
    )
    last_credentials_sent_by = fields.Many2one(
        'res.users',
        string="Credentials Sent By",
        readonly=True,
        copy=False,
        help="Administrator who last emailed login credentials to this user."
    )

    def action_open_send_credentials_wizard(self):
        """Open the Send Login Credentials dialog for this user."""
        self.ensure_one()
        return {
            'name': _('Send Login Credentials'),
            'type': 'ir.actions.act_window',
            'res_model': 'send.user.credentials.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_user_id': self.id,
            }
        }

    def action_send_credentials_direct(self):
        """Quick send credentials in 1 click without wizard."""
        self.ensure_one()
        user = self
        recipient_email = (user.email or user.login or '').strip()
        if not recipient_email:
            raise UserError(_("User '%s' does not have an email address or login configured.") % user.name)

        # 1. Project URL
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').strip()
        if not base_url:
            base_url = 'http://localhost:9904'

        # 2. Generate temporary password & set in Odoo
        temp_password = generate_secure_password(10)
        user._change_password(temp_password)

        # 3. Send email template
        template = self.env.ref('custom_user_credentials.email_template_user_credentials', raise_if_not_found=False)
        if not template:
            raise UserError(_("Email template 'custom_user_credentials.email_template_user_credentials' not found."))

        company_name = user.company_id.name or self.env.company.name or 'Photokina Chemicals Pvt. Ltd.'

        ctx = {
            'project_url': base_url,
            'login_email': recipient_email,
            'user_password': temp_password,
            'user_name': user.name,
            'company_name': company_name,
        }

        email_values = {
            'email_to': recipient_email,
            'auto_delete': False,
        }

        try:
            template.sudo().with_context(**ctx).send_mail(
                user.id,
                force_send=True,
                raise_exception=True,
                email_values=email_values
            )
        except Exception as e:
            _logger.warning("Direct SMTP send failed, queuing email in Outbox: %s", e)
            template.sudo().with_context(**ctx).send_mail(
                user.id,
                force_send=False,
                raise_exception=False,
                email_values=email_values
            )

        # 4. Update audit fields
        user.write({
            'last_credentials_sent_date': fields.Datetime.now(),
            'last_credentials_sent_by': self.env.user.id,
        })

        # 5. Post audit log in partner chatter if available
        if hasattr(user.partner_id, 'message_post'):
            user.partner_id.message_post(
                body=_(
                    "<b>Login Credentials Sent</b><br/>"
                    "Recipient: %s<br/>"
                    "Project URL: %s<br/>"
                    "Sent by: %s"
                ) % (recipient_email, base_url, self.env.user.name),
                subtype_xmlid='mail.mt_note'
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Credentials Sent Successfully'),
                'message': _('Login details (Project URL, Email, Password) have been emailed to %s.') % recipient_email,
                'type': 'success',
                'sticky': False,
            }
        }
