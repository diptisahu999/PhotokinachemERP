# -*- coding: utf-8 -*-
from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

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
    ], string='Transportation Mode', default='1')
    vehicle_type = fields.Selection([
        ('R', 'Regular'),
        ('O', 'Over Dimensional Cargo'),
    ], string='Vehicle Type', default='R')
    vehicle_no = fields.Char(string='Vehicle Number')
    distance = fields.Integer(string='Distance (km)')
    transportation_doc_no = fields.Char(string='Transporter Doc No')
    transportation_doc_date = fields.Date(string='Transporter Doc Date')

    def action_l10n_in_ewaybill_create(self):
        res = super().action_l10n_in_ewaybill_create()
        if hasattr(self, 'l10n_in_ewaybill_ids') and self.l10n_in_ewaybill_ids:
            ewaybill = self.l10n_in_ewaybill_ids[0]
            vals = {}
            if self.transporter_id and not ewaybill.transporter_id:
                vals['transporter_id'] = self.transporter_id.id
            if self.transport_mode and not ewaybill.mode:
                vals['mode'] = self.transport_mode
            if self.vehicle_type and not ewaybill.vehicle_type:
                vals['vehicle_type'] = self.vehicle_type
            if self.vehicle_no and not ewaybill.vehicle_no:
                vals['vehicle_no'] = self.vehicle_no
            if self.distance and not ewaybill.distance:
                vals['distance'] = self.distance
            if self.transportation_doc_no and not ewaybill.transportation_doc_no:
                vals['transportation_doc_no'] = self.transportation_doc_no
            if self.transportation_doc_date and not ewaybill.transportation_doc_date:
                vals['transportation_doc_date'] = self.transportation_doc_date
            if vals:
                ewaybill.write(vals)
        return res

