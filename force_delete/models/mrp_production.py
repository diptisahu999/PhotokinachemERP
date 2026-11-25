# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

try:
    from odoo.addons.mrp.models.mrp_production import MrpProduction as OdooMrpProduction
except ImportError:
    OdooMrpProduction = models.Model


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def action_force_delete(self):
        """Triggered from the Actions dropdown menu to open Force Delete confirmation wizard."""
        if not self:
            raise UserError(_("Please select at least one Manufacturing Order to force delete."))
        if not self.env.user.has_group('force_delete.group_force_delete'):
            raise UserError(_("You do not have permission to force delete records. Please contact an Administrator."))

        names = [f"• {order.name} ({order.product_id.display_name or 'No Product'} - State: {order.state})" for order in self]
        wizard_view = self.env.ref('force_delete.view_force_delete_wizard_form', raise_if_not_found=False)
        return {
            'name': _('Force Delete Manufacturing Orders'),
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

    def _unlink_if_not_done(self):
        if self.env.context.get('force_delete'):
            return
        return super()._unlink_if_not_done()

    def _unlink_except_done(self):
        if self.env.context.get('force_delete'):
            return
        return super()._unlink_except_done()

    def action_cancel(self):
        if self.env.context.get('force_delete'):
            return True
        return super().action_cancel()

    def unlink(self):
        if self.env.context.get('force_delete'):
            for mo in self:
                if mo.workorder_ids:
                    if hasattr(mo.workorder_ids, 'time_ids') and mo.workorder_ids.time_ids:
                        if hasattr(mo.workorder_ids.time_ids, 'account_move_line_id'):
                            mo.workorder_ids.time_ids.write({'account_move_line_id': False})
                        mo.workorder_ids.time_ids.unlink()
                    mo.workorder_ids.unlink()
            return super(OdooMrpProduction, self).unlink()
        return super().unlink()

    def perform_force_delete(self, revert_stock=True, delete_chatter=True):
        """Forcibly delete manufacturing orders and cleanly purge all related dependencies."""
        if not self.env.user.has_group('force_delete.group_force_delete'):
            raise UserError(_("You do not have permission to force delete records."))

        Quant = self.env['stock.quant']

        for mo in self:
            _logger.info("Force deleting Manufacturing Order %s (ID: %s, State: %s)...", mo.name, mo.id, mo.state)

            # 1. Optionally revert physical stock movements for Done orders
            if revert_stock and mo.state == 'done':
                # Revert finished product output (deduct from destination stock location)
                for move in mo.move_finished_ids.filtered(lambda m: m.state == 'done'):
                    for line in move.move_line_ids.filtered(lambda l: l.quantity > 0):
                        try:
                            qty = line.quantity_product_uom or line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id)
                            if line.location_dest_id.usage in ('internal', 'transit'):
                                Quant._update_available_quantity(
                                    line.product_id,
                                    line.location_dest_id,
                                    -qty,
                                    lot_id=line.lot_id or None,
                                    package_id=line.result_package_id or None,
                                    owner_id=line.owner_id or None,
                                )
                        except Exception as e:
                            _logger.warning("Could not revert finished product quant for line %s: %s", line.id, e)

                # Revert component consumption (restore back to raw material source location)
                for move in mo.move_raw_ids.filtered(lambda m: m.state == 'done'):
                    for line in move.move_line_ids.filtered(lambda l: l.quantity > 0):
                        try:
                            qty = line.quantity_product_uom or line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id)
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
                            _logger.warning("Could not revert component quant for line %s: %s", line.id, e)

            # 2. Cleanly delete quality inspections (custom_quality_control or core)
            if 'quality.check' in self.env:
                qc_records = self.env['quality.check'].sudo().search([('production_id', '=', mo.id)])
                if qc_records:
                    qc_scraps = qc_records.mapped('scrap_id')
                    if qc_scraps:
                        qc_scraps.sudo().unlink()
                    qc_records.sudo().unlink()

            # 3. Cleanly delete scraps linked to this MO
            if 'stock.scrap' in self.env:
                scraps = self.env['stock.scrap'].sudo().search([('production_id', '=', mo.id)])
                if scraps:
                    scraps.sudo().unlink()

            # 4. Cleanly delete work orders and productivity time entries
            if mo.workorder_ids:
                if hasattr(mo.workorder_ids, 'time_ids') and mo.workorder_ids.time_ids:
                    if hasattr(mo.workorder_ids.time_ids, 'account_move_line_id'):
                        mo.workorder_ids.time_ids.write({'account_move_line_id': False})
                    mo.workorder_ids.time_ids.unlink()
                mo.workorder_ids.unlink()

            # 5. Clear WIP account moves link if mrp_account is used
            if hasattr(mo, 'wip_move_ids') and mo.wip_move_ids:
                mo.wip_move_ids = [(5, 0, 0)]

            # 6. Delete stock moves and stock move lines
            all_moves = mo.move_raw_ids | mo.move_finished_ids
            if hasattr(mo, 'move_byproduct_ids'):
                all_moves |= mo.move_byproduct_ids
            if all_moves:
                all_moves.mapped('move_line_ids').with_context(force_delete=True).unlink()
                all_moves.with_context(force_delete=True).unlink()

            # 7. Delete chatter messages, followers, activities & attachments
            if delete_chatter:
                self.env['mail.activity'].sudo().search([('res_model', '=', 'mrp.production'), ('res_id', '=', mo.id)]).unlink()
                self.env['mail.message'].sudo().search([('model', '=', 'mrp.production'), ('res_id', '=', mo.id)]).unlink()
                self.env['mail.followers'].sudo().search([('res_model', '=', 'mrp.production'), ('res_id', '=', mo.id)]).unlink()
                self.env['ir.attachment'].sudo().search([('res_model', '=', 'mrp.production'), ('res_id', '=', mo.id)]).unlink()

            # 8. Finally delete the MO record itself
            mo.with_context(force_delete=True).unlink()

        return True
