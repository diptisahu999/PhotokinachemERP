# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

try:
    from odoo.addons.purchase.models.purchase_order import PurchaseOrder as OdooPurchaseOrder
except ImportError:
    OdooPurchaseOrder = models.Model


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_force_delete(self):
        """Triggered from the Actions dropdown menu to open Force Delete confirmation wizard."""
        if not self:
            raise UserError(_("Please select at least one Purchase Order to force delete."))
        if not self.env.user.has_group('force_delete.group_force_delete'):
            raise UserError(_("You do not have permission to force delete records."))

        names = [f"• {po.name} ({po.partner_id.name or 'No Vendor'} - State: {po.state})" for po in self]
        wizard_view = self.env.ref('force_delete.view_force_delete_wizard_form', raise_if_not_found=False)
        return {
            'name': _('Force Delete Purchase Orders'),
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

    def _unlink_if_cancelled(self):
        if self.env.context.get('force_delete'):
            return
        return super()._unlink_if_cancelled()

    def unlink(self):
        if self.env.context.get('force_delete'):
            return super(OdooPurchaseOrder, self).unlink()
        return super().unlink()

    def perform_force_delete(self, revert_stock=True, delete_chatter=True):
        """Forcibly delete purchase orders and linked receipts/invoices."""
        if not self.env.user.has_group('force_delete.group_force_delete'):
            raise UserError(_("You do not have permission to force delete records."))

        for po in self:
            _logger.info("Force deleting Purchase Order %s (ID: %s, State: %s)...", po.name, po.id, po.state)

            # 1. Unlink quality checks
            if 'quality.check' in self.env:
                qc_records = self.env['quality.check'].sudo().search([('purchase_id', '=', po.id)])
                if qc_records:
                    qc_records.unlink()

            # 2. Force delete related receipts / pickings
            if po.picking_ids:
                po.picking_ids.perform_force_delete(revert_stock=revert_stock, delete_chatter=delete_chatter)

            # 3. Unlink order lines
            po.order_line.unlink()

            # 4. Delete chatter
            if delete_chatter:
                self.env['mail.activity'].sudo().search([('res_model', '=', 'purchase.order'), ('res_id', '=', po.id)]).unlink()
                self.env['mail.message'].sudo().search([('model', '=', 'purchase.order'), ('res_id', '=', po.id)]).unlink()
                self.env['mail.followers'].sudo().search([('res_model', '=', 'purchase.order'), ('res_id', '=', po.id)]).unlink()
                self.env['ir.attachment'].sudo().search([('res_model', '=', 'purchase.order'), ('res_id', '=', po.id)]).unlink()

            # 5. Delete PO
            po.with_context(force_delete=True).unlink()

        return True
