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

    # --- Transportation Details ---
    transporter_id = fields.Many2one(
        comodel_name='res.partner',
        string='Transporter',
        help='Transporter / Carrier handling shipment.'
    )
    transport_mode = fields.Selection([
        ('1', 'By Road'),
        ('2', 'Rail'),
        ('3', 'Air'),
        ('4', 'Ship or Ship Cum Road/Rail'),
    ], string='Transportation Mode', default='1', help='Mode of transportation.')
    vehicle_type = fields.Selection([
        ('R', 'Regular'),
        ('O', 'Over Dimensional Cargo'),
    ], string='Vehicle Type', default='R')
    vehicle_no = fields.Char(string='Vehicle Number', help='Vehicle registration number (e.g. GJ26U0758).')
    distance = fields.Integer(string='Distance (km)', help='Distance in kilometers.')
    transportation_doc_no = fields.Char(string='Transporter Doc No', help='LR / Bilty / RR / Airway Bill No.')
    transportation_doc_date = fields.Date(string='Transporter Doc Date')

    # --- Company Bank Details ---
    company_partner_id = fields.Many2one(
        related='company_id.partner_id',
        string='Company Partner',
        readonly=True
    )
    company_bank_id = fields.Many2one(
        comodel_name='res.partner.bank',
        string='Company Bank Account',
        compute='_compute_company_bank_id',
        store=True,
        readonly=False,
        domain="[('partner_id', '=', company_partner_id)]",
        help='Company bank account details to display on quotation and reports.'
    )
    bank_name = fields.Char(
        related='company_bank_id.bank_id.name',
        string='Bank Name',
        readonly=True
    )
    bank_acc_number = fields.Char(
        related='company_bank_id.acc_number',
        string='Account Number',
        readonly=True
    )
    bank_bic = fields.Char(
        related='company_bank_id.bank_id.bic',
        string='IFSC / BIC',
        readonly=True
    )
    bank_acc_holder = fields.Char(
        related='company_bank_id.acc_holder_name',
        string='Account Holder',
        readonly=True
    )

    @api.depends('company_id')
    def _compute_company_bank_id(self):
        for order in self:
            if not order.company_bank_id and order.company_id:
                bank = self.env['res.partner.bank'].search([
                    ('partner_id', '=', order.company_id.partner_id.id)
                ], limit=1)
                order.company_bank_id = bank

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

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            for picking in order.picking_ids:
                vals = {}
                if order.transporter_id and not picking.transporter_id:
                    vals['transporter_id'] = order.transporter_id.id
                if order.transport_mode:
                    vals['transport_mode'] = order.transport_mode
                if order.vehicle_type:
                    vals['vehicle_type'] = order.vehicle_type
                if order.vehicle_no and not picking.vehicle_no:
                    vals['vehicle_no'] = order.vehicle_no
                if order.distance and not picking.distance:
                    vals['distance'] = order.distance
                if order.transportation_doc_no and not picking.transportation_doc_no:
                    vals['transportation_doc_no'] = order.transportation_doc_no
                if order.transportation_doc_date and not picking.transportation_doc_date:
                    vals['transportation_doc_date'] = order.transportation_doc_date
                if vals:
                    picking.write(vals)
        return res
