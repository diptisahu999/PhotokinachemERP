# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_currency_rate_sync = fields.Boolean(
        related='company_id.auto_currency_rate_sync',
        readonly=False,
        string='Automatic Daily Exchange Rate Sync'
    )
    last_currency_rate_sync = fields.Datetime(
        related='company_id.last_currency_rate_sync',
        string='Last Currency Sync'
    )
    currency_rate_provider = fields.Selection(
        related='company_id.currency_rate_provider',
        readonly=False,
        string='Exchange Rate Provider'
    )

    def action_sync_currency_rates_now(self):
        """Action for the 'Update Rates Now' button in Settings."""
        self.ensure_one()
        details = self.company_id.with_context(force_sync=True).action_sync_currency_rates()
        msg = _("Exchange rates updated successfully:\n\n%s") % ("\n".join(details) if details else _("All rates up to date."))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Currency Rates Synchronized"),
                'message': msg,
                'sticky': False,
                'type': 'success',
            }
        }

