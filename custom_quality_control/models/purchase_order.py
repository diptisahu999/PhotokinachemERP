# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    qc_check_ids = fields.One2many(
        'quality.check',
        'purchase_id',
        string='Quality Checks'
    )
    qc_check_count = fields.Integer(
        string='QC Inspections',
        compute='_compute_qc_check_count'
    )
    qc_status = fields.Selection([
        ('none', 'No QC Required'),
        ('to_check', 'QC Required on Receipt'),
        ('pending', 'Under QA/QC Testing'),
        ('passed', 'All Passed (In Stock)'),
        ('failed', 'QC Failed (Rejected)'),
        ('returned', 'Returned to Vendor'),
    ], string='Quality Status', compute='_compute_qc_status', store=True)

    @api.depends('qc_check_ids', 'qc_check_ids.state', 'order_line.product_id.qc_required')
    def _compute_qc_check_count(self):
        for order in self:
            order.qc_check_count = len(order.qc_check_ids)

    @api.depends('qc_check_ids', 'qc_check_ids.state', 'order_line.product_id.qc_required', 'state')
    def _compute_qc_status(self):
        for order in self:
            checks = order.qc_check_ids
            has_qc_prod = any(
                (line.product_id.qc_required or line.product_id.product_tmpl_id.qc_required)
                for line in order.order_line if line.product_id
            )
            if not checks:
                if not has_qc_prod:
                    order.qc_status = 'none'
                elif order.state == 'purchase':
                    order.qc_status = 'to_check'
                else:
                    order.qc_status = 'none'
            elif any(c.state == 'returned' for c in checks):
                order.qc_status = 'returned'
            elif any(c.state == 'failed' for c in checks):
                order.qc_status = 'failed'
            elif any(c.state in ('draft', 'in_progress', 'quarantine') for c in checks):
                order.qc_status = 'pending'
            elif all(c.state == 'passed' for c in checks):
                order.qc_status = 'passed'
            else:
                order.qc_status = 'pending'

    def action_view_qc_checks(self):
        self.ensure_one()
        return {
            'name': _('Quality Checks - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'quality.check',
            'view_mode': 'list,form',
            'domain': [('purchase_id', '=', self.id)],
            'context': {
                'default_purchase_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_qc_type': 'purchase',
            },
        }


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        vals = super()._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        is_qc = False
        if self.product_id:
            is_qc = self.product_id.qc_required or self.product_id.product_tmpl_id.qc_required
        if is_qc:
            warehouse = (
                picking.picking_type_id.warehouse_id
                or self.order_id.picking_type_id.warehouse_id
                or self.env['stock.warehouse'].get_main_warehouse(picking.company_id.id)
            )
            if warehouse:
                qc_loc = warehouse._get_or_create_qc_location()
                if qc_loc:
                    vals['location_dest_id'] = qc_loc.id
                    if 'location_final_id' in vals:
                        vals['location_final_id'] = qc_loc.id
        return vals
