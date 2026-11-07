# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_order_currency_id = fields.Many2one(
        'res.currency',
        string='Order Currency',
        related='sale_id.currency_id',
        readonly=True,
    )
    order_value = fields.Monetary(
        string='Order Value',
        related='sale_id.amount_total',
        readonly=True,
        currency_field='sale_order_currency_id',
        help='Total monetary value of the source sales order.',
    )
    dispatch_remarks = fields.Text(
        string='Remarks',
        help='Remarks regarding product non-availability, expected supply date, or reasons.',
    )
    has_unavailable_products = fields.Boolean(
        string='Has Unavailable Products',
        compute='_compute_has_unavailable_products',
        help='True if picking has unavailable or delayed products.',
    )

    @api.depends('products_availability_state', 'products_availability', 'move_ids.forecast_availability', 'move_ids.is_not_available')
    def _compute_has_unavailable_products(self):
        for picking in self:
            if picking.products_availability_state == 'late':
                picking.has_unavailable_products = True
            elif picking.products_availability == 'Not Available':
                picking.has_unavailable_products = True
            elif any(m.is_not_available for m in picking.move_ids):
                picking.has_unavailable_products = True
            else:
                picking.has_unavailable_products = False
