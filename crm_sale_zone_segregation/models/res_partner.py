# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    team_id = fields.Many2one(
        'crm.team',
        string='Assigned Zone / Sales Team',
        help='The Sales Team / Zone assigned to this customer.'
    )

    @api.onchange('state_id', 'country_id')
    def _onchange_location_set_zone(self):
        """Auto-suggest Zone / Sales Team based on Customer State or Country."""
        if self.state_id or self.country_id:
            zone = self.env['crm.team'].get_zone_for_location(
                state_id=self.state_id.id if self.state_id else False,
                country_id=self.country_id.id if self.country_id else False
            )
            if zone:
                self.team_id = zone

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-assign Zone on Customer creation if State/Country is provided."""
        for vals in vals_list:
            if not vals.get('team_id') and (vals.get('state_id') or vals.get('country_id')):
                zone = self.env['crm.team'].get_zone_for_location(
                    state_id=vals.get('state_id'),
                    country_id=vals.get('country_id')
                )
                if zone:
                    vals['team_id'] = zone.id
        return super().create(vals_list)
