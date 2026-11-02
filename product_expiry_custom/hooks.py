# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

def post_init_hook(env):
    """
    Auto-enable use_expiration_date and set default expiration_time for all tracked products.
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

