# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.osv import expression

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_sale = fields.Boolean(
        string='Sales',
        default=lambda self: self.env.context.get('res_partner_search_mode') != 'supplier',
        help='Check to make this contact available in CRM and Sales modules.'
    )
    is_purchase = fields.Boolean(
        string='Purchase',
        default=lambda self: self.env.context.get('res_partner_search_mode') == 'supplier',
        help='Check to make this contact available in Purchase module.'
    )

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        search_mode = self.env.context.get('res_partner_search_mode')
        if search_mode == 'customer':
            domain = expression.AND([domain or [], [('is_sale', '=', True)]])
        elif search_mode == 'supplier':
            domain = expression.AND([domain or [], [('is_purchase', '=', True)]])
        return super().name_search(name=name, domain=domain, operator=operator, limit=limit)
