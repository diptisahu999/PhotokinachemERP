# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    qc_check_ids = fields.One2many(
        'quality.check',
        'production_id',
        string='Quality Checks'
    )
    qc_check_count = fields.Integer(
        string='QC Inspections',
        compute='_compute_qc_check_count'
    )
    qc_status = fields.Selection([
        ('none', 'No QC Required'),
        ('to_check', 'QC Required on Completion'),
        ('pending', 'Under QA/QC Testing'),
        ('passed', 'All Passed (In Stock)'),
        ('failed', 'QC Failed (Rejected)'),
    ], string='Quality Status', compute='_compute_qc_status', store=True)

    @api.depends('qc_check_ids', 'qc_check_ids.state', 'product_id.qc_required')
    def _compute_qc_check_count(self):
        for order in self:
            order.qc_check_count = len(order.qc_check_ids)

    @api.depends('qc_check_ids', 'qc_check_ids.state', 'product_id.qc_required', 'state')
    def _compute_qc_status(self):
        for order in self:
            checks = order.qc_check_ids
            has_qc = bool(order.product_id and (order.product_id.qc_required or order.product_id.product_tmpl_id.qc_required))
            if not checks:
                if not has_qc:
                    order.qc_status = 'none'
                elif order.state == 'done':
                    order.qc_status = 'pending'
                else:
                    order.qc_status = 'to_check'
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
            'domain': [('production_id', '=', self.id)],
            'context': {
                'default_production_id': self.id,
                'default_product_id': self.product_id.id,
                'default_qc_type': 'mrp',
            },
        }

    def button_mark_done(self):
        # 1. Before completion: route destination location of finished products to QC staging location
        orig_dest_map = {}
        for mo in self:
            if mo.product_id and (mo.product_id.qc_required or mo.product_id.product_tmpl_id.qc_required):
                warehouse = (
                    mo.picking_type_id.warehouse_id
                    or mo.location_dest_id.warehouse_id
                    or self.env['stock.warehouse'].get_main_warehouse(mo.company_id.id)
                )
                qc_loc = warehouse._get_or_create_qc_location() if warehouse else False
                if qc_loc:
                    orig_dest_map[mo.id] = mo.location_dest_id
                    if mo.location_dest_id != qc_loc and not mo.location_dest_id.is_qc_location:
                        mo.location_dest_id = qc_loc
                        for m in mo.move_finished_ids:
                            m.location_dest_id = qc_loc
                            for ml in m.move_line_ids:
                                ml.location_dest_id = qc_loc

        res = super().button_mark_done()

        # 2. Post-done: Generate Quality Check for the finished batch in QC location
        for mo in self:
            if mo.state == 'done' and mo.product_id and (mo.product_id.qc_required or mo.product_id.product_tmpl_id.qc_required):
                existing = self.env['quality.check'].search([
                    ('production_id', '=', mo.id),
                ], limit=1)
                if not existing:
                    warehouse = (
                        mo.picking_type_id.warehouse_id
                        or mo.location_dest_id.warehouse_id
                        or self.env['stock.warehouse'].get_main_warehouse(mo.company_id.id)
                    )
                    orig_target = orig_dest_map.get(mo.id) or (warehouse.lot_stock_id if warehouse else mo.location_dest_id)

                    # Get primary produced lot
                    lot = False
                    lot_name = ''
                    if hasattr(mo, 'lot_producing_ids') and mo.lot_producing_ids:
                        lot = mo.lot_producing_ids[0]
                        lot_name = lot.name
                    elif mo.move_finished_ids.move_line_ids.lot_id:
                        lot = mo.move_finished_ids.move_line_ids.lot_id[0]
                        lot_name = lot.name

                    produced_qty = mo.qty_produced or mo.product_qty or 1.0

                    qc = self.env['quality.check'].create({
                        'qc_type': 'mrp',
                        'product_id': mo.product_id.id,
                        'lot_id': lot.id if lot else False,
                        'lot_name': lot_name,
                        'quantity': produced_qty,
                        'product_uom_id': mo.product_uom_id.id,
                        'production_id': mo.id,
                        'source_location_id': mo.location_dest_id.id,
                        'dest_warehouse_id': warehouse.id if warehouse else False,
                        'dest_location_id': orig_target.id if orig_target else False,
                        'company_id': mo.company_id.id,
                        'state': 'in_progress',
                    })
                    if not qc.check_line_ids:
                        qc._load_product_parameters()

                    mo.message_post(body=_(
                        "Quality Check <a href='#' data-oe-model='quality.check' data-oe-id='%s'>%s</a> "
                        "created for manufactured product <b>%s</b> (Lot: %s, Qty: %s). Location: %s"
                    ) % (qc.id, qc.name, mo.product_id.display_name, lot_name or 'N/A', produced_qty, mo.location_dest_id.display_name))

        return res
