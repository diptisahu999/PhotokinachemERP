# -*- coding: utf-8 -*-
import json
import logging
import urllib.request
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = 'res.company'

    auto_currency_rate_sync = fields.Boolean(
        string='Automatic Daily Currency Rate Sync',
        default=True,
        help='Automatically fetch and update foreign exchange rates (e.g. USD, EUR) daily.'
    )
    last_currency_rate_sync = fields.Datetime(
        string='Last Currency Sync',
        readonly=True,
        help='Timestamp of the last successful currency rate update.'
    )
    currency_rate_provider = fields.Selection([
        ('frankfurter', 'European Central Bank (Frankfurter API)'),
        ('er_api', 'ExchangeRate-API (open.er-api.com)'),
    ], string='Currency Provider', default='frankfurter')

    def _fetch_rates_from_frankfurter(self, base_currency):
        url = f'https://api.frankfurter.app/latest?from={base_currency}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Odoo Currency Sync)'})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('rates', {})

    def _fetch_rates_from_er_api(self, base_currency):
        url = f'https://open.er-api.com/v6/latest/{base_currency}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Odoo Currency Sync)'})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('rates', {})

    def _fetch_exchange_rates(self, base_currency):
        """Fetch rates using the configured provider with automatic fallback."""
        rates = {}
        if self.currency_rate_provider == 'frankfurter':
            try:
                rates = self._fetch_rates_from_frankfurter(base_currency)
            except Exception as e:
                _logger.warning("Frankfurter API failed (%s), attempting fallback to ExchangeRate-API...", e)
                try:
                    rates = self._fetch_rates_from_er_api(base_currency)
                except Exception as fallback_err:
                    _logger.error("All exchange rate providers failed: %s", fallback_err)
        else:
            try:
                rates = self._fetch_rates_from_er_api(base_currency)
            except Exception as e:
                _logger.warning("ExchangeRate-API failed (%s), attempting fallback to Frankfurter...", e)
                try:
                    rates = self._fetch_rates_from_frankfurter(base_currency)
                except Exception as fallback_err:
                    _logger.error("All exchange rate providers failed: %s", fallback_err)
        return rates

    def action_sync_currency_rates(self):
        """Fetch and update currency rates for active currencies against the company currency."""
        today = fields.Date.today()
        updated_details = []

        for company in self:
            if not company.auto_currency_rate_sync and not self.env.context.get('force_sync'):
                continue

            base_currency = company.currency_id.name
            # Find all active currencies for this company (excluding base currency)
            active_currencies = self.env['res.currency'].search([
                ('active', '=', True),
                ('name', '!=', base_currency)
            ])
            if not active_currencies:
                _logger.info("No active foreign currencies to update for company %s", company.name)
                continue

            rates_dict = company._fetch_exchange_rates(base_currency)
            if not rates_dict:
                _logger.warning("Failed to fetch exchange rates for company %s (base %s)", company.name, base_currency)
                continue

            rate_model = self.env['res.currency.rate']
            for currency in active_currencies:
                rate_val = rates_dict.get(currency.name)
                if not rate_val or rate_val <= 0:
                    continue

                existing_rate = rate_model.search([
                    ('company_id', '=', company.id),
                    ('currency_id', '=', currency.id),
                    ('name', '=', today),
                ], limit=1)

                if existing_rate:
                    existing_rate.write({'rate': rate_val})
                else:
                    existing_rate = rate_model.create({
                        'company_id': company.id,
                        'currency_id': currency.id,
                        'name': today,
                        'rate': rate_val,
                    })

                inv_rate = round(1.0 / rate_val, 4) if rate_val else 0
                updated_details.append(f"{currency.name}: 1 {currency.name} = {inv_rate} {base_currency}")

            company.write({'last_currency_rate_sync': fields.Datetime.now()})

        _logger.info("Currency rate sync completed: %s", ", ".join(updated_details) if updated_details else "None")
        return updated_details

    @api.model
    def cron_update_currency_rates(self):
        """Called daily by the scheduled action."""
        companies = self.search([('auto_currency_rate_sync', '=', True)])
        companies.action_sync_currency_rates()

