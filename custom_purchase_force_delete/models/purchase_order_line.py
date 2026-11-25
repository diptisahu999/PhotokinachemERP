# -*- coding: utf-8 -*-
from odoo import models, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_purchase(self):
        """
        Override Odoo's restriction ('Cannot delete a purchase order line which is in state Purchase Order').
        Bypass when force_delete context is active or user has force delete permission.
        """
        if self.env.context.get('force_delete') or any(l.order_id._check_force_delete_access() for l in self):
            return
        return super()._unlink_except_purchase()

    def unlink(self):
        if self.env.context.get('force_delete') or any(l.order_id._check_force_delete_access() for l in self):
            # Decouple any linked stock move or invoice line references
            for line in self:
                if 'stock.move' in self.env:
                    self.env['stock.move'].sudo().search([('purchase_line_id', '=', line.id)]).write({'purchase_line_id': False})
                if 'account.move.line' in self.env:
                    self.env['account.move.line'].sudo().search([('purchase_line_id', '=', line.id)]).write({'purchase_line_id': False})
                if 'quality.check' in self.env:
                    self.env['quality.check'].sudo().search([('purchase_line_id', '=', line.id)]).write({'purchase_line_id': False})
            return super(PurchaseOrderLine, self.sudo().with_context(force_delete=True)).unlink()
        return super().unlink()

