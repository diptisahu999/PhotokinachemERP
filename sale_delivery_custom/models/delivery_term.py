# -*- coding: utf-8 -*-
from odoo import models, fields

class DeliveryTerm(models.Model):
    _name = 'delivery.term'
    _description = 'Delivery Term'
    _order = 'sequence, id'

    name = fields.Char(string='Delivery Term', required=True, translate=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(string='Sequence', default=10)
    picking_policy = fields.Selection([
        ('direct', 'As soon as possible'),
        ('one', 'When all products are ready'),
    ], string='Shipping Policy', default='direct',
       help='Underlying inventory picking policy mapped to this delivery term.')
    note = fields.Text(string='Description / Notes')
    active = fields.Boolean(default=True)

