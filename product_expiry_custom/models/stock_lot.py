# -*- coding: utf-8 -*-
import datetime
from odoo import models, fields, api

class StockLot(models.Model):
    _inherit = 'stock.lot'

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_purchase_details',
        store=True,
        readonly=False,
        help="Currency of the purchase price.",
    )
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        compute='_compute_purchase_details',
        store=True,
        readonly=False,
        help="Purchase Order from which this lot was received.",
    )
    purchase_line_id = fields.Many2one(
        'purchase.order.line',
        string='Purchase Order Line',
        compute='_compute_purchase_details',
        store=True,
        readonly=False,
    )
    purchase_price = fields.Monetary(
        string='Purchase Price',
        currency_field='currency_id',
        compute='_compute_purchase_details',
        store=True,
        readonly=False,
        help="Purchase orderline unit price of this lot.",
    )
    is_expired = fields.Boolean(
        string='Is Expired',
        compute='_compute_expiry_status',
        store=True,
    )
    is_expiring_soon = fields.Boolean(
        string='Is Expiring Soon',
        compute='_compute_expiry_status',
        store=True,
    )

    @api.depends('expiration_date')
    def _compute_expiry_status(self):
        now = fields.Datetime.now()
        soon = now + datetime.timedelta(days=30)
        for lot in self:
            if lot.expiration_date:
                lot.is_expired = lot.expiration_date <= now
                lot.is_expiring_soon = not lot.is_expired and lot.expiration_date <= soon
            else:
                lot.is_expired = False
                lot.is_expiring_soon = False

    @api.depends('product_id')
    def _compute_purchase_details(self):
        for lot in self:
            default_curr = lot.company_id.currency_id or self.env.company.currency_id
            mls = self.env['stock.move.line'].search([
                ('lot_id', '=', lot.id),
                ('move_id.purchase_line_id', '!=', False)
            ], limit=1)
            pol = mls.move_id.purchase_line_id if mls else False
            if pol:
                lot.purchase_order_id = pol.order_id.id
                lot.purchase_line_id = pol.id
                lot.currency_id = pol.currency_id or default_curr
                lot.purchase_price = pol.price_unit
                if pol.currency_id and pol.currency_id != default_curr:
                    lot.standard_price = pol.currency_id._convert(
                        pol.price_unit,
                        default_curr,
                        pol.company_id or self.env.company,
                        pol.order_id.date_order or fields.Date.today()
                    )
                else:
                    lot.standard_price = pol.price_unit
            else:
                lot.currency_id = default_curr
                # If manufactured (Finished Good)
                mo = self.env['mrp.production'].search([('lot_producing_ids', 'in', lot.ids)], limit=1)
                if mo:
                    cost = getattr(mo, 'total_component_cost', 0.0)
                    qty = mo.product_qty or 1.0
                    price = (cost / qty) if qty else 0.0
                    lot.purchase_price = price or lot.product_id.standard_price
                else:
                    lot.purchase_price = lot.product_id.standard_price or 0.0
                if not lot.standard_price and lot.purchase_price:
                    lot.standard_price = lot.purchase_price
