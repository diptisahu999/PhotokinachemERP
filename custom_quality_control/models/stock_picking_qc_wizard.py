# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class StockPickingQcWizard(models.TransientModel):
    _name = 'stock.picking.qc.wizard'
    _description = 'QA/QC Order Routing Notification Wizard'

    picking_id = fields.Many2one('stock.picking', string='Receipt', readonly=True)
    picking_name = fields.Char(related='picking_id.name', string='Receipt Number', readonly=True)
    location_name = fields.Char(string='QC Location', readonly=True)
    qc_check_ids = fields.Many2many('quality.check', string='Generated Quality Checks', readonly=True)
    qc_count = fields.Integer(string='Checks Count', compute='_compute_qc_count')

    @api.depends('qc_check_ids')
    def _compute_qc_count(self):
        for wiz in self:
            wiz.qc_count = len(wiz.qc_check_ids)

    def action_open_qc_checks(self):
        """Open the generated QA/QC inspection records."""
        self.ensure_one()
        if len(self.qc_check_ids) == 1:
            return {
                'name': _('QA/QC Inspection - %s') % self.qc_check_ids[0].name,
                'type': 'ir.actions.act_window',
                'res_model': 'quality.check',
                'res_id': self.qc_check_ids[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'name': _('QA/QC Inspections for %s') % self.picking_name,
            'type': 'ir.actions.act_window',
            'res_model': 'quality.check',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.qc_check_ids.ids)],
            'target': 'current',
        }

