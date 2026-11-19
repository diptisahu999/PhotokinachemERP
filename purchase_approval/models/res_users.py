# -*- coding: utf-8 -*-
from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    purchase_approval = fields.Boolean(
        string='Purchase Approval',
        default=False,
        tracking=True,
        help='If enabled, this user is allowed to approve or reject purchase requests and confirm them into Purchase Orders.'
    )

    @classmethod
    def _ensure_user_approval_column_exists(cls, env):
        try:
            env.cr.execute("""
                ALTER TABLE res_users ADD COLUMN IF NOT EXISTS purchase_approval boolean DEFAULT false;
            """)
        except Exception:
            pass

    def init(self):
        super().init()
        self._ensure_user_approval_column_exists(self.env)

    def _register_hook(self):
        super()._register_hook()
        self._ensure_user_approval_column_exists(self.env)
