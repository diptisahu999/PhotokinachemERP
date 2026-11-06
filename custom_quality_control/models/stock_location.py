# -*- coding: utf-8 -*-
from odoo import models, fields


class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_qc_location = fields.Boolean(
        string='Is Quality Control Location',
        default=False,
        help='Check this box to treat this location as a temporary Quality Inspection holding area.'
    )
    is_quarantine_location = fields.Boolean(
        string='Is Quarantine Location',
        default=False,
        help='Check this box to treat this location as a Quarantine / Rejected material area.'
    )

