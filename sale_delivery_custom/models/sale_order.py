# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _default_delivery_term_id(self):
        return self.env['delivery.term'].search([], limit=1)

    delivery_term_id = fields.Many2one(
        comodel_name='delivery.term',
        string='Delivery Term',
        default=_default_delivery_term_id,
        help='Delivery term for this order (e.g. As soon as possible, Ex-Works, Door Delivery).'
    )

    @api.onchange('delivery_term_id')
    def _onchange_delivery_term_id(self):
        if self.delivery_term_id and self.delivery_term_id.picking_policy:
            self.picking_policy = self.delivery_term_id.picking_policy

    @api.onchange('picking_policy')
    def _onchange_picking_policy(self):
        if self.picking_policy and not self.delivery_term_id:
            term = self.env['delivery.term'].search([('picking_policy', '=', self.picking_policy)], limit=1)
            if term:
                self.delivery_term_id = term

    @api.onchange('partner_id')
    def _onchange_partner_id_shipping_check(self):
        if self.partner_id:
            self.partner_shipping_id = self.partner_id.address_get(['delivery'])['delivery']
        else:
            self.partner_shipping_id = False

