# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    remarks = fields.Char(
        string='Remarks',
        help='Remarks regarding product non-availability, expected supply date, or reasons.',
    )
    is_not_available = fields.Boolean(
        string='Is Not Available',
        compute='_compute_is_not_available',
        help='Indicates if this move has stock shortage or is not available.',
    )

    @api.depends('forecast_availability', 'state', 'product_uom_qty', 'quantity')
    def _compute_is_not_available(self):
        for move in self:
            if move.state in ('done', 'cancel'):
                move.is_not_available = False
            elif move.forecast_availability is not None and move.forecast_availability < 0:
                move.is_not_available = True
            elif move.state in ('confirmed', 'waiting') and move.quantity < move.product_uom_qty:
                move.is_not_available = True
            else:
                move.is_not_available = False
