# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """Backfill unit_price, total_price, and total_component_cost for existing records."""
    moves = env['stock.move'].search([
        ('raw_material_production_id', '!=', False),
        ('product_id', '!=', False),
    ])
    for move in moves:
        company = (
            move.company_id
            or move.raw_material_production_id.company_id
            or env.company
        )
        price = env['stock.move']._get_move_component_price(
            move.product_id, move.product_uom, company
        )
        move.write({'unit_price': price})
    productions = env['mrp.production'].search([])
    for production in productions:
        production._compute_total_component_cost()
