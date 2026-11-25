# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    has_ticket_dashboard_access = fields.Boolean(
        string="15 KPIs Management Dashboard Access",
        compute="_compute_ticket_dashboard_access",
        inverse="_inverse_ticket_dashboard_access",
        help="If enabled, this user is authorized to view and access the 15 Core KPIs Management Dashboard.",
    )

    def _compute_ticket_dashboard_access(self):
        group_dashboard = self.env.ref('custom_ticket_monitoring.group_ticket_dashboard', raise_if_not_found=False)
        for user in self:
            user.has_ticket_dashboard_access = bool(group_dashboard and group_dashboard in user.group_ids)

    def _inverse_ticket_dashboard_access(self):
        group_dashboard = self.env.ref('custom_ticket_monitoring.group_ticket_dashboard', raise_if_not_found=False)
        if not group_dashboard:
            return
        for user in self:
            if user.has_ticket_dashboard_access:
                user.group_ids = [(4, group_dashboard.id)]
            else:
                user.group_ids = [(3, group_dashboard.id)]
