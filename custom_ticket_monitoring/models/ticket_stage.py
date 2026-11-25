# -*- coding: utf-8 -*-
from odoo import models, fields

class TicketStage(models.Model):
    _name = 'ticket.stage'
    _description = 'Ticket Lifecycle Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    state = fields.Selection([
        ('draft', 'Draft / Submitted'),
        ('open', 'Open'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'Under Review / On Hold'),
        ('resolved', 'Resolved (Pending Verification)'),
        ('closed', 'Closed'),
        ('reopened', 'Reopened'),
    ], string='Related State', required=True, default='open')
    fold = fields.Boolean(string='Folded in Kanban', help="This stage will be folded by default in the Kanban view.")
    is_closed = fields.Boolean(string='Is Closed Stage', help="Tickets in this stage are considered completed.")
    description = fields.Text(string='Description')
