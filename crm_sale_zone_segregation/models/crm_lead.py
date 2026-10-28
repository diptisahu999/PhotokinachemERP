# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.onchange('partner_id')
    def _onchange_partner_id_set_zone(self):
        """When customer is selected, inherit their Zone / Sales Team."""
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

    @api.onchange('state_id', 'country_id')
    def _onchange_location_set_zone(self):
        """Auto-suggest Zone based on Lead address location."""
        if (self.state_id or self.country_id) and not self.team_id:
            zone = self.env['crm.team'].get_zone_for_location(
                state_id=self.state_id.id if self.state_id else False,
                country_id=self.country_id.id if self.country_id else False
            )
            if zone:
                self.team_id = zone

    @api.model_create_multi
    def create(self, vals_list):
        """Ensure Zone is populated on creation if partner or location is provided."""
        for vals in vals_list:
            if not vals.get('team_id'):
                # 1. From Partner
                if vals.get('partner_id'):
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

                # 2. From Lead State / Country
                if not vals.get('team_id') and (vals.get('state_id') or vals.get('country_id')):
                    zone = self.env['crm.team'].get_zone_for_location(
                        state_id=vals.get('state_id'),
                        country_id=vals.get('country_id')
                    )
                    if zone:
                        vals['team_id'] = zone.id

        return super().create(vals_list)
