# -*- coding: utf-8 -*-
import datetime
from odoo import models, fields, api

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    expiration_date = fields.Datetime(
        string='Expiration Date',
        compute='_compute_expiration_date',
        inverse='_inverse_expiration_date',
        store=True,
        readonly=False,
        copy=False,
        help="Expiration date of the produced lot / batch."
    )

    @api.depends('lot_producing_ids', 'lot_producing_ids.expiration_date', 'product_id', 'product_id.use_expiration_date', 'product_id.expiration_time', 'date_finished')
    def _compute_expiration_date(self):
        for mo in self:
            if mo.lot_producing_ids and mo.lot_producing_ids[0].expiration_date:
                mo.expiration_date = mo.lot_producing_ids[0].expiration_date
            elif mo.product_id and mo.product_id.use_expiration_date:
                base_date = mo.date_finished or mo.date_start or fields.Datetime.now()
                duration = mo.product_id.expiration_time or 365
                mo.expiration_date = base_date + datetime.timedelta(days=duration)
            else:
                mo.expiration_date = False

    def _inverse_expiration_date(self):
        for mo in self:
            if mo.lot_producing_ids and mo.expiration_date:
                mo.lot_producing_ids.write({'expiration_date': mo.expiration_date})

    def _prepare_stock_lot_values(self):
        values = super()._prepare_stock_lot_values()
        if self.expiration_date:
            values['expiration_date'] = self.expiration_date
        elif self.product_id.use_expiration_date:
            base_date = self.date_finished or self.date_start or fields.Datetime.now()
            duration = self.product_id.expiration_time or 365
            values['expiration_date'] = base_date + datetime.timedelta(days=duration)
        return values

    def button_mark_done(self):
        for mo in self:
            if mo.lot_producing_ids and mo.expiration_date:
                mo.lot_producing_ids.filtered(lambda l: l.expiration_date != mo.expiration_date).write({
                    'expiration_date': mo.expiration_date
                })
        return super().button_mark_done()

