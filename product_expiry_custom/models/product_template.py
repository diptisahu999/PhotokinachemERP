# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    expiry_date = fields.Date(
        string='Expiry Date',
        help='Direct expiration date of the product.',
        tracking=True,
    )

    def _register_hook(self):
        res = super()._register_hook()
        products = self.search([
            ('tracking', 'in', ('lot', 'serial')),
            '|', ('use_expiration_date', '=', False), ('expiration_time', '=', 0)
        ])
        for p in products:
            vals = {}
            if not p.use_expiration_date:
                vals['use_expiration_date'] = True
            if not p.expiration_time:
                vals['expiration_time'] = 365
            if vals:
                p.write(vals)
        return res

    @api.onchange('tracking')
    def _onchange_tracking_auto_expiry(self):
        if self.tracking in ('lot', 'serial'):
            self.use_expiration_date = True
            if not self.expiration_time:
                self.expiration_time = 365

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('tracking') in ('lot', 'serial'):
                if 'use_expiration_date' not in vals:
                    vals['use_expiration_date'] = True
                if not vals.get('expiration_time'):
                    vals['expiration_time'] = 365
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('tracking') in ('lot', 'serial'):
            if 'use_expiration_date' not in vals:
                vals['use_expiration_date'] = True
            if 'expiration_time' not in vals and all(not p.expiration_time for p in self):
                vals['expiration_time'] = 365
        return super().write(vals)
