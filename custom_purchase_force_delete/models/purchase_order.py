# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    can_force_delete = fields.Boolean(
        string='Can Force Delete',
        compute='_compute_can_force_delete'
    )

    def _check_force_delete_access(self):
        """Checks if current user has permission to force delete purchase orders."""
        current_user = self.env.user
        return (
            bool(getattr(current_user, 'purchase_force_delete', False))
            or current_user.has_group('custom_purchase_force_delete.group_allow_force_delete_purchase')
            or self.env.is_superuser()
            or current_user.has_group('base.group_system')
            or current_user.has_group('purchase.group_purchase_manager')
        )

    @api.depends_context('uid')
    def _compute_can_force_delete(self):
        can_del = self._check_force_delete_access()
        for order in self:
            order.can_force_delete = can_del

    @api.ondelete(at_uninstall=False)
    def _unlink_if_cancelled(self):
        """
        Override Odoo's built-in restriction ('you must cancel it first').
        Bypass when force_delete context is active or user has force delete permission.
        """
        if self.env.context.get('force_delete') or self._check_force_delete_access():
            return
        return super()._unlink_if_cancelled()

    def action_force_delete(self):
        """Opens the Force Delete confirmation wizard for selected Purchase Orders."""
        if not self._check_force_delete_access():
            raise UserError(_(
                "Access Denied: You do not have permission to force delete purchase orders.\n\n"
                "Please contact your administrator or enable 'Allow Force Delete Purchase Orders' in your user settings."
            ))
        return {
            'name': _('Force Delete Purchase Order(s)'),
            'type': 'ir.actions.act_window',
            'res_model': 'custom.purchase.force.delete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_ids': [(6, 0, self.ids)],
            },
        }

    def _cleanup_dependencies_for_force_delete(self):
        """
        Safely clears and decouples all linked dependencies across stock, quality checks,
        invoices, chatter, and activities so that unlinking does not hit integrity errors.
        """
        for order in self:
            po_name = order.name
            line_ids = order.order_line

            # 1. Quality Checks (from custom_quality_control if installed)
            if 'quality.check' in self.env:
                qc_records = self.env['quality.check'].sudo().search([
                    '|', ('purchase_id', '=', order.id),
                    ('purchase_line_id', 'in', line_ids.ids)
                ])
                if qc_records:
                    try:
                        if hasattr(qc_records, 'check_line_ids'):
                            qc_records.mapped('check_line_ids').sudo().unlink()
                        qc_records.sudo().unlink()
                    except Exception:
                        qc_ids = tuple(qc_records.ids)
                        if qc_ids:
                            self.env.cr.execute("DELETE FROM quality_check_line WHERE check_id IN %s;", (qc_ids,))
                            self.env.cr.execute("DELETE FROM quality_check WHERE id IN %s;", (qc_ids,))

            # 2. Stock Moves & Pickings
            if 'stock.picking' in self.env:
                pickings = order.picking_ids | self.env['stock.picking'].sudo().search([
                    ('origin', '=', po_name)
                ])
                moves = line_ids.mapped('move_ids') | pickings.mapped('move_ids') | self.env['stock.move'].sudo().search([
                    ('origin', '=', po_name)
                ])

                if moves:
                    # Unlink move lines first
                    if hasattr(moves, 'move_line_ids'):
                        moves.mapped('move_line_ids').sudo().unlink()
                    moves.sudo().write({
                        'state': 'draft',
                        'purchase_line_id': False,
                    })
                    if hasattr(moves, 'move_orig_ids'):
                        moves.sudo().write({'move_orig_ids': [(5, 0, 0)], 'move_dest_ids': [(5, 0, 0)]})
                    moves.sudo().unlink()

                if pickings:
                    pickings.sudo().write({'state': 'draft'})
                    pickings.sudo().unlink()

            # 3. Account Move Lines & Vendor Bills (Decouple references)
            if 'account.move' in self.env:
                inv_lines = self.env['account.move.line'].sudo().search([
                    ('purchase_line_id', 'in', line_ids.ids)
                ])
                if inv_lines:
                    inv_lines.sudo().write({'purchase_line_id': False})

                invoices = order.invoice_ids | self.env['account.move'].sudo().search([
                    ('invoice_origin', '=', po_name)
                ])
                if invoices:
                    invoices.sudo().write({'invoice_origin': False})

            # 4. Reject Wizards & related transient tables
            if 'purchase.approval.reject.wizard' in self.env:
                self.env['purchase.approval.reject.wizard'].sudo().search([
                    ('order_id', '=', order.id)
                ]).unlink()

            # 5. Mail Activities and Chatter Messages
            self.env['mail.activity'].sudo().search([
                ('res_model', '=', 'purchase.order'),
                ('res_id', '=', order.id)
            ]).unlink()
            self.env['mail.message'].sudo().search([
                ('model', '=', 'purchase.order'),
                ('res_id', '=', order.id)
            ]).unlink()

            # 6. Reset order state to cancel to satisfy standard constraints
            order.sudo().write({'state': 'cancel'})

    def unlink(self):
        if self.env.context.get('force_delete') or self._check_force_delete_access():
            # Cascade clean up all related records before unlinking
            self._cleanup_dependencies_for_force_delete()
            return super(PurchaseOrder, self.sudo().with_context(force_delete=True)).unlink()
        return super().unlink()
