# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class QualityCheck(models.Model):
    _name = 'quality.check'
    _description = 'QA / QC Inspection & Analysis'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    title = fields.Char(
        string='Inspection Title',
        compute='_compute_title',
        store=True,
        readonly=False,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'Under Testing'),
        ('passed', 'Passed (Approved)'),
        ('failed', 'Failed (Rejected)'),
        ('quarantine', 'Quarantined'),
        ('returned', 'Returned to Vendor'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, required=True, index=True)

    qc_type = fields.Selection([
        ('purchase', 'Purchase (Incoming Goods)'),
        ('mrp', 'Manufacturing (Finished Goods)'),
        ('internal', 'Internal Stock Inspection'),
    ], string='Inspection Type', required=True, default='purchase', tracking=True, index=True)

    # Product Details
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        tracking=True,
        index=True
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        related='product_id.product_tmpl_id',
        store=True,
        readonly=True
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot / Batch / Serial No.',
        domain="[('product_id', '=', product_id)]",
        tracking=True
    )
    lot_name = fields.Char(string='Batch / Lot Name', tracking=True)
    quantity = fields.Float(
        string='Batch / Inspected Qty',
        digits='Product Unit of Measure',
        default=1.0,
        required=True,
        tracking=True
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        compute='_compute_product_uom',
        store=True,
        readonly=False
    )

    # Source References
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order', tracking=True, index=True)
    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchase Line')
    picking_id = fields.Many2one('stock.picking', string='Receipt / Stock Transfer', tracking=True, index=True)
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', tracking=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Vendor / Partner', tracking=True)

    # Completely Dynamic Locations & Warehouses
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    source_location_id = fields.Many2one(
        'stock.location',
        string='Current Location (QC)',
        domain="[('usage', 'in', ['internal', 'transit'])]",
        help='Location where the product is currently stored waiting for inspection. Can be any location in any warehouse.',
        tracking=True
    )
    @api.model
    def _default_dest_warehouse_id(self):
        return self.env['stock.warehouse'].get_main_warehouse(self.env.company.id)

    @api.model
    def _default_dest_location_id(self):
        wh = self._default_dest_warehouse_id()
        return wh.lot_stock_id if wh else False

    dest_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Target Warehouse',
        default=_default_dest_warehouse_id,
        help='Warehouse where the product will be stored after passing QC. Defaults to the main warehouse where all products store, but can be changed dynamically to any warehouse.',
        tracking=True
    )
    dest_location_id = fields.Many2one(
        'stock.location',
        string='Target Storage Location',
        default=_default_dest_location_id,
        domain="[('usage', 'in', ['internal', 'transit'])]",
        help='Location where product will be stored upon passing QC. Defaults to the main warehouse stock location where all products store, but can be changed dynamically to any location, rack, bin, or tank in any warehouse.',
        tracking=True
    )
    quarantine_location_id = fields.Many2one(
        'stock.location',
        string='Quarantine Location',
        domain="[('usage', 'in', ['internal', 'inventory', 'scrap'])]",
        help='Location for failed/rejected goods. Can be any location in any warehouse.'
    )

    # Stock Transfers Generated
    transfer_picking_id = fields.Many2one(
        'stock.picking',
        string='Inventory Release Transfer',
        readonly=True,
        copy=False,
        tracking=True
    )
    quarantine_picking_id = fields.Many2one(
        'stock.picking',
        string='Quarantine Transfer',
        readonly=True,
        copy=False
    )
    return_picking_id = fields.Many2one(
        'stock.picking',
        string='Return Transfer',
        readonly=True,
        copy=False,
        tracking=True
    )

    # Inspection & Approvals
    user_id = fields.Many2one(
        'res.users',
        string='QC Analyst / Chemist',
        default=lambda self: self.env.user,
        tracking=True
    )
    check_date = fields.Datetime(string='Inspection Date', default=fields.Datetime.now, tracking=True)
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, tracking=True)
    approved_date = fields.Datetime(string='Approval Date', readonly=True, tracking=True)

    # Dynamic Parameters
    check_line_ids = fields.One2many(
        'quality.check.line',
        'check_id',
        string='Dynamic Test Parameters & Analysis',
        copy=True
    )

    # Evaluation Summary
    overall_result = fields.Selection([
        ('pending', 'Pending Evaluation'),
        ('pass', 'Passed'),
        ('fail', 'Failed'),
    ], string='Overall Status', compute='_compute_overall_result', store=True, readonly=False, tracking=True)

    total_parameters = fields.Integer(string='Total Parameters', compute='_compute_overall_result')
    passed_parameters = fields.Integer(string='Parameters Passed', compute='_compute_overall_result')
    failed_parameters = fields.Integer(string='Parameters Failed', compute='_compute_overall_result')
    pending_parameters = fields.Integer(string='Pending Parameters', compute='_compute_overall_result')

    # Remarks
    notes = fields.Text(string='Lab Analysis Notes / Findings')
    rejection_reason = fields.Text(string='Reason for Rejection / Failure', tracking=True)

    @classmethod
    def _ensure_columns_exist(cls, env):
        if not getattr(cls, '_columns_auto_verified', False):
            try:
                env.cr.execute("""
                    ALTER TABLE quality_check ADD COLUMN IF NOT EXISTS return_picking_id integer;
                    ALTER TABLE quality_check ADD COLUMN IF NOT EXISTS transfer_picking_id integer;
                    ALTER TABLE quality_check ADD COLUMN IF NOT EXISTS quarantine_picking_id integer;
                    ALTER TABLE quality_check ADD COLUMN IF NOT EXISTS overall_result varchar;
                    ALTER TABLE quality_check ADD COLUMN IF NOT EXISTS notes text;
                    ALTER TABLE quality_check ADD COLUMN IF NOT EXISTS rejection_reason text;
                    ALTER TABLE quality_check_line ADD COLUMN IF NOT EXISTS specification varchar;
                    ALTER TABLE quality_check_line ADD COLUMN IF NOT EXISTS measured_value varchar;
                    ALTER TABLE quality_product_parameter ADD COLUMN IF NOT EXISTS specification varchar;
                    ALTER TABLE stock_picking ADD COLUMN IF NOT EXISTS qc_status varchar;
                    ALTER TABLE purchase_order ADD COLUMN IF NOT EXISTS qc_status varchar;
                """)
                cls._columns_auto_verified = True
            except Exception:
                pass

    def fetch(self, *args, **kwargs):
        self._ensure_columns_exist(self.env)
        return super().fetch(*args, **kwargs)

    def _search(self, *args, **kwargs):
        self._ensure_columns_exist(self.env)
        return super()._search(*args, **kwargs)

    def _check_access(self, *args, **kwargs):
        self._ensure_columns_exist(self.env)
        return super()._check_access(*args, **kwargs)

    @api.model
    def fields_get(self, *args, **kwargs):
        self._ensure_columns_exist(self.env)
        return super().fields_get(*args, **kwargs)

    def init(self):
        super().init()
        self._ensure_columns_exist(self.env)

    def _register_hook(self):
        super()._register_hook()
        self._ensure_columns_exist(self.env)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('quality.check') or _('New')
        records = super().create(vals_list)
        for record in records:
            if not record.check_line_ids and record.product_id:
                record._load_product_parameters()
        return records

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
            if not self.check_line_ids:
                lines = []
                tmpl = self.product_id.product_tmpl_id
                if tmpl and tmpl.qc_parameter_ids:
                    for p in tmpl.qc_parameter_ids:
                        spec = p.specification or p.target_value or p.expected_text or ''
                        if not spec and (p.min_value or p.max_value):
                            uom = f" {p.uom_name}" if p.uom_name else ""
                            spec = f"{p.min_value} - {p.max_value}{uom}"
                        lines.append((0, 0, {
                            'sequence': p.sequence,
                            'parameter_id': p.parameter_id.id if p.parameter_id else False,
                            'name': p.name,
                            'specification': spec,
                            'parameter_type': p.parameter_type or 'numeric',
                            'test_method': p.test_method or '',
                            'uom_name': p.uom_name or '',
                            'min_value': p.min_value,
                            'max_value': p.max_value,
                            'target_value': p.target_value or '',
                            'expected_text': p.expected_text or '',
                            'is_mandatory': p.is_mandatory,
                            'notes': p.notes or '',
                            'status': 'pending',
                        }))
                else:
                    default_params = self._get_dynamic_default_parameters()
                    for dp in default_params:
                        lines.append((0, 0, dict(dp)))
                self.check_line_ids = lines

    @api.depends('product_id', 'lot_id', 'lot_name', 'qc_type')
    def _compute_title(self):
        for check in self:
            lot_str = check.lot_id.name if check.lot_id else (check.lot_name or '')
            p_name = check.product_id.display_name or _('Product')
            type_str = dict(check._fields['qc_type'].selection).get(check.qc_type, '')
            if lot_str:
                check.title = f"{type_str}: {p_name} (Batch: {lot_str})"
            else:
                check.title = f"{type_str}: {p_name}"

    @api.depends('product_id')
    def _compute_product_uom(self):
        for check in self:
            if check.product_id and not check.product_uom_id:
                check.product_uom_id = check.product_id.uom_id

    @api.onchange('dest_warehouse_id')
    def _onchange_dest_warehouse_id(self):
        if self.dest_warehouse_id:
            self.dest_location_id = self.dest_warehouse_id.lot_stock_id

    @api.depends('check_line_ids.status')
    def _compute_overall_result(self):
        for check in self:
            lines = check.check_line_ids
            total = len(lines)
            passed = sum(1 for l in lines if l.status == 'pass')
            failed = sum(1 for l in lines if l.status == 'fail')
            pending = sum(1 for l in lines if l.status == 'pending')

            check.total_parameters = total
            check.passed_parameters = passed
            check.failed_parameters = failed
            check.pending_parameters = pending

            if not lines:
                check.overall_result = 'pending'
            elif failed > 0:
                check.overall_result = 'fail'
            elif passed == total:
                check.overall_result = 'pass'
            else:
                check.overall_result = 'pending'

    def _get_dynamic_default_parameters(self):
        """
        Determine smart, industry-standard dynamic parameters based on the chemical product type.
        Distinguishes between Resins/Polymers, Solvents/Esters, Pigments/Dyes, and General Chemicals.
        """
        self.ensure_one()
        p_name = (self.product_id.name or '').lower()
        p_cat = (self.product_id.categ_id.name or '').lower() if self.product_id.categ_id else ''
        p_full = f"{p_name} {p_cat}"

        Param = self.env['quality.parameter']
        param_cache = {p.code: p for p in Param.search([]) if p.code}

        def p_id(code):
            return param_cache.get(code, False).id if param_cache.get(code) else False

        # 1. Resins, Polymers, Emulsions, Coatings
        if any(k in p_full for k in ['resin', 'polymer', 'pk-100', 'emulsion', 'coating', 'monomer', 'binder', 'varnish']):
            return [
                {
                    'sequence': 10,
                    'parameter_id': p_id('APPR'),
                    'name': 'Physical Appearance',
                    'specification': 'Clear Amber Viscous Liquid',
                    'parameter_type': 'text',
                    'test_method': 'Visual Inspection @ 25°C',
                    'expected_text': 'Clear Amber Viscous Liquid, free from sediment',
                    'is_mandatory': True,
                    'status': 'pending',
                },
                {
                    'sequence': 20,
                    'parameter_id': p_id('VISC'),
                    'name': 'Viscosity',
                    'specification': '2,500 - 3,500 cP',
                    'parameter_type': 'numeric',
                    'uom_name': 'cP',
                    'test_method': 'ASTM D2196 (Brookfield Viscometer @ 25°C)',
                    'min_value': 2500.0,
                    'max_value': 3500.0,
                    'target_value': '3000 cP',
                    'is_mandatory': True,
                    'status': 'pending',
                },
                {
                    'sequence': 30,
                    'parameter_id': p_id('SOLIDS'),
                    'name': 'Solid Content / Non-Volatile (%)',
                    'specification': '98.0 - 100.0 %',
                    'parameter_type': 'numeric',
                    'uom_name': '%',
                    'test_method': 'Oven Drying Method @ 105°C',
                    'min_value': 98.0,
                    'max_value': 100.0,
                    'target_value': '99.0 %',
                    'is_mandatory': True,
                    'status': 'pending',
                },
                {
                    'sequence': 40,
                    'parameter_id': p_id('SG'),
                    'name': 'Specific Gravity',
                    'specification': '1.10 - 1.15 g/cm³',
                    'parameter_type': 'numeric',
                    'uom_name': 'g/cm³',
                    'test_method': 'ASTM D891 (Pycnometer @ 25°C)',
                    'min_value': 1.10,
                    'max_value': 1.15,
                    'target_value': '1.12 g/cm³',
                    'is_mandatory': True,
                    'status': 'pending',
                },
                {
                    'sequence': 50,
                    'parameter_id': p_id('COLOR'),
                    'name': 'Color (Gardner / Visual)',
                    'specification': 'Amber to Light Yellow',
                    'parameter_type': 'text',
                    'test_method': 'Visual / Gardner Scale',
                    'expected_text': 'Amber to Light Yellow (Gardner <= 4)',
                    'is_mandatory': False,
                    'status': 'pending',
                },
                {
                    'sequence': 60,
                    'parameter_id': p_id('PH'),
                    'name': 'pH Value',
                    'specification': '6.5 - 7.5 pH',
                    'parameter_type': 'numeric',
                    'uom_name': 'pH',
                    'test_method': 'ASTM D1293 (Digital pH Meter)',
                    'min_value': 6.5,
                    'max_value': 7.5,
                    'target_value': '7.0',
                    'is_mandatory': False,
                    'status': 'pending',
                },
                {
                    'sequence': 70,
                    'parameter_id': p_id('PKG'),
                    'name': 'Packaging & Label Integrity',
                    'specification': 'Conforms to UN Standards',
                    'parameter_type': 'boolean',
                    'test_method': 'Physical Container & UN Hazard Label Audit',
                    'is_mandatory': True,
                    'status': 'pending',
                },
            ]

        # 2. Solvents, Esters, Alcohols, Acetates
        elif any(k in p_full for k in ['solvent', 'acetate', 'ethyl', 'alcohol', 'ethanol', 'acetone', 'toluene', 'xylene', 'thinner', 'glycol']):
            return [
                {
                    'sequence': 10,
                    'parameter_id': p_id('APPR'),
                    'name': 'Physical Appearance',
                    'specification': 'Clear Colorless Volatile Liquid',
                    'parameter_type': 'text',
                    'test_method': 'Visual Inspection @ 25°C',
                    'expected_text': 'Clear Colorless Volatile Liquid, free from turbidity',
                    'is_mandatory': True,
                    'status': 'pending',
                },
                {
                    'sequence': 20,
                    'parameter_id': p_id('PURITY'),
                    'name': 'Purity / Assay (%)',
                    'specification': 'Min 99.5 % (Target 99.8%)',
                    'parameter_type': 'numeric',
                    'uom_name': '%',
                    'test_method': 'Gas Chromatography (GC)',
                    'min_value': 99.5,
                    'max_value': 100.0,
                    'target_value': '99.8 %',
                    'is_mandatory': True,
                    'status': 'pending',
                },
                {
                    'sequence': 30,
                    'parameter_id': p_id('MOIST'),
                    'name': 'Moisture Content (%)',
                    'specification': 'Max 0.05 % (Target 0.02%)',
                    'parameter_type': 'numeric',
                    'uom_name': '%',
                    'test_method': 'Karl Fischer Titration (ASTM D1364)',
                    'min_value': 0.00,
                    'max_value': 0.05,
                    'target_value': '0.02 %',
                    'is_mandatory': True,
                    'status': 'pending',
                },
                {
                    'sequence': 40,
                    'parameter_id': p_id('SG'),
                    'name': 'Specific Gravity',
                    'specification': '0.898 - 0.902 g/cm³',
                    'parameter_type': 'numeric',
                    'uom_name': 'g/cm³',
                    'test_method': 'ASTM D891 (Pycnometer @ 20°C)',
                    'min_value': 0.898,
                    'max_value': 0.902,
                    'target_value': '0.900 g/cm³',
                    'is_mandatory': True,
                    'status': 'pending',
                },
                {
                    'sequence': 50,
                    'parameter_id': p_id('ODOR'),
                    'name': 'Odor',
                    'specification': 'Characteristic pleasant fruity odor',
                    'parameter_type': 'text',
                    'test_method': 'Olfactory Sensory Evaluation',
                    'expected_text': 'Characteristic pleasant fruity ester odor',
                    'is_mandatory': False,
                    'status': 'pending',
                },
                {
                    'sequence': 60,
                    'parameter_id': p_id('COLOR'),
                    'name': 'Color (APHA)',
                    'specification': 'Colorless (Max 10 APHA)',
                    'parameter_type': 'text',
                    'test_method': 'ASTM D1209 (Platinum-Cobalt / APHA)',
                    'expected_text': 'Colorless (Max 10 APHA)',
                    'is_mandatory': False,
                    'status': 'pending',
                },
                {
                    'sequence': 70,
                    'parameter_id': p_id('PKG'),
                    'name': 'Packaging & Flammability Labeling',
                    'specification': 'Conforms (Airtight Sealed Drum)',
                    'parameter_type': 'boolean',
                    'test_method': 'Airtight Seal & Flammable Liquid Hazard Audit',
                    'is_mandatory': True,
                    'status': 'pending',
                },
            ]

        # 3. Pigments, Dyes, Inks, Powders
        elif any(k in p_full for k in ['pigment', 'dye', 'ink', 'paste', 'powder', 'black', 'white']):
            return [
                {
                    'sequence': 10,
                    'parameter_id': p_id('APPR'),
                    'name': 'Physical Appearance',
                    'specification': 'Uniform fine dispersion, no agglomerates',
                    'parameter_type': 'text',
                    'test_method': 'Visual & Hegman Gauge',
                    'expected_text': 'Uniform fine dispersion, no agglomerates',
                    'is_mandatory': True,
                    'status': 'pending',
                },
                {
                    'sequence': 20,
                    'parameter_id': p_id('SOLIDS'),
                    'name': 'Solid Content / Active Concentration (%)',
                    'specification': '95.0 - 100.0 %',
                    'parameter_type': 'numeric',
                    'uom_name': '%',
                    'test_method': 'Oven Drying Method @ 105°C',
                    'min_value': 95.0,
                    'max_value': 100.0,
                    'target_value': '98.0 %',
                    'is_mandatory': True,
                    'status': 'pending',
                },
                {
                    'sequence': 30,
                    'parameter_id': p_id('MOIST'),
                    'name': 'Moisture Content (%)',
                    'specification': 'Max 1.0 %',
                    'parameter_type': 'numeric',
                    'uom_name': '%',
                    'test_method': 'Moisture Analyzer',
                    'min_value': 0.0,
                    'max_value': 1.0,
                    'target_value': '0.3 %',
                    'is_mandatory': True,
                    'status': 'pending',
                },
                {
                    'sequence': 40,
                    'parameter_id': p_id('COLOR'),
                    'name': 'Color Shade & Undertone',
                    'specification': 'Conforms to master standard',
                    'parameter_type': 'text',
                    'test_method': 'Spectrophotometer (Delta E < 0.5)',
                    'expected_text': 'Conforms to master standard swatch',
                    'is_mandatory': True,
                    'status': 'pending',
                },
                {
                    'sequence': 50,
                    'parameter_id': p_id('PKG'),
                    'name': 'Packaging & Label Integrity',
                    'specification': 'Moisture-proof Seal & Markings',
                    'parameter_type': 'boolean',
                    'test_method': 'Moisture-proof Seal & Batch Markings',
                    'is_mandatory': True,
                    'status': 'pending',
                },
            ]

        # 4. General / Default Chemical Specification
        else:
            return [
                {
                    'sequence': 10,
                    'parameter_id': p_id('APPR'),
                    'name': 'Physical Appearance',
                    'specification': 'Clear homogeneous, free from contamination',
                    'parameter_type': 'text',
                    'test_method': 'Visual Inspection @ 25°C',
                    'expected_text': 'Clear homogeneous, free from contamination',
                    'is_mandatory': True,
                    'status': 'pending',
                },
                {
                    'sequence': 20,
                    'parameter_id': p_id('PURITY'),
                    'name': 'Purity / Assay (%)',
                    'specification': 'Min 95.0 % (Target 98.0%)',
                    'parameter_type': 'numeric',
                    'uom_name': '%',
                    'test_method': 'Standard Assay Method',
                    'min_value': 95.0,
                    'max_value': 100.0,
                    'target_value': '98.0 %',
                    'is_mandatory': True,
                    'status': 'pending',
                },
                {
                    'sequence': 30,
                    'parameter_id': p_id('SG'),
                    'name': 'Specific Gravity',
                    'specification': '0.95 - 1.25 g/cm³',
                    'parameter_type': 'numeric',
                    'uom_name': 'g/cm³',
                    'test_method': 'ASTM D891',
                    'min_value': 0.95,
                    'max_value': 1.25,
                    'target_value': '1.05 g/cm³',
                    'is_mandatory': False,
                    'status': 'pending',
                },
                {
                    'sequence': 40,
                    'parameter_id': p_id('PH'),
                    'name': 'pH Value',
                    'specification': '6.0 - 8.0 pH',
                    'parameter_type': 'numeric',
                    'uom_name': 'pH',
                    'test_method': 'Digital pH Meter',
                    'min_value': 6.0,
                    'max_value': 8.0,
                    'target_value': '7.0',
                    'is_mandatory': False,
                    'status': 'pending',
                },
                {
                    'sequence': 50,
                    'parameter_id': p_id('PKG'),
                    'name': 'Packaging & Label Integrity',
                    'specification': 'Conforms to packaging audit',
                    'parameter_type': 'boolean',
                    'test_method': 'Physical Container Audit',
                    'is_mandatory': True,
                    'status': 'pending',
                },
            ]

    def _load_product_parameters(self):
        """
        Copies parameters configured on the product template into dynamic check lines.
        If none are configured, automatically generates smart chemical parameters based
        on the product type, and saves them to the product template for future use.
        """
        self.ensure_one()
        tmpl = self.product_id.product_tmpl_id or self.product_tmpl_id
        if not tmpl:
            return

        lines_to_create = []
        if tmpl.qc_parameter_ids:
            for p in tmpl.qc_parameter_ids:
                spec_str = p.specification or p.target_value or p.expected_text or ''
                if not spec_str and (p.min_value or p.max_value):
                    uom = f" {p.uom_name}" if p.uom_name else ""
                    spec_str = f"{p.min_value} - {p.max_value}{uom}"
                lines_to_create.append({
                    'check_id': self.id,
                    'sequence': p.sequence,
                    'parameter_id': p.parameter_id.id if p.parameter_id else False,
                    'name': p.name,
                    'specification': spec_str,
                    'parameter_type': p.parameter_type,
                    'test_method': p.test_method,
                    'uom_name': p.uom_name,
                    'min_value': p.min_value,
                    'max_value': p.max_value,
                    'target_value': p.target_value,
                    'expected_text': p.expected_text,
                    'is_mandatory': p.is_mandatory,
                    'notes': p.notes,
                    'status': 'pending',
                })
        else:
            # Auto-generate dynamic parameters tailored to the chemical product
            default_params = self._get_dynamic_default_parameters()
            tmpl_params_to_save = []
            for dp in default_params:
                line_data = dict(dp)
                line_data['check_id'] = self.id
                lines_to_create.append(line_data)

                # Save onto product template as master specifications
                tmpl_params_to_save.append({
                    'product_tmpl_id': tmpl.id,
                    'sequence': dp.get('sequence', 10),
                    'parameter_id': dp.get('parameter_id', False),
                    'name': dp.get('name', ''),
                    'specification': dp.get('specification', ''),
                    'parameter_type': dp.get('parameter_type', 'numeric'),
                    'test_method': dp.get('test_method', ''),
                    'uom_name': dp.get('uom_name', ''),
                    'min_value': dp.get('min_value', 0.0),
                    'max_value': dp.get('max_value', 0.0),
                    'target_value': dp.get('target_value', ''),
                    'expected_text': dp.get('expected_text', ''),
                    'is_mandatory': dp.get('is_mandatory', True),
                })
            if tmpl_params_to_save:
                self.env['quality.product.parameter'].create(tmpl_params_to_save)

        if lines_to_create:
            self.env['quality.check.line'].create(lines_to_create)

    def action_load_product_parameters(self):
        """Action button to manually reload parameters from product template."""
        for check in self:
            if check.state in ('passed', 'failed', 'quarantine'):
                raise UserError(_("Cannot reload parameters on an already completed inspection."))
            check.check_line_ids.unlink()
            check._load_product_parameters()
            check.message_post(body=_("Dynamic parameters reloaded from product template specifications."))

    def action_save_parameters_to_product(self):
        """
        Saves the current inspection parameters to the product template so all
        future purchase and manufacturing inspections will automatically use them.
        """
        self.ensure_one()
        tmpl = self.product_id.product_tmpl_id or self.product_tmpl_id
        if not tmpl:
            raise UserError(_("No product template found for this inspection."))

        if not self.check_line_ids:
            raise UserError(_("No parameters available to save."))

        tmpl.qc_parameter_ids.unlink()
        params_to_create = []
        for line in self.check_line_ids:
            params_to_create.append({
                'product_tmpl_id': tmpl.id,
                'sequence': line.sequence,
                'parameter_id': line.parameter_id.id if line.parameter_id else False,
                'name': line.name,
                'specification': line.specification or line.target_value or '',
                'parameter_type': line.parameter_type or 'numeric',
                'test_method': line.test_method or '',
                'notes': line.notes or '',
                'min_value': line.min_value,
                'max_value': line.max_value,
                'target_value': line.target_value or '',
                'expected_text': line.expected_text or '',
            })

        self.env['quality.product.parameter'].create(params_to_create)
        tmpl.qc_required = True
        self.message_post(body=_(
            "Quality specifications updated and saved to Product Template <b>%s</b>."
        ) % tmpl.display_name)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Product Specifications Saved!'),
                'message': _('The %d parameters have been saved to %s for all future inspections.') % (len(params_to_create), tmpl.display_name),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_start(self):
        """Move from draft to in_progress (Under Testing)."""
        for check in self:
            if check.state == 'draft':
                check.write({'state': 'in_progress'})
                check.message_post(body=_("QA/QC Testing and parameter analysis started."))

    def action_open_release_wizard(self):
        """Opens a dynamic release wizard allowing the user to select any warehouse and storage location."""
        self.ensure_one()
        if self.failed_parameters > 0:
            raise UserError(_(
                "Cannot Pass: %d parameter(s) have failed the specification. "
                "Review parameters or reject the inspection."
            ) % self.failed_parameters)

        default_wh = (
            self.dest_warehouse_id
            or (self.dest_location_id.warehouse_id if self.dest_location_id else False)
            or (self.source_location_id.warehouse_id if self.source_location_id else False)
            or self.env['stock.warehouse'].get_main_warehouse(self.company_id.id)
        )
        default_loc = self.dest_location_id or (default_wh.lot_stock_id if default_wh else self.source_location_id)

        return {
            'name': _('Release to Dynamic Storage Location'),
            'type': 'ir.actions.act_window',
            'res_model': 'quality.release.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_check_id': self.id,
                'default_dest_warehouse_id': default_wh.id if default_wh else False,
                'default_dest_location_id': default_loc.id if default_loc else False,
            },
        }

    def action_pass(self):
        """
        Mark inspection as Passed and transfer the product to the chosen
        Target Storage Location in any warehouse.
        """
        for check in self:
            if check.state in ('passed', 'failed', 'quarantine'):
                raise UserError(_("This inspection is already finished."))

            if check.failed_parameters > 0:
                raise UserError(_(
                    "Cannot Pass: %d parameter(s) have failed the specification. "
                    "Review parameters or reject the inspection."
                ) % check.failed_parameters)

            # If dest_location_id is not set, open the dynamic release wizard
            if not check.dest_location_id:
                return check.action_open_release_wizard()

            check.write({
                'state': 'passed',
                'overall_result': 'pass',
                'approved_by_id': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })

            # Automatically move product to the dynamically chosen destination location
            transfer = check._action_transfer_to_inventory()

            dest_name = check.dest_location_id.display_name
            msg = _("<b>Quality Check PASSED</b> by %s.<br/>Product approved for release to: <b>%s</b>.") % (self.env.user.name, dest_name)
            if transfer:
                msg += _("<br/>Internal Transfer <a href='#' data-oe-model='stock.picking' data-oe-id='%s'>%s</a> created and validated.") % (transfer.id, transfer.name)
            elif check.source_location_id == check.dest_location_id:
                msg += _("<br/>Product approved in-place at current location.")
            check.message_post(body=msg)

            # Also notify source documents
            if check.purchase_id:
                check.purchase_id.message_post(body=_("Quality Check %s for %s PASSED. Released to: %s.") % (check.name, check.product_id.display_name, dest_name))
            if check.picking_id and check.picking_id != transfer:
                check.picking_id.message_post(body=_("Quality Check %s for %s PASSED. Released to: %s.") % (check.name, check.product_id.display_name, dest_name))
            if check.production_id:
                check.production_id.message_post(body=_("Quality Check %s for %s PASSED. Finished products released to: %s.") % (check.name, check.product_id.display_name, dest_name))

    def action_fail(self):
        """Mark inspection as Failed (Rejected). Does not add product to inventory."""
        for check in self:
            if check.state in ('passed', 'failed', 'quarantine'):
                raise UserError(_("This inspection is already finished."))

            check.write({
                'state': 'failed',
                'overall_result': 'fail',
                'approved_by_id': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })

            msg = _("<b>Quality Check FAILED / REJECTED</b> by %s.") % self.env.user.name
            if check.rejection_reason:
                msg += _("<br/><b>Reason:</b> %s") % check.rejection_reason
            msg += _("<br/>Products are held at current location (%s) and NOT added to inventory stock.") % (check.source_location_id.display_name if check.source_location_id else 'QC')
            check.message_post(body=msg)

            if check.purchase_id:
                check.purchase_id.message_post(body=_("Quality Check %s for %s FAILED. Material rejected.") % (check.name, check.product_id.display_name))
            if check.picking_id:
                check.picking_id.message_post(body=_("Quality Check %s for %s FAILED. Material rejected.") % (check.name, check.product_id.display_name))
            if check.production_id:
                check.production_id.message_post(body=_("Quality Check %s for %s FAILED. Manufactured batch rejected.") % (check.name, check.product_id.display_name))

    def action_send_to_quarantine(self):
        """Move rejected product to quarantine location in any warehouse."""
        self.ensure_one()
        transfer = self._action_transfer_to_quarantine()
        self.write({'state': 'quarantine'})
        msg = _("Product transferred to Quarantine location: %s") % (self.quarantine_location_id.display_name if self.quarantine_location_id else 'Quarantine')
        if transfer:
            msg += _("<br/>Quarantine Transfer: %s") % transfer.name
        self.message_post(body=msg)

    def action_reset_draft(self):
        for check in self:
            if check.transfer_picking_id and check.transfer_picking_id.state == 'done':
                raise UserError(_("Cannot reset to draft: products have already been transferred to inventory."))
            check.write({'state': 'draft'})

    def action_cancel(self):
        for check in self:
            if check.transfer_picking_id and check.transfer_picking_id.state == 'done':
                raise UserError(_("Cannot cancel: products have already been transferred to inventory."))
            check.write({'state': 'cancel'})

    def _action_transfer_to_inventory(self):
        """
        Creates and automatically validates an internal stock picking to transfer
        passed goods from source_location_id to dest_location_id across ANY warehouse.
        """
        self.ensure_one()
        if self.transfer_picking_id and self.transfer_picking_id.state == 'done':
            return self.transfer_picking_id

        source_loc = self.source_location_id
        dest_loc = self.dest_location_id

        if not source_loc or not dest_loc:
            raise UserError(_("Cannot perform inventory transfer: Source or Destination location missing."))

        if source_loc == dest_loc:
            # Already at destination location in-place
            return False

        # Determine warehouse for internal transfer picking type
        target_wh = (
            dest_loc.warehouse_id
            or self.dest_warehouse_id
            or source_loc.warehouse_id
            or self.env['stock.warehouse'].get_main_warehouse(self.company_id.id)
        )

        picking_type = target_wh.int_type_id or self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id', '=', target_wh.id)
        ], limit=1)
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)

        picking_vals = {
            'picking_type_id': picking_type.id,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'location_id': source_loc.id,
            'location_dest_id': dest_loc.id,
            'origin': f"QC Passed: {self.name} ({self.product_id.display_name})",
            'company_id': self.company_id.id,
            'move_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'description_picking': f"QC Passed: {self.name}",
                'product_uom': self.product_uom_id.id or self.product_id.uom_id.id,
                'product_uom_qty': self.quantity,
                'location_id': source_loc.id,
                'location_dest_id': dest_loc.id,
                'company_id': self.company_id.id,
            })],
        }

        picking = self.env['stock.picking'].create(picking_vals)
        picking.action_confirm()
        picking.action_assign()

        # Update move lines with quantity and lot
        for move in picking.move_ids:
            if hasattr(move, 'picked'):
                move.picked = True
            move.quantity = self.quantity
            if self.lot_id:
                if move.move_line_ids:
                    for sml in move.move_line_ids:
                        sml.quantity = self.quantity
                        sml.lot_id = self.lot_id.id
                else:
                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'picking_id': picking.id,
                        'product_id': self.product_id.id,
                        'product_uom_id': self.product_uom_id.id or self.product_id.uom_id.id,
                        'quantity': self.quantity,
                        'location_id': source_loc.id,
                        'location_dest_id': dest_loc.id,
                        'lot_id': self.lot_id.id,
                        'company_id': self.company_id.id,
                    })
            else:
                if move.move_line_ids:
                    for sml in move.move_line_ids:
                        sml.quantity = self.quantity
                else:
                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'picking_id': picking.id,
                        'product_id': self.product_id.id,
                        'product_uom_id': self.product_uom_id.id or self.product_id.uom_id.id,
                        'quantity': self.quantity,
                        'location_id': source_loc.id,
                        'location_dest_id': dest_loc.id,
                        'company_id': self.company_id.id,
                    })

        try:
            picking.button_validate()
        except Exception as e:
            picking.message_post(body=_("Validation note: %s") % str(e))

        self.transfer_picking_id = picking.id
        return picking

    def _action_transfer_to_quarantine(self):
        """Move product to quarantine location in any warehouse."""
        self.ensure_one()
        if self.quarantine_picking_id and self.quarantine_picking_id.state == 'done':
            return self.quarantine_picking_id

        source_loc = self.source_location_id
        target_wh = (
            source_loc.warehouse_id
            or (self.dest_location_id.warehouse_id if self.dest_location_id else False)
            or self.env['stock.warehouse'].get_main_warehouse(self.company_id.id)
        )
        quar_loc = self.quarantine_location_id or target_wh._get_or_create_quarantine_location()
        self.quarantine_location_id = quar_loc

        picking_type = target_wh.int_type_id or self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id', '=', target_wh.id)
        ], limit=1)
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)

        picking_vals = {
            'picking_type_id': picking_type.id,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'location_id': source_loc.id,
            'location_dest_id': quar_loc.id,
            'origin': f"QC Failed / Quarantined: {self.name}",
            'company_id': self.company_id.id,
            'move_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'description_picking': f"QC Rejected: {self.name}",
                'product_uom': self.product_uom_id.id or self.product_id.uom_id.id,
                'product_uom_qty': self.quantity,
                'location_id': source_loc.id,
                'location_dest_id': quar_loc.id,
                'company_id': self.company_id.id,
            })],
        }

        picking = self.env['stock.picking'].create(picking_vals)
        picking.action_confirm()
        picking.action_assign()

        for move in picking.move_ids:
            if hasattr(move, 'picked'):
                move.picked = True
            move.quantity = self.quantity
            if self.lot_id:
                if move.move_line_ids:
                    for sml in move.move_line_ids:
                        sml.quantity = self.quantity
                        sml.lot_id = self.lot_id.id
                else:
                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'picking_id': picking.id,
                        'product_id': self.product_id.id,
                        'product_uom_id': self.product_uom_id.id or self.product_id.uom_id.id,
                        'quantity': self.quantity,
                        'location_id': source_loc.id,
                        'location_dest_id': quar_loc.id,
                        'lot_id': self.lot_id.id,
                        'company_id': self.company_id.id,
                    })
            else:
                if move.move_line_ids:
                    for sml in move.move_line_ids:
                        sml.quantity = self.quantity

        try:
            picking.button_validate()
        except Exception:
            pass

        self.quarantine_picking_id = picking.id
        return picking

    def action_view_transfer(self):
        self.ensure_one()
        return {
            'name': _('Inventory Transfer'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.transfer_picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_quarantine_transfer(self):
        self.ensure_one()
        return {
            'name': _('Quarantine Transfer'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.quarantine_picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_return_transfer(self):
        self.ensure_one()
        if not self.return_picking_id:
            raise UserError(_("No return transfer has been created yet."))
        return {
            'name': _('Vendor Return Transfer'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.return_picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_return_to_vendor(self):
        """
        Creates an immediate Return Transfer picking to return the defective / failed
        products from QC location back to the Vendor (or production/source).
        """
        self.ensure_one()
        if self.transfer_picking_id and self.transfer_picking_id.state == 'done':
            raise UserError(_("Cannot return: products have already been approved and released to inventory stock."))

        if self.state not in ('failed', 'in_progress', 'quarantine'):
            raise UserError(_("Only failed or under-testing inspections can be returned."))

        if not self.rejection_reason and self.failed_parameters > 0:
            self.rejection_reason = _("Failed %d quality parameter(s)") % self.failed_parameters

        return_picking = self._action_create_return_transfer()
        self.write({
            'state': 'returned',
            'overall_result': 'fail',
            'approved_by_id': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })

        partner_name = self.partner_id.name if self.partner_id else _("Vendor")
        msg = _(
            "<b>Product REJECTED &amp; Returned to Vendor (%s)</b> by %s.<br/>"
            "Return Transfer <a href='#' data-oe-model='stock.picking' data-oe-id='%s'>%s</a> created."
        ) % (partner_name, self.env.user.name, return_picking.id, return_picking.name)
        if self.rejection_reason:
            msg += _("<br/><b>Reason:</b> %s") % self.rejection_reason
        self.message_post(body=msg)

        if self.purchase_id:
            self.purchase_id.message_post(body=_(
                "Quality Check %s FAILED. Return Transfer <a href='#' data-oe-model='stock.picking' data-oe-id='%s'>%s</a> created to return defective goods to %s."
            ) % (self.name, return_picking.id, return_picking.name, partner_name))
        if self.picking_id:
            self.picking_id.message_post(body=_(
                "Quality Check %s FAILED. Return Transfer <a href='#' data-oe-model='stock.picking' data-oe-id='%s'>%s</a> created."
            ) % (self.name, return_picking.id, return_picking.name))

        return {
            'name': _('Vendor Return Transfer'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': return_picking.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _action_create_return_transfer(self):
        """
        Creates a Return Transfer picking for the rejected product:
        - For Purchase receipts: returns goods from QC location back to the Vendor Location.
        - For Manufacturing: returns back to production/virtual production or scrap location.
        - For Internal: returns back to original source location.
        """
        self.ensure_one()
        if self.return_picking_id:
            return self.return_picking_id

        source_loc = self.source_location_id
        if not source_loc:
            raise UserError(_("Cannot process return: Current QC storage location is not specified."))

        # 1. Determine destination return location
        partner = self.partner_id or (self.purchase_id.partner_id if self.purchase_id else False)
        vendor_loc = False
        if partner and partner.property_stock_supplier:
            vendor_loc = partner.property_stock_supplier
        if not vendor_loc and self.picking_id and self.picking_id.location_id:
            vendor_loc = self.picking_id.location_id
        if not vendor_loc:
            vendor_loc = self.env['stock.location'].search([
                ('usage', '=', 'supplier'),
                ('company_id', 'in', [self.company_id.id, False]),
            ], limit=1)
        if not vendor_loc:
            vendor_loc = self.env.ref('stock.stock_location_suppliers', raise_if_not_found=False)

        # For manufacturing, destination is production location
        if self.qc_type == 'mrp':
            if self.production_id and self.production_id.location_src_id:
                dest_return_loc = self.production_id.location_src_id
            else:
                dest_return_loc = self.env['stock.location'].search([
                    ('usage', '=', 'production'),
                    ('company_id', 'in', [self.company_id.id, False]),
                ], limit=1) or source_loc
        else:
            dest_return_loc = vendor_loc or source_loc

        # 2. Determine picking type for return
        warehouse = (
            source_loc.warehouse_id
            or (self.dest_location_id.warehouse_id if self.dest_location_id else False)
            or self.env['stock.warehouse'].get_main_warehouse(self.company_id.id)
        )

        return_picking_type = False
        if self.picking_id and self.picking_id.picking_type_id.return_picking_type_id:
            return_picking_type = self.picking_id.picking_type_id.return_picking_type_id
        elif warehouse and warehouse.out_type_id:
            return_picking_type = warehouse.out_type_id
        else:
            return_picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'outgoing'),
                ('warehouse_id', '=', warehouse.id if warehouse else False),
            ], limit=1)
        if not return_picking_type:
            return_picking_type = self.env['stock.picking.type'].search([('code', 'in', ('outgoing', 'internal'))], limit=1)

        origin_str = f"QC Rejected Return: {self.name} ({self.product_id.display_name})"
        if self.purchase_id:
            origin_str += f" - {self.purchase_id.name}"
        elif self.picking_id:
            origin_str += f" - {self.picking_id.name}"

        picking_vals = {
            'picking_type_id': return_picking_type.id if return_picking_type else False,
            'partner_id': partner.id if partner else False,
            'location_id': source_loc.id,
            'location_dest_id': dest_return_loc.id if dest_return_loc else source_loc.id,
            'origin': origin_str,
            'company_id': self.company_id.id,
            'move_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'description_picking': f"QC Rejected Return: {self.name}",
                'product_uom': self.product_uom_id.id or self.product_id.uom_id.id,
                'product_uom_qty': self.quantity,
                'location_id': source_loc.id,
                'location_dest_id': dest_return_loc.id if dest_return_loc else source_loc.id,
                'company_id': self.company_id.id,
            })],
        }

        return_picking = self.env['stock.picking'].create(picking_vals)
        try:
            return_picking.action_confirm()
            return_picking.action_assign()
        except Exception:
            pass

        # Update move lines with quantity and lot
        for move in return_picking.move_ids:
            if hasattr(move, 'picked'):
                move.picked = True
            move.quantity = self.quantity
            if self.lot_id:
                if move.move_line_ids:
                    for sml in move.move_line_ids:
                        sml.quantity = self.quantity
                        sml.lot_id = self.lot_id.id
                else:
                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'picking_id': return_picking.id,
                        'product_id': self.product_id.id,
                        'product_uom_id': self.product_uom_id.id or self.product_id.uom_id.id,
                        'quantity': self.quantity,
                        'location_id': source_loc.id,
                        'location_dest_id': dest_return_loc.id,
                        'lot_id': self.lot_id.id,
                        'company_id': self.company_id.id,
                    })
            else:
                if move.move_line_ids:
                    for sml in move.move_line_ids:
                        sml.quantity = self.quantity
                else:
                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'picking_id': return_picking.id,
                        'product_id': self.product_id.id,
                        'product_uom_id': self.product_uom_id.id or self.product_id.uom_id.id,
                        'quantity': self.quantity,
                        'location_id': source_loc.id,
                        'location_dest_id': dest_return_loc.id,
                        'company_id': self.company_id.id,
                    })

        self.return_picking_id = return_picking.id
        return return_picking

    def action_print_coa(self):
        """Print Certificate of Analysis report."""
        self.ensure_one()
        return self.env.ref('custom_quality_control.action_report_quality_check').report_action(self)
