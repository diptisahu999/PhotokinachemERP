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
        help='Unit price / cost of the component in company currency (converts foreign vendor currencies like USD to INR).',
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
    def _get_move_component_price(self, product, product_uom=None, company=None, date=None):
        """Return unit price for product in company currency (e.g. INR).
        Checks standard_price (Cost); if 0, falls back to vendor purchase price
        with currency conversion (e.g. USD to INR using daily exchange rates),
        or last confirmed PO price, or Sales Price.
        """
        if not product:
            return 0.0
        company = company or self.env.company
        date = date or fields.Date.today()
        price = product.with_company(company).standard_price

        # If standard_price is 0, check vendor pricelist (seller_ids)
        if not price and product.seller_ids:
            seller = product._select_seller(
                quantity=1.0,
                uom_id=product_uom or product.uom_id,
                params={'company_id': company.id}
            ) or product.seller_ids[0]
            seller_price = seller.price
            if seller.currency_id and seller.currency_id != company.currency_id:
                price = seller.currency_id._convert(
                    seller_price,
                    company.currency_id,
                    company,
                    date
                )
            else:
                price = seller_price

        # If still 0, check latest confirmed purchase order
        if not price:
            last_po_line = self.env['purchase.order.line'].search([
                ('product_id', '=', product.id),
                ('state', 'in', ['purchase', 'done']),
                ('company_id', '=', company.id)
            ], order='date_order desc, id desc', limit=1)
            if last_po_line and last_po_line.price_unit:
                po_currency = last_po_line.order_id.currency_id
                po_date = last_po_line.order_id.date_order or date
                if po_currency and po_currency != company.currency_id:
                    price = po_currency._convert(
                        last_po_line.price_unit,
                        company.currency_id,
                        company,
                        po_date
                    )
                else:
                    price = last_po_line.price_unit

        # If still 0, fallback to sales price
        if not price:
            price = product.lst_price or product.list_price or 0.0

        # Adjust for Unit of Measure differences
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
                date = (
                    move.raw_material_production_id.date_start
                    or move.raw_material_production_id.create_date
                    or fields.Date.today()
                )
                move.unit_price = self._get_move_component_price(
                    move.product_id, move.product_uom, company, date=date
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
            date = (
                self.raw_material_production_id.date_start
                or fields.Date.today()
            )
            self.unit_price = self._get_move_component_price(
                self.product_id, self.product_uom, company, date=date
            )

    @api.onchange('unit_price', 'product_uom_qty')
    def _onchange_pricing(self):
        qty = self.quantity if (
            self.raw_material_production_id
            and self.raw_material_production_id.state == 'done'
            and self.quantity
        ) else self.product_uom_qty
        self.total_price = (self.unit_price or 0.0) * (qty or 0.0)
