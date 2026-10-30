# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_currency_id',
        help='Company currency for manufacturing order costs.',
    )

    total_component_cost = fields.Monetary(
        string='Total Overall Price',
        compute='_compute_total_component_cost',
        currency_field='currency_id',
        store=True,
        help='Total overall price / cost of components in this manufacturing order.',
    )

    @api.depends('company_id')
    def _compute_currency_id(self):
        for order in self:
            order.currency_id = order.company_id.currency_id or self.env.company.currency_id

    @api.depends('move_raw_ids.total_price', 'move_raw_ids.state')
    def _compute_total_component_cost(self):
        for order in self:
            order.total_component_cost = sum(
                m.total_price for m in order.move_raw_ids if m.state != 'cancel'
            )

    def _get_move_raw_values(self, product, product_uom_qty, product_uom, operation_id=False, bom_line=False):
        vals = super()._get_move_raw_values(
            product, product_uom_qty, product_uom, operation_id, bom_line
        )
        company = self.company_id or self.env.company
        price = self.env['stock.move']._get_move_component_price(product, product_uom, company)
        vals['unit_price'] = price
        return vals
