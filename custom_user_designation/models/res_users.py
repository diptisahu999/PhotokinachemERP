# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    designation_id = fields.Many2one(
        'user.designation',
        string='Designation',
        copy=False,
        ondelete='set null',
        help="Job designation of the user (e.g. Director, Manager, Assistant, Executive, Supervisor)."
    )
    sub_department_id = fields.Many2one(
        'user.sub_department',
        string='Sub Department',
        copy=False,
        ondelete='set null',
        help="Sub department or team (e.g. Accounts, Dispatch, Sales, Purchase, Production)."
    )

    designation = fields.Char(
        string='Designation Name',
        related='designation_id.name',
        readonly=True,
        help="Text representation of the designation."
    )
    sub_department = fields.Char(
        string='Sub Department Name',
        related='sub_department_id.name',
        readonly=True,
        help="Text representation of the sub department."
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('designation_id') and not vals.get('function'):
                desig = self.env['user.designation'].browse(vals['designation_id'])
                if desig.exists():
                    vals['function'] = desig.name
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('designation_id') and not vals.get('function'):
            desig = self.env['user.designation'].browse(vals['designation_id'])
            if desig.exists():
                vals['function'] = desig.name
        return super().write(vals)

    @classmethod
    def _ensure_user_columns_exist(cls, env):
        try:
            env.cr.execute("""
                ALTER TABLE res_users ADD COLUMN IF NOT EXISTS designation_id INTEGER;
                ALTER TABLE res_users ADD COLUMN IF NOT EXISTS sub_department_id INTEGER;
            """)
        except Exception:
            pass

    def _register_hook(self):
        super()._register_hook()
        self._ensure_user_columns_exist(self.env)

    def init(self):
        super().init()
        self._ensure_user_columns_exist(self.env)
