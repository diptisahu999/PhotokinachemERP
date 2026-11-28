# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_apps_access = fields.Boolean(
        string='Apps Module Access',
        compute='_compute_has_apps_access',
        inverse='_inverse_has_apps_access',
        search='_search_has_apps_access',
        help='When enabled, this user is granted access to the Apps module and can see it in the navigation sidebar.'
    )

    def _compute_has_apps_access(self):
        apps_group = self.env.ref('custom_hide_menus.group_apps_access', raise_if_not_found=False)
        for user in self:
            if not apps_group:
                user.has_apps_access = False
            else:
                user.has_apps_access = bool(apps_group in user.group_ids or user.has_group('custom_hide_menus.group_apps_access'))

    def _inverse_has_apps_access(self):
        apps_group = self.env.ref('custom_hide_menus.group_apps_access', raise_if_not_found=False)
        if not apps_group:
            return
        for user in self:
            if user.has_apps_access:
                if apps_group not in user.group_ids:
                    user.sudo().write({'group_ids': [(4, apps_group.id)]})
            else:
                if apps_group in user.group_ids or user.has_group('custom_hide_menus.group_apps_access'):
                    user.sudo().write({'group_ids': [(3, apps_group.id)]})

    def _search_has_apps_access(self, operator, value):
        apps_group = self.env.ref('custom_hide_menus.group_apps_access', raise_if_not_found=False)
        if not apps_group:
            return []
        positive = (operator == '=' and value) or (operator == '!=' and not value)
        return [('id', 'in' if positive else 'not in', apps_group.user_ids.ids)]

    def action_toggle_apps_access(self):
        """Button action to grant or revoke Apps module access."""
        for user in self:
            user.has_apps_access = not user.has_apps_access
        new_state = "enabled" if self.has_apps_access else "disabled"
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Apps Access Updated"),
                'message': _("Apps module access has been %s for %s.") % (new_state, self.name),
                'type': 'success',
                'sticky': False,
            }
        }
