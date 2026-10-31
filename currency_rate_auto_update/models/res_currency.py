# -*- coding: utf-8 -*-
from odoo import models, fields, _

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def action_sync_live_rates_button(self):
        """Action for the 'Update Live Rates' button on Currencies view."""
        company = self.env.company
        details = company.with_context(force_sync=True).action_sync_currency_rates()
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

