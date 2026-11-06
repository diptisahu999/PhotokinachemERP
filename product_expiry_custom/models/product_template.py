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
<<<<<<< Updated upstream
        try:
            # 1. Auto-enable expiration date on tracked products
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

            # 2. Set default removal strategy to FEFO (First Expiry First Out) on categories and locations
            fefo = self.env['product.removal'].search([('method', '=', 'fefo')], limit=1)
            if fefo:
                categories = self.env['product.category'].search([('removal_strategy_id', '=', False)])
                if categories:
                    categories.write({'removal_strategy_id': fefo.id})
                internal_locations = self.env['stock.location'].search([
                    ('usage', '=', 'internal'),
                    ('removal_strategy_id', '=', False)
                ])
                if internal_locations:
                    internal_locations.write({'removal_strategy_id': fefo.id})
        except Exception:
            # Protect server startup from failing before schema migration
            pass
=======
        # 1. Auto-enable expiration date on tracked products
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

        # 2. Set default removal strategy to FEFO (First Expiry First Out) on categories and locations
        fefo = self.env['product.removal'].search([('method', '=', 'fefo')], limit=1)
        if fefo:
            categories = self.env['product.category'].search([('removal_strategy_id', '=', False)])
            if categories:
                categories.write({'removal_strategy_id': fefo.id})
            internal_locations = self.env['stock.location'].search([
                ('usage', '=', 'internal'),
                ('removal_strategy_id', '=', False)
            ])
            if internal_locations:
                internal_locations.write({'removal_strategy_id': fefo.id})

        # 3. Compute purchase details and expiry status on all existing lots
        lots = self.env['stock.lot'].search([])
        if lots:
            lots._compute_purchase_details()
            lots._compute_expiry_status()
>>>>>>> Stashed changes

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
