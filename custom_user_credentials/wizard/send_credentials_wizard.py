# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..models.res_users import generate_secure_password

_logger = logging.getLogger(__name__)


class SendUserCredentialsWizard(models.TransientModel):
    _name = 'send.user.credentials.wizard'
    _description = 'Wizard to Send Login Credentials to User'

    user_id = fields.Many2one(
        'res.users',
        string="User",
        required=True,
        ondelete='cascade',
        help="Target user who will receive the login details."
    )
    recipient_name = fields.Char(
        string="User Name",
        related='user_id.name',
        readonly=True
    )
    email = fields.Char(
        string="Login / Email",
        required=True,
        help="Email address where credentials will be delivered, also used as login."
    )
    project_url = fields.Char(
        string="Project / ERP URL",
        required=True,
        help="System URL for the ERP portal (e.g. http://localhost:9904 or your live domain)."
    )
    password = fields.Char(
        string="Password",
        required=True,
        help="Password to be sent to the user. You can modify this or click Regenerate."
    )
    update_user_password = fields.Boolean(
        string="Update User Password in System",
        default=True,
        help="When checked, automatically sets this password as the user's active password in Odoo so they can log in immediately."
    )
    send_copy_to_admin = fields.Boolean(
        string="Send Copy to My Email (CC)",
        default=False,
        help="Receive a copy of the credentials email at your own administrator email address."
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id') or res.get('user_id')
        if active_id:
            user = self.env['res.users'].browse(active_id)
            if user.exists():
                res['user_id'] = user.id
                res['email'] = (user.email or user.login or '').strip()
        
        # Determine Project / ERP URL
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').strip()
        if not base_url:
            base_url = 'http://localhost:9904'
        res['project_url'] = base_url

        # Generate a strong, secure temporary password
        res['password'] = generate_secure_password(10)
        return res

    def action_regenerate_password(self):
        """Generate a new random password and update the wizard."""
        self.ensure_one()
        new_pwd = generate_secure_password(10)
        self.password = new_pwd
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_send_mail(self):
        """Send the credentials email containing Project URL, Email, and Password."""
        self.ensure_one()
        user = self.user_id
        if not user.exists():
            raise UserError(_("User record no longer exists."))

        recipient_email = (self.email or '').strip()
        if not recipient_email:
            raise UserError(_("Please provide a valid recipient email address."))

        project_url = (self.project_url or '').strip()
        if not project_url:
            raise UserError(_("Please provide a valid Project / ERP URL."))

        password = (self.password or '').strip()
        if not password:
            raise UserError(_("Please provide a password to send."))

        # 1. Update user password in system if requested
        if self.update_user_password:
            user._change_password(password)

        # 2. Get mail template
        template = self.env.ref('custom_user_credentials.email_template_user_credentials', raise_if_not_found=False)
        if not template:
            raise UserError(_("Email template 'custom_user_credentials.email_template_user_credentials' not found."))

        company_name = user.company_id.name or self.env.company.name or 'Photokina Chemicals Pvt. Ltd.'

        ctx = {
            'project_url': project_url,
            'login_email': recipient_email,
            'user_password': password,
            'user_name': user.name,
            'company_name': company_name,
        }

        email_values = {
            'email_to': recipient_email,
            'auto_delete': False,
        }

        if self.send_copy_to_admin and self.env.user.email:
            email_values['email_cc'] = self.env.user.email.strip()

        # 3. Send email (attempt instant dispatch, fallback to outbox queue)
        try:
            template.sudo().with_context(**ctx).send_mail(
                user.id,
                force_send=True,
                raise_exception=True,
                email_values=email_values
            )
        except Exception as e:
            _logger.warning("Direct SMTP send failed, queuing in Outbox: %s", e)
            template.sudo().with_context(**ctx).send_mail(
                user.id,
                force_send=False,
                raise_exception=False,
                email_values=email_values
            )

        # 4. Update audit timestamp on user
        user.write({
            'last_credentials_sent_date': fields.Datetime.now(),
            'last_credentials_sent_by': self.env.user.id,
        })

        # 5. Log in partner chatter
        if hasattr(user.partner_id, 'message_post'):
            user.partner_id.message_post(
                body=_(
                    "<b>Login Credentials Sent</b><br/>"
                    "Recipient: %s<br/>"
                    "Project URL: %s<br/>"
                    "Sent by: %s"
                ) % (recipient_email, project_url, self.env.user.name),
                subtype_xmlid='mail.mt_note'
            )

        # 6. Show friendly success popup notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Credentials Sent Successfully'),
                'message': _('Login details (Project URL, Email, Password) have been emailed to %s.') % recipient_email,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
