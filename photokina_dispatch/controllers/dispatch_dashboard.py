# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta
from odoo import http
from odoo.http import request


class DispatchDashboard(http.Controller):

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _period_domain(self, period):
        """Return extra domain filters based on selected period."""
        today = date.today()
        if period == 'today':
            start = today.strftime('%Y-%m-%d 00:00:00')
            return ['|', ('date_done', '>=', start), '&', ('date_done', '=', False), ('scheduled_date', '>=', start)]
        elif period == 'week':
            start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d 00:00:00')
            return ['|', ('date_done', '>=', start), '&', ('date_done', '=', False), ('scheduled_date', '>=', start)]
        elif period == 'month':
            start = today.replace(day=1).strftime('%Y-%m-%d 00:00:00')
            return ['|', ('date_done', '>=', start), '&', ('date_done', '=', False), ('scheduled_date', '>=', start)]
        elif period == 'year':
            start = today.replace(month=1, day=1).strftime('%Y-%m-%d 00:00:00')
            return ['|', ('date_done', '>=', start), '&', ('date_done', '=', False), ('scheduled_date', '>=', start)]
        return []  # 'all'

    def _base_domain(self):
        # Include all outgoing deliveries (completed and pending, exclude draft & cancel)
        return [
            ('picking_type_code', '=', 'outgoing'),
            ('state', 'not in', ('draft', 'cancel')),
        ]

    # ------------------------------------------------------------------ #
    #  KPI endpoint
    # ------------------------------------------------------------------ #

    @http.route('/photokina_dispatch/kpi_data', type='json', auth='user', methods=['POST'])
    def kpi_data(self, period='all', **kwargs):
        domain = self._base_domain() + self._period_domain(period)
        pickings = request.env['stock.picking'].sudo().search(domain)
        total = len(pickings)
        late = 0
        now = datetime.now()

        for p in pickings:
            if p.state == 'done':
                if p.date_done and p.scheduled_date and p.date_done > p.scheduled_date:
                    late += 1
            else:
                # Pending: check if already overdue compared to scheduled_date
                if p.scheduled_date and now > p.scheduled_date:
                    late += 1

        on_time = total - late
        on_time_pct = round(on_time / total * 100, 1) if total else 0.0
        late_pct = round(late / total * 100, 1) if total else 0.0

        return {
            'total': total,
            'on_time': on_time,
            'late': late,
            'on_time_pct': on_time_pct,
            'late_pct': late_pct,
        }

    # ------------------------------------------------------------------ #
    #  Delay-bucket chart endpoint
    # ------------------------------------------------------------------ #

    @http.route('/photokina_dispatch/delay_buckets', type='json', auth='user', methods=['POST'])
    def delay_buckets(self, period='all', **kwargs):
        domain = self._base_domain() + self._period_domain(period)
        pickings = request.env['stock.picking'].sudo().search(domain)
        buckets = {
            '0 Days': 0,
            '1-3 Days': 0,
            '4-7 Days': 0,
            '8-14 Days': 0,
            '15+ Days': 0,
        }
        now = datetime.now()

        for p in pickings:
            delay = 0
            if p.state == 'done':
                if p.scheduled_date and p.date_done:
                    delay = max(0, (p.date_done - p.scheduled_date).days)
            else:
                if p.scheduled_date and now > p.scheduled_date:
                    delay = max(0, (now - p.scheduled_date).days)

            if delay == 0:
                buckets['0 Days'] += 1
            elif delay <= 3:
                buckets['1-3 Days'] += 1
            elif delay <= 7:
                buckets['4-7 Days'] += 1
            elif delay <= 14:
                buckets['8-14 Days'] += 1
            else:
                buckets['15+ Days'] += 1

        return [{'label': k, 'count': v} for k, v in buckets.items()]

    # ------------------------------------------------------------------ #
    #  Delivery-table endpoint
    # ------------------------------------------------------------------ #

    @http.route('/photokina_dispatch/delivery_table', type='json', auth='user', methods=['POST'])
    def delivery_table(self, period='all', search='', **kwargs):
        domain = self._base_domain() + self._period_domain(period)
        if search:
            domain += [
                '|', '|', '|',
                ('name', 'ilike', search),
                ('partner_id.name', 'ilike', search),
                ('origin', 'ilike', search),
                ('sale_id.name', 'ilike', search),
            ]
        pickings = request.env['stock.picking'].sudo().search(
            domain, order='date_done desc, scheduled_date desc', limit=1000
        )
        rows = []
        now = datetime.now()

        for p in pickings:
            scheduled = p.scheduled_date
            done = p.date_done
            days_delay = 0
            is_late = False

            if p.state == 'done':
                actual_date_str = done.strftime('%d/%m/%Y') if done else '-'
                if scheduled and done:
                    diff = (done - scheduled).days
                    days_delay = max(0, diff)
                    is_late = diff > 0
            else:
                # Pending order status
                status_label = dict(p._fields['state'].selection).get(p.state, p.state.title())
                actual_date_str = f"Pending ({status_label})"
                if scheduled and now > scheduled:
                    diff = (now - scheduled).days
                    days_delay = max(0, diff)
                    is_late = diff > 0

            # Order reference
            order_no = ''
            if p.sale_id:
                order_no = p.sale_id.name
            elif p.origin:
                order_no = p.origin
            else:
                order_no = p.name

            rows.append({
                'order_no': order_no,
                'picking_name': p.name,
                'company': p.partner_id.name or '-',
                'proposed_date': scheduled.strftime('%d/%m/%Y') if scheduled else '-',
                'actual_date': actual_date_str,
                'days_delay': days_delay,
                'is_late': is_late,
                'state': p.state,
            })

        return rows
