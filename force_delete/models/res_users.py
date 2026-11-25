# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    allow_force_delete = fields.Boolean(
        string='Allow Force Delete',
        compute='_compute_allow_force_delete',
        inverse='_inverse_allow_force_delete',
        search='_search_allow_force_delete',
        help='If enabled, this user is authorized to force delete locked records (Manufacturing Orders, Transfers, Invoices, etc.).'
    )

    def _compute_allow_force_delete(self):
        group = self.env.ref('force_delete.group_force_delete', raise_if_not_found=False)
        for user in self:
            if not group:
                user.allow_force_delete = False
            else:
                user.allow_force_delete = bool(group in user.group_ids or user.has_group('force_delete.group_force_delete'))

    def _inverse_allow_force_delete(self):
        group = self.env.ref('force_delete.group_force_delete', raise_if_not_found=False)
        if not group:
            return
        for user in self:
            if user.allow_force_delete:
                if group not in user.group_ids:
                    user.sudo().write({'group_ids': [(4, group.id)]})
            else:
                if group in user.group_ids:
                    user.sudo().write({'group_ids': [(3, group.id)]})

    def _search_allow_force_delete(self, operator, value):
        group = self.env.ref('force_delete.group_force_delete', raise_if_not_found=False)
        if not group:
            return []
        positive = (operator == '=' and value) or (operator == '!=' and not value)
        users = group.user_ids
        return [('id', 'in' if positive else 'not in', users.ids)]

    @classmethod
    def _clean_group_system_implied(cls, env):
        """Ensure group_system does not force force_delete on all admins, keeping it strictly userwise."""
        try:
            group_force_delete = env.ref('force_delete.group_force_delete', raise_if_not_found=False)
            group_system = env.ref('base.group_system', raise_if_not_found=False)
            if group_force_delete and group_system:
                env.cr.execute("""
                    DELETE FROM res_groups_implied_rel 
                    WHERE gid = %s AND hid = %s
                """, (group_system.id, group_force_delete.id))
        except Exception:
            pass

    def init(self):
        super().init()
        self._clean_group_system_implied(self.env)
