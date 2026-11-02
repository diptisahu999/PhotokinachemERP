# -*- coding: utf-8 -*-
import datetime
from odoo import models, fields, api

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.onchange('lot_name', 'product_id')
    def _onchange_lot_name_set_expiry(self):
        for line in self:
            if line.product_id and line.product_id.tracking != 'none' and not line.expiration_date:
                from_date = line.picking_id.scheduled_date or fields.Datetime.now()
                duration = line.product_id.expiration_time or 365
                line.expiration_date = from_date + datetime.timedelta(days=duration)

