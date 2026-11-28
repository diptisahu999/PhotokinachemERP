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

    @api.depends('group_ids')
    def _compute_has_apps_access(self):
        apps_group = self.env.ref('custom_hide_menus.group_apps_access', raise_if_not_found=False)
        admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
        for user in self:
            is_admin = bool(admin_group and admin_group in (user.all_group_ids if hasattr(user, 'all_group_ids') else user.group_ids))
            has_grp = bool(apps_group and apps_group in (user.all_group_ids if hasattr(user, 'all_group_ids') else user.group_ids))
            user.has_apps_access = bool(has_grp or is_admin)

    def _inverse_has_apps_access(self):
        apps_group = self.env.ref('custom_hide_menus.group_apps_access', raise_if_not_found=False)
        if not apps_group:
            return
        for user in self:
            if user.has_apps_access:
                self.env.cr.execute("""
                    INSERT INTO res_groups_users_rel (gid, uid)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                """, (apps_group.id, user.id))
            else:
                self.env.cr.execute("""
                    DELETE FROM res_groups_users_rel
                    WHERE gid = %s AND uid = %s;
                """, (apps_group.id, user.id))
            user.invalidate_recordset(['group_ids'])
            if hasattr(user, 'all_group_ids'):
                user.invalidate_recordset(['all_group_ids'])

    def _search_has_apps_access(self, operator, value):
        apps_group = self.env.ref('custom_hide_menus.group_apps_access', raise_if_not_found=False)
        admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
        gids = []
        if apps_group:
            gids.append(apps_group.id)
        if admin_group:
            gids.append(admin_group.id)

        if (operator in ('=', '==') and value) or (operator in ('!=', '<>') and not value):
            return [('group_ids', 'in', gids)]
        else:
            return [('group_ids', 'not in', gids)]

    def action_toggle_apps_access(self):
        """Button action to grant or revoke Apps module access."""
        for user in self:
            user.has_apps_access = not user.has_apps_access
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Apps Access Updated"),
                'message': _("Apps module access updated for %s.") % self.name,
                'type': 'info',
                'sticky': False,
            }
        }

    def init(self):
        super().init()
        try:
            apps_group = self.env.ref('custom_hide_menus.group_apps_access', raise_if_not_found=False)
            admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
            if apps_group and admin_group:
                self.env.cr.execute("""
                    INSERT INTO res_groups_users_rel (gid, uid)
                    SELECT %s, u.uid FROM res_groups_users_rel u
                    WHERE u.gid = %s
                    ON CONFLICT DO NOTHING;
                """, (apps_group.id, admin_group.id))
        except Exception:
            pass
