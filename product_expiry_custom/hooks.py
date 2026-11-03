# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

def post_init_hook(env):
    """
    Auto-enable use_expiration_date and set default expiration_time for all tracked products,
    and configure FEFO removal strategy for customer deliveries.
    """
    products = env['product.template'].search([('tracking', 'in', ('lot', 'serial'))])
    for p in products:
        vals = {}
        if not p.use_expiration_date:
            vals['use_expiration_date'] = True
        if not p.expiration_time:
            vals['expiration_time'] = 365
        if vals:
            p.write(vals)

    fefo = env['product.removal'].search([('method', '=', 'fefo')], limit=1)
    if fefo:
        env['product.category'].search([('removal_strategy_id', '=', False)]).write({
            'removal_strategy_id': fefo.id
        })
        env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('removal_strategy_id', '=', False)
        ]).write({
            'removal_strategy_id': fefo.id
        })
