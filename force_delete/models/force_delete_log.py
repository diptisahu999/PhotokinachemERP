# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ForceDeleteLog(models.Model):
    _name = 'force.delete.log'
    _description = 'Force Delete Audit Log'
    _order = 'delete_date desc, id desc'

    name = fields.Char('Action Title', required=True)
    user_id = fields.Many2one('res.users', string='Deleted By', default=lambda self: self.env.user, required=True, readonly=True)
    delete_date = fields.Datetime('Timestamp', default=fields.Datetime.now, required=True, readonly=True)
    res_model = fields.Char('Model Technical Name', required=True, readonly=True)
    res_model_name = fields.Char('Document Type', readonly=True)
    record_ids_text = fields.Char('Record IDs', readonly=True)
    record_names = fields.Text('Deleted Record References', readonly=True)
    record_count = fields.Integer('Records Deleted Count', readonly=True)
    revert_stock = fields.Boolean('Stock Reverted', readonly=True)
    details = fields.Text('Audit Details & Summary', readonly=True)
