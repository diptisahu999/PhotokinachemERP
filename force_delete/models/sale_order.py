# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

try:
    from odoo.addons.sale.models.sale_order import SaleOrder as OdooSaleOrder
except ImportError:
    OdooSaleOrder = models.Model


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_force_delete(self):
        """Triggered from the Actions dropdown menu to open Force Delete confirmation wizard."""
        if not self:
            raise UserError(_("Please select at least one Sales Order to force delete."))
        if not self.env.user.has_group('force_delete.group_force_delete'):
            raise UserError(_("You do not have permission to force delete records."))

        names = [f"• {so.name} ({so.partner_id.name or 'No Customer'} - State: {so.state})" for so in self]
        wizard_view = self.env.ref('force_delete.view_force_delete_wizard_form', raise_if_not_found=False)
        return {
            'name': _('Force Delete Sales Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'force.delete.wizard',
            'view_mode': 'form',
            'view_id': wizard_view.id if wizard_view else False,
            'views': [(wizard_view.id if wizard_view else False, 'form')],
            'target': 'new',
            'context': {
                'default_model_name': self._name,
                'default_record_ids': ','.join(str(i) for i in self.ids),
                'default_record_names': '\n'.join(names),
            }
        }

    def _unlink_except_draft_or_cancel(self):
        if self.env.context.get('force_delete'):
            return
        return super()._unlink_except_draft_or_cancel()

    def unlink(self):
        if self.env.context.get('force_delete'):
            return super(OdooSaleOrder, self).unlink()
        return super().unlink()

    def perform_force_delete(self, revert_stock=True, delete_chatter=True):
        """Forcibly delete sales orders and linked deliveries/invoices."""
        if not self.env.user.has_group('force_delete.group_force_delete'):
            raise UserError(_("You do not have permission to force delete records."))

        for so in self:
            _logger.info("Force deleting Sale Order %s (ID: %s, State: %s)...", so.name, so.id, so.state)

            # 1. Force delete related deliveries / pickings
            if so.picking_ids:
                so.picking_ids.perform_force_delete(revert_stock=revert_stock, delete_chatter=delete_chatter)

            # 2. Unlink order lines
            so.order_line.unlink()

            # 3. Delete chatter
            if delete_chatter:
                self.env['mail.activity'].sudo().search([('res_model', '=', 'sale.order'), ('res_id', '=', so.id)]).unlink()
                self.env['mail.message'].sudo().search([('model', '=', 'sale.order'), ('res_id', '=', so.id)]).unlink()
                self.env['mail.followers'].sudo().search([('res_model', '=', 'sale.order'), ('res_id', '=', so.id)]).unlink()
                self.env['ir.attachment'].sudo().search([('res_model', '=', 'sale.order'), ('res_id', '=', so.id)]).unlink()

            # 4. Delete SO
            so.with_context(force_delete=True).unlink()

        return True
