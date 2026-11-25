# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseForceDeleteWizard(models.TransientModel):
    _name = 'custom.purchase.force.delete.wizard'
    _description = 'Force Delete Purchase Order Wizard'

    order_ids = fields.Many2many('purchase.order', string='Orders to Delete')
    order_names = fields.Char(string='Order References', compute='_compute_order_details')
    count = fields.Integer(string='Selected Orders', compute='_compute_order_details')

    picking_count = fields.Integer(string='Linked Receipts', compute='_compute_order_details')
    invoice_count = fields.Integer(string='Linked Vendor Bills', compute='_compute_order_details')
    qc_count = fields.Integer(string='Linked Quality Checks', compute='_compute_order_details')

    delete_pickings = fields.Boolean(
        string='Delete Linked Stock Receipts & Moves',
        default=True,
        help='If checked, all incoming receipts and stock moves linked to these purchase orders will also be deleted.'
    )
    delete_invoices = fields.Boolean(
        string='Cancel & Delete Draft/Cancelled Vendor Bills',
        default=False,
        help='If checked, draft or cancelled vendor bills associated with these purchase orders will be unlinked or deleted.'
    )
    delete_quality_checks = fields.Boolean(
        string='Delete Linked Quality Inspections',
        default=True,
        help='If checked, quality inspection records associated with these purchase orders will also be deleted.'
    )

    @api.depends('order_ids')
    def _compute_order_details(self):
        for rec in self:
            orders = rec.order_ids
            if orders:
                rec.count = len(orders)
                names = orders.mapped('name')
                rec.order_names = ", ".join(names[:10]) + ("..." if len(names) > 10 else "")

                # Pickings
                po_names = orders.mapped('name')
                pickings = orders.mapped('picking_ids')
                if 'stock.picking' in self.env:
                    pickings |= self.env['stock.picking'].sudo().search([('origin', 'in', po_names)])
                rec.picking_count = len(pickings)

                # Vendor bills
                rec.invoice_count = len(orders.mapped('invoice_ids'))

                # Quality checks
                if 'quality.check' in self.env:
                    lines = orders.mapped('order_line')
                    qc_records = self.env['quality.check'].sudo().search([
                        '|', ('purchase_id', 'in', orders.ids),
                        ('purchase_line_id', 'in', lines.ids)
                    ])
                    rec.qc_count = len(qc_records)
                else:
                    rec.qc_count = 0
            else:
                rec.count = 0
                rec.order_names = ""
                rec.picking_count = 0
                rec.invoice_count = 0
                rec.qc_count = 0

    def action_confirm_force_delete(self):
        self.ensure_one()
        if not self.order_ids:
            return

        # Check permissions
        if not self.env['purchase.order']._check_force_delete_access():
            raise UserError(_(
                "Access Denied: You do not have permission to force delete purchase orders."
            ))

        order_ids = self.order_ids.sudo()
        line_ids = order_ids.mapped('order_line')
        po_names = order_ids.mapped('name')
        deleted_count = len(order_ids)

        # 1. Quality Checks cleanup
        if 'quality.check' in self.env:
            qc_records = self.env['quality.check'].sudo().search([
                '|', ('purchase_id', 'in', order_ids.ids),
                ('purchase_line_id', 'in', line_ids.ids)
            ])
            if qc_records:
                if self.delete_quality_checks:
                    try:
                        if hasattr(qc_records, 'check_line_ids'):
                            qc_records.mapped('check_line_ids').sudo().unlink()
                        qc_records.sudo().unlink()
                    except Exception:
                        qc_ids = tuple(qc_records.ids)
                        if qc_ids:
                            self.env.cr.execute("DELETE FROM quality_check_line WHERE check_id IN %s;", (qc_ids,))
                            self.env.cr.execute("DELETE FROM quality_check WHERE id IN %s;", (qc_ids,))
                else:
                    try:
                        qc_records.sudo().write({'purchase_id': False, 'purchase_line_id': False})
                    except Exception:
                        qc_ids = tuple(qc_records.ids)
                        if qc_ids:
                            self.env.cr.execute("UPDATE quality_check SET purchase_id = NULL, purchase_line_id = NULL WHERE id IN %s;", (qc_ids,))

        # 2. Stock Pickings & Moves cleanup
        if 'stock.picking' in self.env:
            pickings = order_ids.mapped('picking_ids') | self.env['stock.picking'].sudo().search([
                ('origin', 'in', po_names)
            ])
            moves = line_ids.mapped('move_ids') | pickings.mapped('move_ids') | self.env['stock.move'].sudo().search([
                ('origin', 'in', po_names)
            ])

            if moves:
                try:
                    if hasattr(moves, 'move_line_ids'):
                        moves.mapped('move_line_ids').sudo().unlink()
                    moves.sudo().write({
                        'state': 'draft',
                        'purchase_line_id': False,
                    })
                    if hasattr(moves, 'move_orig_ids'):
                        moves.sudo().write({'move_orig_ids': [(5, 0, 0)], 'move_dest_ids': [(5, 0, 0)]})
                    if self.delete_pickings:
                        moves.sudo().unlink()
                except Exception:
                    move_ids = tuple(moves.ids)
                    if move_ids:
                        self.env.cr.execute("DELETE FROM stock_move_line WHERE move_id IN %s;", (move_ids,))
                        self.env.cr.execute("DELETE FROM stock_move WHERE id IN %s;", (move_ids,))

            if pickings and self.delete_pickings:
                try:
                    pickings.sudo().write({'state': 'draft'})
                    pickings.sudo().unlink()
                except Exception:
                    pk_ids = tuple(pickings.ids)
                    if pk_ids:
                        self.env.cr.execute("DELETE FROM stock_picking WHERE id IN %s;", (pk_ids,))

        # 3. Vendor Bills cleanup
        if 'account.move' in self.env:
            inv_lines = self.env['account.move.line'].sudo().search([
                ('purchase_line_id', 'in', line_ids.ids)
            ])
            if inv_lines:
                try:
                    inv_lines.sudo().write({'purchase_line_id': False})
                except Exception:
                    self.env.cr.execute("UPDATE account_move_line SET purchase_line_id = NULL WHERE purchase_line_id IN %s;", (tuple(line_ids.ids),))

            invoices = order_ids.mapped('invoice_ids') | self.env['account.move'].sudo().search([
                ('invoice_origin', 'in', po_names)
            ])
            if invoices:
                if self.delete_invoices:
                    draft_canc_invoices = invoices.filtered(lambda m: m.state in ('draft', 'cancel'))
                    try:
                        draft_canc_invoices.sudo().unlink()
                    except Exception:
                        pass
                else:
                    try:
                        invoices.sudo().write({'invoice_origin': False})
                    except Exception:
                        pass

        # 4. Reject Wizards & transient references
        if 'purchase.approval.reject.wizard' in self.env:
            try:
                self.env['purchase.approval.reject.wizard'].sudo().search([
                    ('order_id', 'in', order_ids.ids)
                ]).unlink()
            except Exception:
                self.env.cr.execute("DELETE FROM purchase_approval_reject_wizard WHERE order_id IN %s;", (tuple(order_ids.ids),))

        # 5. Chatter Activities and Messages
        self.env['mail.activity'].sudo().search([
            ('res_model', '=', 'purchase.order'),
            ('res_id', 'in', order_ids.ids)
        ]).unlink()
        self.env['mail.message'].sudo().search([
            ('model', '=', 'purchase.order'),
            ('res_id', 'in', order_ids.ids)
        ]).unlink()

        # 6. Reset PO state to cancel and unlink with force_delete context
        try:
            order_ids.sudo().write({'state': 'cancel'})
            order_ids.sudo().with_context(force_delete=True).unlink()
        except Exception:
            po_id_tuple = tuple(order_ids.ids)
            po_line_tuple = tuple(line_ids.ids)
            if po_line_tuple:
                self.env.cr.execute("DELETE FROM purchase_order_line WHERE id IN %s;", (po_line_tuple,))
            if po_id_tuple:
                self.env.cr.execute("DELETE FROM purchase_order WHERE id IN %s;", (po_id_tuple,))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Deleted Successfully!'),
                'message': _('%d Purchase Order(s) forcefully deleted.') % deleted_count,
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.order',
                    'view_mode': 'list,form',
                    'views': [(False, 'list'), (False, 'form')],
                }
            }
        }
