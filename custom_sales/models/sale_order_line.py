# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_qty_on_hand = fields.Float(
        string='On Hand',
        compute='_compute_product_availability',
        digits='Product Unit of Measure',
        help='Current quantity physically available in stock (on-hand).',
    )
    product_qty_forecasted = fields.Float(
        string='Forecasted',
        compute='_compute_product_availability',
        digits='Product Unit of Measure',
        help='Forecasted quantity taking into account all confirmed moves (incoming - outgoing).',
    )

    @api.depends('product_id')
    def _compute_product_availability(self):
        for line in self:
            if line.product_id:
                line.product_qty_on_hand = line.product_id.qty_available
                line.product_qty_forecasted = line.product_id.virtual_available
            else:
                line.product_qty_on_hand = 0.0
                line.product_qty_forecasted = 0.0

