# -*- coding: utf-8 -*-
from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_force_delete_purchase_access = fields.Boolean(
        string='Allow Force Delete Purchase Orders',
        compute='_compute_has_force_delete_purchase_access',
        inverse='_set_has_force_delete_purchase_access',
        store=False,
        help='If enabled, this user can forcefully delete Purchase Orders and RFQs regardless of state.'
    )

    def _compute_has_force_delete_purchase_access(self):
        group = self.env.ref(
            'custom_purchase_force_delete.group_allow_force_delete_purchase',
            raise_if_not_found=False
        )
        for user in self:
            user.has_force_delete_purchase_access = group in user.group_ids if group else False

    def _set_has_force_delete_purchase_access(self):
        group = self.env.ref(
            'custom_purchase_force_delete.group_allow_force_delete_purchase',
            raise_if_not_found=False
        )
        if not group:
            return
        for user in self:
            if user.has_force_delete_purchase_access:
                user.group_ids = [(4, group.id)]
            else:
                user.group_ids = [(3, group.id)]

