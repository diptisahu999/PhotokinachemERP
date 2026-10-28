# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    zone_code = fields.Char(
        string='Zone Code',
        size=10,
        help='Short identifier for this Zone (e.g., NZ for North Zone, WZ for West Zone).'
    )
    is_zone = fields.Boolean(
        string='Is Zone',
        default=True,
        help='Indicates whether this Sales Team operates as a geographical Zone.'
    )
    state_ids = fields.Many2many(
        'res.country.state',
        'crm_team_state_rel',
        'team_id',
        'state_id',
        string='Covered States / Provinces',
        help='Geographical states/provinces routed to this Zone.'
    )
    country_ids = fields.Many2many(
        'res.country',
        'crm_team_country_rel',
        'team_id',
        'country_id',
        string='Covered Countries',
        help='Geographical countries routed to this Zone.'
    )

    @api.model
    def get_zone_for_location(self, state_id=False, country_id=False):
        """
        Find the active Zone (Sales Team) assigned to a given state or country.
        Returns crm.team record or False.
        """
        if state_id:
            team = self.search([
                ('active', '=', True),
                ('is_zone', '=', True),
                ('state_ids', 'in', [state_id if isinstance(state_id, int) else state_id.id]),
            ], limit=1)
            if team:
                return team

        if country_id:
            team = self.search([
                ('active', '=', True),
                ('is_zone', '=', True),
                ('country_ids', 'in', [country_id if isinstance(country_id, int) else country_id.id]),
            ], limit=1)
            if team:
                return team

        return False
