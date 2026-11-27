# -*- coding: utf-8 -*-
from odoo import models, fields


class UserDesignation(models.Model):
    _name = 'user.designation'
    _description = 'User Designation'
    _order = 'name'

    name = fields.Char(string='Designation Name', required=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)

    user_ids = fields.One2many('res.users', 'designation_id', string='Assigned Users')
    user_count = fields.Integer(string='Users Count', compute='_compute_user_count')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Designation name must be unique!')
    ]

    def _compute_user_count(self):
        for rec in self:
            rec.user_count = len(rec.user_ids)


class UserSubDepartment(models.Model):
    _name = 'user.sub_department'
    _description = 'User Sub Department'
    _order = 'name'

    name = fields.Char(string='Sub Department Name', required=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)

    user_ids = fields.One2many('res.users', 'sub_department_id', string='Assigned Users')
    user_count = fields.Integer(string='Users Count', compute='_compute_user_count')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Sub Department name must be unique!')
    ]

    def _compute_user_count(self):
        for rec in self:
            rec.user_count = len(rec.user_ids)
