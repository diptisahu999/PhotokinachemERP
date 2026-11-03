# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    lot_currency_id = fields.Many2one(
        'res.currency',
        string='Lot Currency',
        related='lot_id.currency_id',
        readonly=True,
    )

    lot_cost = fields.Monetary(
        string='Purchase Price',
        related='lot_id.purchase_price',
        currency_field='lot_currency_id',
        readonly=True,
    )

    @api.model
    def _get_removal_strategy(self, product_id, location_id):
        # Prioritize FEFO (First Expiry First Out) for all products using expiration dates
        if product_id.sudo().use_expiration_date:
            return 'fefo'
        return super()._get_removal_strategy(product_id, location_id)

    @api.model
    def _get_removal_strategy_order(self, removal_strategy):
        if removal_strategy == 'fefo':
            # Earliest expiry first (NULLS LAST), then FIFO (in_date ASC)
            return 'removal_date ASC NULLS LAST, in_date ASC, id ASC'
        return super()._get_removal_strategy_order(removal_strategy)
