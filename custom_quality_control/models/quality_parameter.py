# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


def _format_num(val):
    if val is None or val is False:
        return ""
    try:
        fval = float(val)
        if fval == int(fval):
            return f"{int(fval):,}"
        return f"{fval:,.4f}".rstrip('0').rstrip('.')
    except (ValueError, TypeError):
        return str(val)


class QualityParameter(models.Model):
    _name = 'quality.parameter'
    _description = 'Master Quality Parameter'
    _order = 'name asc'

    name = fields.Char(string='Parameter Name', required=True, translate=True)
    code = fields.Char(string='Code', help='Short code or abbreviation (e.g. PH, VISC, DENS)')
    parameter_type = fields.Selection([
        ('numeric', 'Numeric / Quantitative'),
        ('text', 'Descriptive / Qualitative'),
        ('boolean', 'Pass / Fail (Conforming)'),
    ], string='Parameter Type', default='numeric', required=True)

    default_test_method = fields.Char(string='Standard Test Method', help='e.g. ASTM D1293, In-house Method, GC-MS')
    default_uom_name = fields.Char(string='Unit of Measure', help='e.g. pH, cP, %, g/cm³, ppm, °C')
    default_min_value = fields.Float(string='Default Min Value', digits=(16, 4))
    default_max_value = fields.Float(string='Default Max Value', digits=(16, 4))
    default_target_value = fields.Char(string='Default Target Value')
    default_expected_text = fields.Char(string='Default Expected Text')
    description = fields.Text(string='Description / Guidance')
    active = fields.Boolean(string='Active', default=True)


class QualityProductParameter(models.Model):
    _name = 'quality.product.parameter'
    _description = 'Product Quality Specification Parameter'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        required=True,
        ondelete='cascade',
        index=True
    )
    parameter_id = fields.Many2one('quality.parameter', string='Master Parameter')
    name = fields.Char(string='Parameter / Test Name', required=True)
    specification = fields.Char(
        string='Specification / Target',
        help='Target or expected specification for this product (e.g. 2,500 - 3,500 cP, Min 99.5%, Clear Liquid).'
    )
    parameter_type = fields.Selection([
        ('numeric', 'Numeric / Quantitative'),
        ('text', 'Descriptive / Qualitative'),
        ('boolean', 'Pass / Fail (Conforming)'),
    ], string='Type', default='numeric', required=True)

    test_method = fields.Char(string='Test Method')
    uom_name = fields.Char(string='Unit')
    min_value = fields.Float(string='Min Value', digits=(16, 4))
    max_value = fields.Float(string='Max Value', digits=(16, 4))
    target_value = fields.Char(string='Target / Spec')
    expected_text = fields.Char(string='Expected Text')
    is_mandatory = fields.Boolean(string='Mandatory', default=True)
    notes = fields.Char(string='Standard Remarks')

    @api.onchange('parameter_id')
    def _onchange_parameter_id(self):
        if self.parameter_id:
            self.name = self.parameter_id.name
            self.parameter_type = self.parameter_id.parameter_type
            self.test_method = self.parameter_id.default_test_method
            self.uom_name = self.parameter_id.default_uom_name
            self.min_value = self.parameter_id.default_min_value
            self.max_value = self.parameter_id.default_max_value
            self.target_value = self.parameter_id.default_target_value
            self.expected_text = self.parameter_id.default_expected_text

            p = self.parameter_id
            if p.default_min_value or p.default_max_value:
                uom_str = f" {p.default_uom_name}" if p.default_uom_name else ""
                self.specification = f"{_format_num(p.default_min_value)} - {_format_num(p.default_max_value)}{uom_str}"
            elif p.default_target_value:
                self.specification = p.default_target_value
            elif p.default_expected_text:
                self.specification = p.default_expected_text

