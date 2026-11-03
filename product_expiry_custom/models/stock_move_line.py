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

    def _prepare_new_lot_vals(self):
        vals = super()._prepare_new_lot_vals()
        pol = self.move_id.purchase_line_id
        if pol:
            default_curr = self.company_id.currency_id or self.env.company.currency_id
            vals['currency_id'] = pol.currency_id.id
            vals['purchase_price'] = pol.price_unit
            vals['purchase_order_id'] = pol.order_id.id
            vals['purchase_line_id'] = pol.id
            if pol.currency_id and pol.currency_id != default_curr:
                vals['standard_price'] = pol.currency_id._convert(
                    pol.price_unit,
                    default_curr,
                    self.company_id or self.env.company,
                    pol.order_id.date_order or fields.Date.today()
                )
            else:
                vals['standard_price'] = pol.price_unit
        return vals

    def write(self, vals):
        res = super().write(vals)
        if 'lot_id' in vals and vals['lot_id']:
            for line in self:
                pol = line.move_id.purchase_line_id
                if pol and line.lot_id and not line.lot_id.purchase_price:
                    default_curr = line.company_id.currency_id or self.env.company.currency_id
                    vals_to_write = {
                        'currency_id': pol.currency_id.id,
                        'purchase_price': pol.price_unit,
                        'purchase_order_id': pol.order_id.id,
                        'purchase_line_id': pol.id,
                    }
                    if pol.currency_id and pol.currency_id != default_curr:
                        vals_to_write['standard_price'] = pol.currency_id._convert(
                            pol.price_unit,
                            default_curr,
                            line.company_id or self.env.company,
                            pol.order_id.date_order or fields.Date.today()
                        )
                    else:
                        vals_to_write['standard_price'] = pol.price_unit
                    line.lot_id.write(vals_to_write)
        return res
