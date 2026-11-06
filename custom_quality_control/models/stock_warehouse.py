# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    qc_location_id = fields.Many2one(
        'stock.location',
        string='Quality Control Location',
        domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]",
        help='Internal location where purchased or manufactured products await quality inspection before entering stock. Dynamically created per warehouse.'
    )
    quarantine_location_id = fields.Many2one(
        'stock.location',
        string='Quarantine / Rejected Location',
        domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]",
        help='Internal location where failed or rejected products are segregated. Dynamically created per warehouse.'
    )

    @api.model
    def get_main_warehouse(self, company_id=None):
        """
        Dynamically returns the main warehouse for the company where all products are stored by default.
        Does not fix or hardcode any warehouse name.
        """
        cid = company_id or self.env.company.id
        return self.search([('company_id', '=', cid)], order='id asc', limit=1)

    def _get_or_create_qc_location(self):
        """
        Find or create a Quality Control location dynamically for this specific warehouse.
        Does not assume or fix any warehouse name.
        """
        self.ensure_one()
        if self.qc_location_id:
            return self.qc_location_id

        parent_loc = self.view_location_id or (self.lot_stock_id.location_id if self.lot_stock_id else False)
        if not parent_loc:
            parent_loc = self.lot_stock_id

        qc_loc = self.env['stock.location'].search([
            ('company_id', '=', self.company_id.id),
            ('is_qc_location', '=', True),
            ('location_id', '=', parent_loc.id if parent_loc else False),
        ], limit=1)
        if not qc_loc and parent_loc:
            qc_loc = self.env['stock.location'].search([
                ('company_id', '=', self.company_id.id),
                ('name', '=', 'Quality Control'),
                ('location_id', '=', parent_loc.id),
            ], limit=1)
        if not qc_loc:
            qc_loc = self.env['stock.location'].create({
                'name': 'Quality Control',
                'usage': 'internal',
                'location_id': parent_loc.id if parent_loc else False,
                'company_id': self.company_id.id,
                'is_qc_location': True,
            })
        else:
            if not qc_loc.is_qc_location:
                qc_loc.write({'is_qc_location': True})

        self.write({'qc_location_id': qc_loc.id})
        return qc_loc

    def _get_or_create_quarantine_location(self):
        """
        Find or create a Quarantine location dynamically for this specific warehouse.
        Does not assume or fix any warehouse name.
        """
        self.ensure_one()
        if self.quarantine_location_id:
            return self.quarantine_location_id

        parent_loc = self.view_location_id or (self.lot_stock_id.location_id if self.lot_stock_id else False)
        if not parent_loc:
            parent_loc = self.lot_stock_id

        quar_loc = self.env['stock.location'].search([
            ('company_id', '=', self.company_id.id),
            ('is_quarantine_location', '=', True),
            ('location_id', '=', parent_loc.id if parent_loc else False),
        ], limit=1)
        if not quar_loc and parent_loc:
            quar_loc = self.env['stock.location'].search([
                ('company_id', '=', self.company_id.id),
                ('name', '=', 'Quarantine'),
                ('location_id', '=', parent_loc.id),
            ], limit=1)
        if not quar_loc:
            quar_loc = self.env['stock.location'].create({
                'name': 'Quarantine',
                'usage': 'internal',
                'location_id': parent_loc.id if parent_loc else False,
                'company_id': self.company_id.id,
                'is_quarantine_location': True,
            })
        else:
            if not quar_loc.is_quarantine_location:
                quar_loc.write({'is_quarantine_location': True})

        self.write({'quarantine_location_id': quar_loc.id})
        return quar_loc
