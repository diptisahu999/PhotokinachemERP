# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_lost_customer = fields.Boolean(
        string='Lost Customer',
        compute='_compute_is_lost_customer',
        store=True,
        readonly=False,
        help="Indicates if the selected customer is flagged as a Lost Customer.",
    )
    lost_status_display = fields.Char(
        string='Customer Status',
        compute='_compute_lost_status_display',
        help="Text displayed inside badge on quotations list view",
    )
    partner_last_deal_date = fields.Datetime(
        string='Last Deal / Order Date',
        related='partner_id.last_deal_or_order_date',
        readonly=True,
    )
    partner_days_inactive = fields.Integer(
        string='Customer Inactive Days',
        related='partner_id.days_since_last_activity',
        readonly=True,
    )

    @api.depends('partner_id', 'partner_id.is_lost_customer', 'state')
    def _compute_is_lost_customer(self):
        for order in self:
            if order.state in ('sale', 'done'):
                order.is_lost_customer = False
            elif order.partner_id:
                order.is_lost_customer = order.partner_id.is_lost_customer
            else:
                order.is_lost_customer = False

    @api.depends('is_lost_customer')
    def _compute_lost_status_display(self):
        for order in self:
            order.lost_status_display = 'Lost Customer' if order.is_lost_customer else False

    @api.onchange('partner_id')
    def _onchange_partner_id_lost_customer(self):
        if self.partner_id:
            self.partner_id.update_lost_customer_status()
            if self.state not in ('sale', 'done'):
                self.is_lost_customer = self.partner_id.is_lost_customer
            else:
                self.is_lost_customer = False

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if order.partner_id and order.partner_id.is_lost_customer:
                order.partner_id.action_reactivate_customer(order_name=order.name)
            order.is_lost_customer = False
        return res

