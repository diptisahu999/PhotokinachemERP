# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

try:
    from odoo.addons.stock.models.stock_picking import Picking as OdooStockPicking
except ImportError:
    OdooStockPicking = models.Model


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_force_delete(self):
        """Triggered from the Actions dropdown menu to open Force Delete confirmation wizard."""
        if not self:
            raise UserError(_("Please select at least one Transfer / Picking to force delete."))
        if not self.env.user.has_group('force_delete.group_force_delete'):
            raise UserError(_("You do not have permission to force delete records."))

        names = [f"• {p.name} ({p.partner_id.name or 'No Partner'} - State: {p.state})" for p in self]
        wizard_view = self.env.ref('force_delete.view_force_delete_wizard_form', raise_if_not_found=False)
        return {
            'name': _('Force Delete Transfers'),
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

    def unlink(self):
        if self.env.context.get('force_delete'):
            # In force delete mode, delete move lines and moves with force_delete context
            if self.move_ids:
                self.move_ids.mapped('move_line_ids').with_context(force_delete=True).unlink()
                self.move_ids.with_context(force_delete=True).unlink()
            return super(OdooStockPicking, self).unlink()
        return super().unlink()

    def perform_force_delete(self, revert_stock=True, delete_chatter=True):
        """Forcibly delete pickings/transfers and clean up associated stock moves."""
        if not self.env.user.has_group('force_delete.group_force_delete'):
            raise UserError(_("You do not have permission to force delete records."))

        Quant = self.env['stock.quant']

        for picking in self:
            _logger.info("Force deleting Picking %s (ID: %s, State: %s)...", picking.name, picking.id, picking.state)

            # 1. Optionally revert stock if the transfer is done
            if revert_stock and picking.state == 'done':
                for line in picking.move_line_ids.filtered(lambda l: l.quantity > 0):
                    try:
                        qty = line.quantity_product_uom or line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id)
                        # Revert: decrement from destination, increment back to source
                        if line.location_dest_id.usage in ('internal', 'transit'):
                            Quant._update_available_quantity(
                                line.product_id,
                                line.location_dest_id,
                                -qty,
                                lot_id=line.lot_id or None,
                                package_id=line.result_package_id or None,
                                owner_id=line.owner_id or None,
                            )
                        if line.location_id.usage in ('internal', 'transit'):
                            Quant._update_available_quantity(
                                line.product_id,
                                line.location_id,
                                qty,
                                lot_id=line.lot_id or None,
                                package_id=line.package_id or None,
                                owner_id=line.owner_id or None,
                            )
                    except Exception as e:
                        _logger.warning("Could not revert quant for picking line %s: %s", line.id, e)

            # 2. Cleanly delete quality inspections linked to this picking
            if 'quality.check' in self.env:
                qc_records = self.env['quality.check'].sudo().search([('picking_id', '=', picking.id)])
                if qc_records:
                    qc_records.unlink()

            # 3. Delete stock moves and move lines
            if picking.move_ids:
                picking.move_ids.mapped('move_line_ids').with_context(force_delete=True).unlink()
                picking.move_ids.with_context(force_delete=True).unlink()

            # 4. Delete chatter
            if delete_chatter:
                self.env['mail.activity'].sudo().search([('res_model', '=', 'stock.picking'), ('res_id', '=', picking.id)]).unlink()
                self.env['mail.message'].sudo().search([('model', '=', 'stock.picking'), ('res_id', '=', picking.id)]).unlink()
                self.env['mail.followers'].sudo().search([('res_model', '=', 'stock.picking'), ('res_id', '=', picking.id)]).unlink()
                self.env['ir.attachment'].sudo().search([('res_model', '=', 'stock.picking'), ('res_id', '=', picking.id)]).unlink()

            # 5. Delete picking itself
            picking.with_context(force_delete=True).unlink()

        return True
