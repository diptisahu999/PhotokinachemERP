# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class QualityReleaseWizard(models.TransientModel):
    _name = 'quality.release.wizard'
    _description = 'Release Approved Product to Dynamic Inventory Location'

    @api.model
    def _default_dest_warehouse_id(self):
        check_id = self.env.context.get('default_check_id')
        if check_id:
            check = self.env['quality.check'].browse(check_id)
            if check.dest_warehouse_id:
                return check.dest_warehouse_id
        return self.env['stock.warehouse'].get_main_warehouse(self.env.company.id)

    @api.model
    def _default_dest_location_id(self):
        check_id = self.env.context.get('default_check_id')
        if check_id:
            check = self.env['quality.check'].browse(check_id)
            if check.dest_location_id:
                return check.dest_location_id
        wh = self._default_dest_warehouse_id()
        return wh.lot_stock_id if wh else False

    check_id = fields.Many2one('quality.check', string='Quality Check', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', related='check_id.product_id', readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lot / Batch', related='check_id.lot_id', readonly=True)
    quantity = fields.Float(string='Quantity', related='check_id.quantity', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit', related='check_id.product_uom_id', readonly=True)
    source_location_id = fields.Many2one(
        'stock.location',
        string='Current QC Location',
        related='check_id.source_location_id',
        readonly=True
    )
    dest_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Target Warehouse',
        default=_default_dest_warehouse_id,
        required=True,
        help='Select any warehouse where you wish to store this approved product. Defaults to the main warehouse where all products store.'
    )
    dest_location_id = fields.Many2one(
        'stock.location',
        string='Target Storage Location',
        default=_default_dest_location_id,
        domain="[('usage', 'in', ['internal', 'transit'])]",
        required=True,
        help='Select the exact shelf, rack, bin, tank, or stock location to store the product. Defaults to the main warehouse location where all products store.'
    )
    notes = fields.Text(string='Release Remarks / Notes')

    @api.onchange('dest_warehouse_id')
    def _onchange_dest_warehouse_id(self):
        if self.dest_warehouse_id:
            self.dest_location_id = self.dest_warehouse_id.lot_stock_id

    def action_confirm_release(self):
        """Confirm destination storage location and release product to inventory."""
        self.ensure_one()
        check = self.check_id
        if not self.dest_location_id:
            raise UserError(_("Please choose a Target Storage Location."))

        check.write({
            'dest_warehouse_id': self.dest_warehouse_id.id,
            'dest_location_id': self.dest_location_id.id,
        })
        if self.notes:
            existing = check.notes or ''
            check.write({'notes': f"{existing}\nRelease Note: {self.notes}".strip()})

        # Execute pass and transfer to the dynamically chosen location
        return check.action_pass()
