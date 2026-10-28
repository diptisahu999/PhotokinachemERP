# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    expiry_date = fields.Date(
        string='Expiry Date',
        help='Direct expiration date of the product.',
        tracking=True,
    )
