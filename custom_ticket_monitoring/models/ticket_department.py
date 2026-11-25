# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class TicketDepartment(models.Model):
    _name = 'ticket.department'
    _description = 'Ticket Department'
    _order = 'sequence, name'

    name = fields.Char(string='Department Name', required=True, translate=True)
    code = fields.Char(string='Department Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    hod_id = fields.Many2one('res.users', string='Department Head (HOD)')
    member_ids = fields.Many2many('res.users', 'ticket_dept_users_rel', 'dept_id', 'user_id', string='Department Members')
    sla_target_percent = fields.Float(string='SLA Target (%)', default=95.0, help="Initial monthly SLA compliance target percentage.")
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(string='Active', default=True)

    ticket_count = fields.Integer(string='Ticket Count', compute='_compute_ticket_count')
    open_ticket_count = fields.Integer(string='Open Tickets', compute='_compute_ticket_count')

    category_ids = fields.One2many('ticket.category', 'department_id', string='Categories')

    @api.constrains('code')
    def _check_code_unique(self):
        for dept in self:
            if dept.code and self.search_count([('code', '=', dept.code), ('id', '!=', dept.id)]) > 0:
                raise ValidationError(_("Department Code '%s' must be unique!") % dept.code)

    def _compute_ticket_count(self):
        for dept in self:
            tickets = self.env['ticket.monitoring'].search([('assigned_department_id', '=', dept.id)])
            dept.ticket_count = len(tickets)
            dept.open_ticket_count = len(tickets.filtered(lambda t: t.state not in ('closed',)))

    def action_view_department_tickets(self):
        self.ensure_one()
        return {
            'name': f'{self.name} Tickets',
            'type': 'ir.actions.act_window',
            'res_model': 'ticket.monitoring',
            'view_mode': 'kanban,list,form,pivot,graph',
            'domain': [('assigned_department_id', '=', self.id)],
            'context': {'default_assigned_department_id': self.id},
        }
