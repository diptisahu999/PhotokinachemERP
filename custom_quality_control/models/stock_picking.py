# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    dest_qc_location_id = fields.Many2one(
        'stock.location',
        string='Target Inventory Location',
        help='The intended inventory storage location where goods will be moved once QA/QC inspection passes.'
    )


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    qc_check_ids = fields.One2many(
        'quality.check',
        'picking_id',
        string='Quality Checks'
    )
    qc_check_count = fields.Integer(
        string='QC Inspections',
        compute='_compute_qc_check_count'
    )
    qc_status = fields.Selection([
        ('none', 'No QC Required'),
        ('to_check', 'QC Required on Validation'),
        ('pending', 'Under QA/QC Testing'),
        ('passed', 'All Passed (In Stock)'),
        ('failed', 'QC Failed (Rejected)'),
        ('returned', 'Returned to Vendor'),
    ], string='Quality Status', compute='_compute_qc_status', store=True)

    @api.depends('qc_check_ids', 'qc_check_ids.state', 'move_ids.product_id.qc_required')
    def _compute_qc_check_count(self):
        for picking in self:
            picking.qc_check_count = len(picking.qc_check_ids)

    @api.depends('qc_check_ids', 'qc_check_ids.state', 'move_ids.product_id.qc_required', 'state')
    def _compute_qc_status(self):
        for picking in self:
            checks = picking.qc_check_ids
            has_qc = any((m.product_id.qc_required or m.product_id.product_tmpl_id.qc_required) for m in picking.move_ids if m.product_id)
            if not checks:
                if not has_qc:
                    picking.qc_status = 'none'
                elif picking.state == 'done':
                    picking.qc_status = 'pending'
                else:
                    picking.qc_status = 'to_check'
            elif any(c.state == 'returned' for c in checks):
                picking.qc_status = 'returned'
            elif any(c.state == 'failed' for c in checks):
                picking.qc_status = 'failed'
            elif any(c.state in ('draft', 'in_progress', 'quarantine') for c in checks):
                picking.qc_status = 'pending'
            elif all(c.state == 'passed' for c in checks):
                picking.qc_status = 'passed'
            else:
                picking.qc_status = 'pending'

    def action_view_qc_checks(self):
        self.ensure_one()
        return {
            'name': _('Quality Checks - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'quality.check',
            'view_mode': 'list,form',
            'domain': [('picking_id', '=', self.id)],
            'context': {
                'default_picking_id': self.id,
                'default_purchase_id': self.purchase_id.id if self.purchase_id else False,
                'default_partner_id': self.partner_id.id if self.partner_id else False,
                'default_qc_type': 'purchase',
            },
        }

    def button_validate(self):
        # 1. Before validation: if this is an incoming receipt with qc-required products,
        # redirect the destination location of the moves to the warehouse QC location.
        for picking in self:
            if picking.picking_type_code == 'incoming':
                wh = (
                    picking.picking_type_id.warehouse_id
                    or picking.location_dest_id.warehouse_id
                    or self.env['stock.warehouse'].get_main_warehouse(picking.company_id.id)
                )
                qc_loc = wh._get_or_create_qc_location() if wh else False
                if qc_loc:
                    for move in picking.move_ids.filtered(lambda m: (m.product_id.qc_required or m.product_id.product_tmpl_id.qc_required)):
                        # Save original intended destination (defaults to main warehouse stock location)
                        if not move.dest_qc_location_id:
                            move.dest_qc_location_id = move.location_dest_id or (wh.lot_stock_id if wh else False)
                        # Route move to QC staging location
                        if move.location_dest_id != qc_loc and not move.location_dest_id.is_qc_location:
                            move.location_dest_id = qc_loc
                            for ml in move.move_line_ids:
                                ml.location_dest_id = qc_loc

        # 2. Call standard Odoo validation
        res = super().button_validate()

        # 3. If validation completed into 'done' and QC checks were generated,
        # pop up the notification wizard on the user's screen!
        done_qc_pickings = self.filtered(lambda p: p.state == 'done' and p.qc_check_ids)
        if done_qc_pickings and (res is True or res is None):
            first_p = done_qc_pickings[0]
            # Ensure dynamic parameters are loaded
            for qc in first_p.qc_check_ids:
                if not qc.check_line_ids:
                    qc._load_product_parameters()

            qc_loc_name = first_p.location_dest_id.display_name
            wiz = self.env['stock.picking.qc.wizard'].create({
                'picking_id': first_p.id,
                'location_name': qc_loc_name,
                'qc_check_ids': [(6, 0, first_p.qc_check_ids.ids)],
            })
            return {
                'name': _('Order Sent to QA/QC!'),
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking.qc.wizard',
                'res_id': wiz.id,
                'view_mode': 'form',
                'target': 'new',
            }

        return res

    def _action_done(self):
        res = super()._action_done()
        self._create_quality_checks()
        return res

    def _create_quality_checks(self):
        """
        Create QA/QC checks for incoming receipts with products requiring inspection.
        Locations are completely dynamic: source location is the QC location where
        goods arrived, and target warehouse/location can be edited on the check.
        """
        for picking in self:
            if picking.picking_type_code != 'incoming':
                continue

            warehouse = (
                picking.picking_type_id.warehouse_id
                or picking.location_dest_id.warehouse_id
                or self.env['stock.warehouse'].get_main_warehouse(picking.company_id.id)
            )
            default_stock_loc = warehouse.lot_stock_id if warehouse else picking.location_dest_id

            for move in picking.move_ids.filtered(lambda m: (m.product_id.qc_required or m.product_id.product_tmpl_id.qc_required) and m.state == 'done'):
                target_dest = move.dest_qc_location_id or default_stock_loc

                # Check if tracked by lot/serial
                if move.move_line_ids and move.product_id.tracking in ('lot', 'serial'):
                    for sml in move.move_line_ids.filtered(lambda l: l.quantity > 0):
                        existing = self.env['quality.check'].search([
                            ('picking_id', '=', picking.id),
                            ('product_id', '=', move.product_id.id),
                            ('lot_id', '=', sml.lot_id.id if sml.lot_id else False),
                        ], limit=1)
                        if not existing:
                            qc = self.env['quality.check'].create({
                                'qc_type': 'purchase',
                                'product_id': move.product_id.id,
                                'lot_id': sml.lot_id.id if sml.lot_id else False,
                                'lot_name': sml.lot_id.name if sml.lot_id else (sml.lot_name or ''),
                                'quantity': sml.quantity,
                                'product_uom_id': sml.product_uom_id.id or move.product_uom.id,
                                'purchase_id': picking.purchase_id.id if picking.purchase_id else False,
                                'picking_id': picking.id,
                                'partner_id': picking.partner_id.id if picking.partner_id else False,
                                'source_location_id': sml.location_dest_id.id,
                                'dest_warehouse_id': warehouse.id if warehouse else False,
                                'dest_location_id': target_dest.id if target_dest else False,
                                'company_id': picking.company_id.id,
                                'state': 'in_progress',
                            })
                            picking.message_post(body=_(
                                "Quality Check <a href='#' data-oe-model='quality.check' data-oe-id='%s'>%s</a> "
                                "created for <b>%s</b> (Lot: %s, Qty: %s). Location: %s"
                            ) % (qc.id, qc.name, move.product_id.display_name, sml.lot_id.name or 'N/A', sml.quantity, sml.location_dest_id.display_name))
                else:
                    existing = self.env['quality.check'].search([
                        ('picking_id', '=', picking.id),
                        ('product_id', '=', move.product_id.id),
                    ], limit=1)
                    if not existing:
                        qc = self.env['quality.check'].create({
                            'qc_type': 'purchase',
                            'product_id': move.product_id.id,
                            'quantity': move.quantity,
                            'product_uom_id': move.product_uom.id,
                            'purchase_id': picking.purchase_id.id if picking.purchase_id else False,
                            'picking_id': picking.id,
                            'partner_id': picking.partner_id.id if picking.partner_id else False,
                            'source_location_id': move.location_dest_id.id,
                            'dest_warehouse_id': warehouse.id if warehouse else False,
                            'dest_location_id': target_dest.id if target_dest else False,
                            'company_id': picking.company_id.id,
                            'state': 'in_progress',
                        })
                        picking.message_post(body=_(
                            "Quality Check <a href='#' data-oe-model='quality.check' data-oe-id='%s'>%s</a> "
                            "created for <b>%s</b> (Qty: %s). Location: %s"
                        ) % (qc.id, qc.name, move.product_id.display_name, move.quantity, move.location_dest_id.display_name))
