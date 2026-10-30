# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_currency_id',
        help='Company currency for unit and total price display.',
    )

    available_qty = fields.Float(
        string='Available Qty',
        compute='_compute_available_qty',
        digits='Product Unit of Measure',
        help='Current physically available quantity in stock at the source location.',
    )

    unit_price = fields.Float(
        string='Unit Price',
        digits='Product Price',
        compute='_compute_unit_price',
        store=True,
        readonly=False,
        help='Unit price / cost of the component. Defaults to Cost, Vendor Price, or Sales Price.',
    )

    total_price = fields.Float(
        string='Total Price',
        digits='Product Price',
        compute='_compute_total_price',
        store=True,
        help='Total price = Unit Price * Quantity.',
    )

    # -------------------------------------------------------------------------
    # Price Helper
    # -------------------------------------------------------------------------

    @api.model
    def _get_move_component_price(self, product, product_uom=None, company=None):
        """Return unit price for product.
        Checks standard_price (Cost); if 0, falls back to vendor purchase price or Sales Price.
        """
        if not product:
            return 0.0
        company = company or self.env.company
        price = product.with_company(company).standard_price
        if not price and product.seller_ids:
            price = product.seller_ids[0].price
        if not price:
            price = product.lst_price or product.list_price or 0.0
        if product_uom and product.uom_id and product_uom != product.uom_id:
            price = product.uom_id._compute_price(price, product_uom)
        return price

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends('company_id', 'raw_material_production_id.company_id')
    def _compute_currency_id(self):
        for move in self:
            company = (
                move.company_id
                or (move.raw_material_production_id and move.raw_material_production_id.company_id)
                or self.env.company
            )
            move.currency_id = company.currency_id

    @api.depends('product_id', 'product_uom', 'location_id', 'raw_material_production_id.location_src_id')
    def _compute_available_qty(self):
        for move in self:
            if move.product_id:
                loc = move.location_id or (
                    move.raw_material_production_id and move.raw_material_production_id.location_src_id
                )
                prod = move.product_id.with_context(location=loc.id) if loc else move.product_id
                qty = prod.qty_available
                if move.product_uom and prod.uom_id and move.product_uom != prod.uom_id:
                    qty = prod.uom_id._compute_quantity(qty, move.product_uom)
                move.available_qty = qty
            else:
                move.available_qty = 0.0

    @api.depends('product_id', 'product_uom', 'company_id')
    def _compute_unit_price(self):
        for move in self:
            if move.product_id:
                company = move.company_id or (
                    move.raw_material_production_id and move.raw_material_production_id.company_id
                ) or self.env.company
                move.unit_price = self._get_move_component_price(
                    move.product_id, move.product_uom, company
                )
            else:
                move.unit_price = 0.0

    @api.depends('unit_price', 'product_uom_qty', 'quantity', 'raw_material_production_id.state')
    def _compute_total_price(self):
        for move in self:
            qty = move.quantity if (
                move.raw_material_production_id
                and move.raw_material_production_id.state == 'done'
                and move.quantity
            ) else move.product_uom_qty
            move.total_price = (move.unit_price or 0.0) * (qty or 0.0)

    # -------------------------------------------------------------------------
    # Onchange methods
    # -------------------------------------------------------------------------

    @api.onchange('product_id', 'product_uom')
    def _onchange_product_id_unit_price(self):
        if self.product_id:
            company = (
                self.company_id
                or (self.raw_material_production_id and self.raw_material_production_id.company_id)
                or self.env.company
            )
            self.unit_price = self._get_move_component_price(
                self.product_id, self.product_uom, company
            )

    @api.onchange('unit_price', 'product_uom_qty')
    def _onchange_pricing(self):
        qty = self.quantity if (
            self.raw_material_production_id
            and self.raw_material_production_id.state == 'done'
            and self.quantity
        ) else self.product_uom_qty
        self.total_price = (self.unit_price or 0.0) * (qty or 0.0)
