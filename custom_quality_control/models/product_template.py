# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    qc_required = fields.Boolean(
        string='Quality Check Required',
        default=True,
        help='When enabled, all incoming purchase receipts and finished manufacturing batches of this product must undergo QA/QC inspection before entering available inventory.'
    )
    qc_parameter_ids = fields.One2many(
        'quality.product.parameter',
        'product_tmpl_id',
        string='Default Quality Parameters & Specifications',
        copy=True
    )
    qc_check_count = fields.Integer(
        string='Quality Inspections Count',
        compute='_compute_qc_check_count'
    )

    def init(self):
        super().init()
        # Ensure all existing products in database have qc_required = True
        self.env.cr.execute("""
            UPDATE product_template
            SET qc_required = TRUE
            WHERE qc_required IS NULL;
        """)

    def _compute_qc_check_count(self):
        for tmpl in self:
            tmpl.qc_check_count = self.env['quality.check'].search_count([
                ('product_tmpl_id', '=', tmpl.id)
            ])

    def action_view_qc_checks(self):
        self.ensure_one()
        return {
            'name': _('Quality Checks - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'quality.check',
            'view_mode': 'list,form',
            'domain': [('product_tmpl_id', '=', self.id)],
            'context': {
                'default_product_id': self.product_variant_id.id if self.product_variant_id else False,
            },
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    qc_required = fields.Boolean(
        related='product_tmpl_id.qc_required',
        string='Quality Check Required',
        readonly=False,
        store=True,
    )
