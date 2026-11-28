# -*- coding: utf-8 -*-
from odoo import models, fields

class TicketCategory(models.Model):
    _name = 'ticket.category'
    _description = 'Ticket Issue Category'
    _order = 'department_id, sequence, name'

    name = fields.Char(string='Category / Issue Type', required=True, translate=True)
    department_id = fields.Many2one('ticket.department', string='Department', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    default_priority = fields.Selection([
        ('0', '0 stars — None'),
        ('1', '1 star — Low'),
        ('2', '2 stars — Normal'),
        ('3', '3 stars — High'),
    ], string='Default Priority', default='1')
    default_owner_id = fields.Many2one('res.users', string='Default Owner / SPOC')
    description = fields.Text(string='Description / Guidance')
    active = fields.Boolean(string='Active', default=True)
