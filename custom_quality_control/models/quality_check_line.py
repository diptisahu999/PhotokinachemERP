# -*- coding: utf-8 -*-
import re
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


class QualityCheckLine(models.Model):
    _name = 'quality.check.line'
    _description = 'Quality Check Parameter Line'
    _order = 'sequence, id'

    check_id = fields.Many2one(
        'quality.check',
        string='Quality Check',
        required=True,
        ondelete='cascade',
        index=True
    )
    sequence = fields.Integer(string='Sequence', default=10)

    # 1. Parameter / Test Name
    name = fields.Char(string='Parameter', required=True)

    # 2. Standard Specification (Target)
    specification = fields.Char(
        string='Standard Specification',
        compute='_compute_specification',
        store=True,
        readonly=False,
        help='Target or expected specification for this product (e.g. 2,500 - 3,500 cP, Min 99.5%, Clear Liquid).'
    )

    # 3. Measured / Observed Value
    measured_value = fields.Char(
        string='Actual / Measured Value',
        compute='_compute_measured_value',
        store=True,
        readonly=False,
        help='Value measured or observed in laboratory testing.'
    )

    # 4. Result (Pass / Fail / Pending)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Result', default='pending', required=True)

    # 5. Remarks
    notes = fields.Char(string='Remarks')

    # Master link & Technical Specification Fields (used under the hood for auto-calculation)
    parameter_id = fields.Many2one(
        'quality.parameter',
        string='Master Parameter',
        help='Optional link to master parameter'
    )
    parameter_type = fields.Selection([
        ('numeric', 'Numeric'),
        ('text', 'Descriptive'),
        ('boolean', 'Pass / Fail'),
    ], string='Type', default='numeric')

    test_method = fields.Char(string='Test Method / Standard')
    uom_name = fields.Char(string='Unit')
    min_value = fields.Float(string='Min Value', digits=(16, 4))
    max_value = fields.Float(string='Max Value', digits=(16, 4))
    target_value = fields.Char(string='Target / Spec')
    expected_text = fields.Char(string='Expected Result')
    is_mandatory = fields.Boolean(string='Mandatory', default=True)

    # Backward compatibility fields
    measured_numeric = fields.Float(string='Measured Value (Num)', digits=(16, 4))
    measured_text = fields.Char(string='Observed Value (Text)')
    measured_boolean = fields.Boolean(string='Conforms?')
    tested_by_id = fields.Many2one('res.users', string='Tested By', default=lambda self: self.env.user)
    test_date = fields.Datetime(string='Test Date', default=fields.Datetime.now)

    @api.depends('parameter_id', 'min_value', 'max_value', 'target_value', 'expected_text', 'uom_name', 'parameter_type')
    def _compute_specification(self):
        for line in self:
            if line.specification:
                continue
            spec = ""
            if line.parameter_type == 'numeric':
                uom = f" {line.uom_name}" if line.uom_name else ""
                if line.min_value and line.max_value:
                    spec = f"{_format_num(line.min_value)} - {_format_num(line.max_value)}{uom}"
                elif line.min_value:
                    spec = f"Min {_format_num(line.min_value)}{uom}"
                elif line.max_value:
                    spec = f"Max {_format_num(line.max_value)}{uom}"
                elif line.target_value:
                    spec = line.target_value
            elif line.parameter_type == 'text' and line.expected_text:
                spec = line.expected_text
            elif line.parameter_type == 'boolean':
                spec = _("Conforms to standard")
            line.specification = spec or False

    @api.depends('measured_numeric', 'measured_text', 'measured_boolean', 'parameter_type')
    def _compute_measured_value(self):
        for line in self:
            if line.measured_value:
                continue
            val = ""
            if line.parameter_type == 'numeric' and line.measured_numeric:
                uom = f" {line.uom_name}" if line.uom_name else ""
                val = f"{_format_num(line.measured_numeric)}{uom}"
            elif line.parameter_type == 'text' and line.measured_text:
                val = line.measured_text
            elif line.parameter_type == 'boolean' and line.measured_boolean:
                val = _("Conforms")
            line.measured_value = val or False

    @api.onchange('parameter_id')
    def _onchange_parameter_id(self):
        if self.parameter_id:
            p = self.parameter_id
            self.name = p.name
            self.parameter_type = p.parameter_type
            self.test_method = p.default_test_method
            self.uom_name = p.default_uom_name
            self.min_value = p.default_min_value
            self.max_value = p.default_max_value
            self.target_value = p.default_target_value
            self.expected_text = p.default_expected_text

            if p.default_min_value or p.default_max_value:
                uom_str = f" {p.default_uom_name}" if p.default_uom_name else ""
                self.specification = f"{_format_num(p.default_min_value)} - {_format_num(p.default_max_value)}{uom_str}"
            elif p.default_target_value:
                self.specification = p.default_target_value
            elif p.default_expected_text:
                self.specification = p.default_expected_text

    @api.onchange('measured_value')
    def _onchange_measured_value(self):
        """
        Auto-evaluates Pass or Fail when a test value is entered,
        while still allowing the inspector to manually toggle Pass/Fail.
        """
        if not self.measured_value:
            self.status = 'pending'
            return

        val_str = self.measured_value.strip().lower()

        # Check for direct pass/fail words
        if val_str in ('pass', 'passed', 'ok', 'yes', 'true', 'conforms', 'conforming'):
            self.status = 'pass'
            return
        elif val_str in ('fail', 'failed', 'not ok', 'no', 'false', 'rejected', 'non-conforming'):
            self.status = 'fail'
            return

        # Check numeric limits if min/max are defined
        nums = re.findall(r"[-+]?\d*\.?\d+", val_str.replace(',', ''))
        if nums and (self.min_value or self.max_value):
            try:
                num = float(nums[0])
                self.measured_numeric = num
                failed = False
                if self.min_value and num < self.min_value:
                    failed = True
                if self.max_value and num > self.max_value:
                    failed = True
                self.status = 'fail' if failed else 'pass'
                return
            except ValueError:
                pass

        # Check numeric limits from specification string if available
        if nums and self.specification and not (self.min_value or self.max_value):
            spec_nums = re.findall(r"[-+]?\d*\.?\d+", self.specification.replace(',', ''))
            if len(spec_nums) >= 2 and '-' in self.specification:
                try:
                    num = float(nums[0])
                    s_min = float(spec_nums[0])
                    s_max = float(spec_nums[1])
                    self.status = 'pass' if (s_min <= num <= s_max) else 'fail'
                    return
                except ValueError:
                    pass
            elif len(spec_nums) >= 1 and 'min' in self.specification.lower():
                try:
                    num = float(nums[0])
                    s_min = float(spec_nums[0])
                    self.status = 'pass' if num >= s_min else 'fail'
                    return
                except ValueError:
                    pass
            elif len(spec_nums) >= 1 and 'max' in self.specification.lower():
                try:
                    num = float(nums[0])
                    s_max = float(spec_nums[0])
                    self.status = 'pass' if num <= s_max else 'fail'
                    return
                except ValueError:
                    pass

        # Check expected text matching
        if self.expected_text:
            exp_clean = self.expected_text.strip().lower()
            if exp_clean in val_str or val_str in exp_clean:
                self.status = 'pass'
                return

        # Default to pass when a value is provided and no rule failed
        if not self.status or self.status == 'pending':
            self.status = 'pass'
