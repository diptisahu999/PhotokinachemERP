# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_currency_id',
        store=True,
        help='Company currency for cost display.',
    )

    total_bom_cost = fields.Float(
        string='Total BoM Cost',
        digits='Product Price',
        compute='_compute_bom_cost_summary',
        store=True,
        help='Total cost of all components in this BoM batch.',
    )

    unit_cost = fields.Float(
        string='Cost per Unit',
        digits='Product Price',
        compute='_compute_bom_cost_summary',
        store=True,
        help='Manufacturing cost per finished unit (Total BoM Cost / BoM Quantity).',
    )

    @api.depends('company_id')
    def _compute_currency_id(self):
        for bom in self:
            bom.currency_id = bom.company_id.currency_id or self.env.company.currency_id

    @api.depends('bom_line_ids.total_cost', 'product_qty')
    def _compute_bom_cost_summary(self):
        for bom in self:
            total = sum(bom.bom_line_ids.mapped('total_cost'))
            bom.total_bom_cost = total
            qty = bom.product_qty or 1.0
            bom.unit_cost = (total / qty) if qty > 0 else total

    def action_recompute_bom_costs(self):
        """Force recomputation of component unit costs from latest product standard price/vendor prices."""
        for bom in self:
            bom.bom_line_ids._compute_cost()
            bom.bom_line_ids._compute_total_cost()
            bom._compute_bom_cost_summary()


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='bom_id.currency_id',
        store=True,
        readonly=True,
    )

    cost = fields.Float(
        string='Cost',
        digits='Product Price',
        compute='_compute_cost',
        store=True,
        readonly=False,
        help='Unit cost of the component in company currency. Defaults to standard price/cost or vendor price.',
    )

    total_cost = fields.Float(
        string='Total Cost',
        digits='Product Price',
        compute='_compute_total_cost',
        store=True,
        help='Total line cost = Quantity * Unit Cost.',
    )

    @api.depends('product_id', 'product_uom_id', 'bom_id.company_id')
    def _compute_cost(self):
        stock_move_obj = self.env['stock.move']
        for line in self:
            if line.product_id:
                company = line.bom_id.company_id or self.env.company
                line.cost = stock_move_obj._get_move_component_price(
                    line.product_id,
                    product_uom=line.product_uom_id,
                    company=company,
                    date=fields.Date.today()
                )
            else:
                line.cost = 0.0

    @api.depends('product_qty', 'cost')
    def _compute_total_cost(self):
        for line in self:
            line.total_cost = (line.product_qty or 0.0) * (line.cost or 0.0)
