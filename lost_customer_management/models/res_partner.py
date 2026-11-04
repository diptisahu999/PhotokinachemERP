# -*- coding: utf-8 -*-
import datetime
from odoo import models, fields, api, _

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_lost_customer = fields.Boolean(
        string='Lost Customer',
        default=False,
        index=True,
        help="Automatically set to True if this customer has had no deals or confirmed orders in the last 6 months.",
    )
    lost_status_display = fields.Char(
        string='Lost Status',
        compute='_compute_lost_status_display',
        help="Display label for list views badge",
    )
    last_deal_or_order_date = fields.Datetime(
        string='Last Deal / Order Date',
        readonly=True,
        help="Date of the latest confirmed sale order or won CRM opportunity.",
    )
    days_since_last_activity = fields.Integer(
        string='Days Inactive',
        compute='_compute_days_since_last_activity',
        help="Number of days since last confirmed sale order or won opportunity.",
    )

    @api.depends('is_lost_customer')
    def _compute_lost_status_display(self):
        for partner in self:
            partner.lost_status_display = 'Lost Customer' if partner.is_lost_customer else False

    @api.depends('last_deal_or_order_date', 'create_date')
    def _compute_days_since_last_activity(self):
        now = fields.Datetime.now()
        for partner in self:
            ref_date = partner.last_deal_or_order_date or partner.create_date
            if ref_date:
                delta = now - ref_date
                partner.days_since_last_activity = max(0, delta.days)
            else:
                partner.days_since_last_activity = 0

    def _get_lost_customer_tag(self):
        tag = self.env.ref('lost_customer_management.partner_category_lost_customer', raise_if_not_found=False)
        if not tag:
            tag = self.env['res.partner.category'].search([('name', '=', 'Lost Customer')], limit=1)
            if not tag:
                tag = self.env['res.partner.category'].create({'name': 'Lost Customer', 'color': 1})
        return tag

    def update_lost_customer_status(self):
        """Check and update lost customer status for this partner."""
        tag = self._get_lost_customer_tag()
        days_param = self.env['ir.config_parameter'].sudo().get_param('lost_customer.inactivity_days', default=180)
        try:
            threshold_days = int(days_param)
        except (ValueError, TypeError):
            threshold_days = 180

        cutoff_date = fields.Datetime.now() - datetime.timedelta(days=threshold_days)

        for partner in self:
            # 1. Latest confirmed sale order
            confirmed_orders = partner.sale_order_ids.filtered(lambda s: s.state in ('sale', 'done'))
            last_order_dt = max(confirmed_orders.mapped('date_order')) if confirmed_orders else False

            # 2. Latest won CRM lead / opportunity
            won_opps = partner.opportunity_ids.filtered(lambda o: (o.stage_id and o.stage_id.is_won) or o.date_closed)
            last_opp_dt = max(won_opps.mapped('date_closed')) if won_opps else False

            # Compare dates
            dates = [d for d in [last_order_dt, last_opp_dt] if d]
            latest_dt = max(dates) if dates else False

            is_lost = False
            if latest_dt:
                if latest_dt < cutoff_date:
                    is_lost = True
            else:
                # No orders or won deals ever. If account was created > threshold days ago, mark as lost
                if partner.create_date and partner.create_date < cutoff_date:
                    is_lost = True

            partner.last_deal_or_order_date = latest_dt
            partner.is_lost_customer = is_lost

            # Attach or detach the 'Lost Customer' tag
            if is_lost:
                if tag.id not in partner.category_id.ids:
                    partner.category_id = [fields.Command.link(tag.id)]
            else:
                if tag.id in partner.category_id.ids:
                    partner.category_id = [fields.Command.unlink(tag.id)]

    @api.model
    def cron_update_lost_customers(self):
        """Daily automated job to scan all customers and refresh lost customer tags."""
        domain = ['|', ('customer_rank', '>', 0), ('is_sale', '=', True)] if 'is_sale' in self._fields else [('customer_rank', '>', 0)]
        customers = self.search(domain)
        customers.update_lost_customer_status()

    def action_check_lost_status(self):
        """Manual button to re-check lost customer status."""
        self.update_lost_customer_status()

    def action_reactivate_customer(self, order_name=None):
        """Called when a lost customer places a new confirmed order."""
        tag = self._get_lost_customer_tag()
        for partner in self:
            if partner.is_lost_customer:
                partner.is_lost_customer = False
                if tag.id in partner.category_id.ids:
                    partner.category_id = [fields.Command.unlink(tag.id)]
                msg = _("Customer reactivated! Placed confirmed order %s.") % (order_name or "")
                partner.message_post(body=msg)

