# -*- coding: utf-8 -*-
from . import models

def post_init_hook(env):
    partners = env['res.partner'].search([])
    for partner in partners:
        vals = {}
        if partner.id == 1 or partner.user_ids:
            vals['is_sale'] = True
            vals['is_purchase'] = True
        elif partner.supplier_rank > 0 or 'distribut' in (partner.name or '').lower():
            vals['is_purchase'] = True
            if partner.customer_rank == 0:
                vals['is_sale'] = False
        elif partner.customer_rank > 0 or 'apex' in (partner.name or '').lower():
            vals['is_sale'] = True
            if partner.supplier_rank == 0:
                vals['is_purchase'] = False
        if vals:
            partner.write(vals)
