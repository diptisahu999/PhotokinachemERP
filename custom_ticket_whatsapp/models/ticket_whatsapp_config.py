# -*- coding: utf-8 -*-
import json
import logging
import requests
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TicketWhatsappConfig(models.Model):
    _name = 'ticket.whatsapp.config'
    _description = 'InfiQ WhatsApp Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Configuration Name', default='InfiQ WhatsApp Gateway', required=True)
    api_url = fields.Char(
        string='InfiQ API Endpoint',
        default='https://api.infiq.in/v1/messages',
        required=True,
        help="InfiQ WhatsApp REST API messages endpoint."
    )
    api_key = fields.Char(
        string='InfiQ API Key',
        help="API Key from InfiQ portal (app.infiq.in), starts with 'isk_live_' or 'isk_test_'."
    )
    is_enabled = fields.Boolean(
        string='Enable WhatsApp Notifications',
        default=True,
        help="Globally enable or disable automated WhatsApp notifications."
    )

    # 3 Required Templates
    template_registered = fields.Char(
        string='1) Registration Template Name',
        default='ticket_registered',
        required=True,
        help="Meta-approved template name in InfiQ for new ticket assignment."
    )
    template_status = fields.Char(
        string='2) State Change Template Name (WIP / On Hold)',
        default='ticket_status_update',
        required=True,
        help="Meta-approved template name in InfiQ for status updates (WIP, On Hold)."
    )
    template_completed = fields.Char(
        string='3) Completion Template Name',
        default='ticket_completed',
        required=True,
        help="Meta-approved template name in InfiQ for task resolution & closure."
    )

    # Testing field
    test_mobile = fields.Char(
        string='Test Mobile Number',
        help="10-digit mobile number or with country code (e.g. 9377730103 or 919377730103) to test sending."
    )

    def init(self):
        super().init()
        try:
            self.env.cr.execute("""
                UPDATE ticket_whatsapp_config 
                SET api_key = 'isk_live_kuE6dyNqjfFcrM4UNCfUUfF4zFDotlTod3bVwyhbvD0'
                WHERE api_key IS NULL OR api_key = '';
            """)
        except Exception:
            pass

    @api.model
    def get_config(self):
        """Return the active WhatsApp configuration."""
        config = self.search([('is_enabled', '=', True)], limit=1)
        if not config:
            config = self.search([], limit=1)
        return config

    @staticmethod
    def sanitize_mobile(number):
        """Format mobile number to E.164 without plus: 919876543210."""
        if not number:
            return False
        digits = re.sub(r'\D+', '', str(number))
        if len(digits) == 10:
            return "91" + digits
        if len(digits) == 12 and digits.startswith("91"):
            return digits
        if len(digits) > 10:
            return digits
        return False

    def action_test_connection(self):
        """Test InfiQ API connectivity with test mobile number."""
        self.ensure_one()
        if not self.api_key:
            raise UserError(_("Please enter your InfiQ API Key before testing."))
        if not self.test_mobile:
            raise UserError(_("Please enter a Test Mobile Number (e.g. 9377730103)."))

        mobile = self.sanitize_mobile(self.test_mobile)
        if not mobile:
            raise UserError(_("Invalid mobile number format."))

        headers = {
            "X-INFIQ-API-KEY": self.api_key.strip(),
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": mobile,
            "type": "template",
            "template": {
                "name": self.template_registered.strip(),
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": "TKT/TEST/001"},
                            {"type": "text", "text": "27-11-2026 15:00"},
                            {"type": "text", "text": "IT Department / Admin"},
                            {"type": "text", "text": "Ticket Monitoring / Test User"},
                            {"type": "text", "text": "InfiQ Connectivity Test"},
                            {"type": "text", "text": "P3 - Medium"},
                            {"type": "text", "text": "28-11-2026 18:00"},
                        ]
                    }
                ]
            }
        }

        try:
            response = requests.post(self.api_url.strip(), headers=headers, json=payload, timeout=15)
            res_data = response.json() if response.content else {}
            if response.status_code in (200, 201):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("WhatsApp Sent Successfully!"),
                        'message': _("InfiQ accepted the message (Status %s): %s") % (response.status_code, json.dumps(res_data)),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("InfiQ API Error (HTTP %s)") % response.status_code,
                        'message': _("Response from InfiQ: %s") % json.dumps(res_data),
                        'type': 'danger',
                        'sticky': True,
                    }
                }
        except Exception as e:
            raise UserError(_("Connection to InfiQ failed: %s") % str(e))
