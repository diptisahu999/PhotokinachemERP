# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('partner_id')
    def _onchange_partner_id_set_zone(self):
        """Auto-populate Zone / Sales Team when Customer is selected on Quotation."""
        if self.partner_id:
            if self.partner_id.team_id:
                self.team_id = self.partner_id.team_id
            elif self.partner_id.state_id or self.partner_id.country_id:
                zone = self.env['crm.team'].get_zone_for_location(
                    state_id=self.partner_id.state_id.id if self.partner_id.state_id else False,
                    country_id=self.partner_id.country_id.id if self.partner_id.country_id else False
                )
                if zone:
                    self.team_id = zone

    @api.model_create_multi
    def create(self, vals_list):
        """Ensure Zone is populated on Quotation / Sales Order creation."""
        for vals in vals_list:
            if not vals.get('team_id') and vals.get('partner_id'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                if partner.team_id:
                    vals['team_id'] = partner.team_id.id
                elif partner.state_id or partner.country_id:
                    zone = self.env['crm.team'].get_zone_for_location(
                        state_id=partner.state_id.id if partner.state_id else False,
                        country_id=partner.country_id.id if partner.country_id else False
                    )
                    if zone:
                        vals['team_id'] = zone.id

        return super().create(vals_list)
