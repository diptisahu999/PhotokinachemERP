# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """
    Setup Quality Control and Quarantine locations for all existing warehouses,
    ensure products have qc_required enabled by default, and seed chemical
    test specifications for chemical products.
    """
    warehouses = env['stock.warehouse'].search([])
    for wh in warehouses:
        # 1. Quality Control Location
        parent_loc = wh.view_location_id or wh.lot_stock_id.location_id
        qc_loc = env['stock.location'].search([
            ('company_id', '=', wh.company_id.id),
            ('is_qc_location', '=', True),
            ('location_id', '=', parent_loc.id),
        ], limit=1)
        if not qc_loc:
            qc_loc = env['stock.location'].search([
                ('company_id', '=', wh.company_id.id),
                ('name', '=', 'Quality Control'),
                ('location_id', '=', parent_loc.id),
            ], limit=1)
        if not qc_loc:
            qc_loc = env['stock.location'].create({
                'name': 'Quality Control',
                'usage': 'internal',
                'location_id': parent_loc.id,
                'company_id': wh.company_id.id,
                'is_qc_location': True,
            })
        else:
            qc_loc.write({'is_qc_location': True, 'usage': 'internal'})
        wh.write({'qc_location_id': qc_loc.id})

        # 2. Quarantine Location
        quar_loc = env['stock.location'].search([
            ('company_id', '=', wh.company_id.id),
            ('is_quarantine_location', '=', True),
            ('location_id', '=', parent_loc.id),
        ], limit=1)
        if not quar_loc:
            quar_loc = env['stock.location'].search([
                ('company_id', '=', wh.company_id.id),
                ('name', '=', 'Quarantine'),
                ('location_id', '=', parent_loc.id),
            ], limit=1)
        if not quar_loc:
            quar_loc = env['stock.location'].create({
                'name': 'Quarantine',
                'usage': 'internal',
                'location_id': parent_loc.id,
                'company_id': wh.company_id.id,
                'is_quarantine_location': True,
            })
        else:
            quar_loc.write({'is_quarantine_location': True, 'usage': 'internal'})
        wh.write({'quarantine_location_id': quar_loc.id})

    # Set qc_required on storable / consu products by default
    products = env['product.template'].search([('type', '!=', 'service')])
    if products:
        products.write({'qc_required': True})

    # Pre-seed dynamic parameters for common chemical products if they don't have specifications
    param_cache = {p.code: p for p in env['quality.parameter'].search([]) if p.code}
    def p_id(code):
        return param_cache.get(code).id if param_cache.get(code) else False

    for tmpl in env['product.template'].search([('qc_required', '=', True)]):
        if tmpl.qc_parameter_ids:
            continue
        p_name = (tmpl.name or '').lower()
        if any(k in p_name for k in ['resin', 'polymer', 'pk-100', 'emulsion']):
            env['quality.product.parameter'].create([
                {
                    'product_tmpl_id': tmpl.id,
                    'sequence': 10,
                    'parameter_id': p_id('APPR'),
                    'name': 'Physical Appearance',
                    'parameter_type': 'text',
                    'test_method': 'Visual Inspection @ 25°C',
                    'expected_text': 'Clear Amber Viscous Liquid, free from sediment',
                    'is_mandatory': True,
                },
                {
                    'product_tmpl_id': tmpl.id,
                    'sequence': 20,
                    'parameter_id': p_id('VISC'),
                    'name': 'Viscosity',
                    'parameter_type': 'numeric',
                    'uom_name': 'cP',
                    'test_method': 'ASTM D2196 (Brookfield Viscometer @ 25°C)',
                    'min_value': 2500.0,
                    'max_value': 3500.0,
                    'target_value': '3000 cP',
                    'is_mandatory': True,
                },
                {
                    'product_tmpl_id': tmpl.id,
                    'sequence': 30,
                    'parameter_id': p_id('SOLIDS'),
                    'name': 'Solid Content / Non-Volatile (%)',
                    'parameter_type': 'numeric',
                    'uom_name': '%',
                    'test_method': 'Oven Drying Method @ 105°C',
                    'min_value': 98.0,
                    'max_value': 100.0,
                    'target_value': '99.0 %',
                    'is_mandatory': True,
                },
                {
                    'product_tmpl_id': tmpl.id,
                    'sequence': 40,
                    'parameter_id': p_id('SG'),
                    'name': 'Specific Gravity',
                    'parameter_type': 'numeric',
                    'uom_name': 'g/cm³',
                    'test_method': 'ASTM D891 (Pycnometer @ 25°C)',
                    'min_value': 1.10,
                    'max_value': 1.15,
                    'target_value': '1.12 g/cm³',
                    'is_mandatory': True,
                },
                {
                    'product_tmpl_id': tmpl.id,
                    'sequence': 50,
                    'parameter_id': p_id('COLOR'),
                    'name': 'Color (Gardner / Visual)',
                    'parameter_type': 'text',
                    'test_method': 'Visual / Gardner Scale',
                    'expected_text': 'Amber to Light Yellow (Gardner <= 4)',
                    'is_mandatory': False,
                },
                {
                    'product_tmpl_id': tmpl.id,
                    'sequence': 60,
                    'parameter_id': p_id('PH'),
                    'name': 'pH Value',
                    'parameter_type': 'numeric',
                    'uom_name': 'pH',
                    'test_method': 'ASTM D1293 (Digital pH Meter)',
                    'min_value': 6.5,
                    'max_value': 7.5,
                    'target_value': '7.0',
                    'is_mandatory': False,
                },
                {
                    'product_tmpl_id': tmpl.id,
                    'sequence': 70,
                    'parameter_id': p_id('PKG'),
                    'name': 'Packaging & Label Integrity',
                    'parameter_type': 'boolean',
                    'test_method': 'Physical Container & UN Hazard Label Audit',
                    'is_mandatory': True,
                },
            ])
        elif any(k in p_name for k in ['solvent', 'acetate', 'ethyl', 'alcohol', 'ethanol', 'thinner']):
            env['quality.product.parameter'].create([
                {
                    'product_tmpl_id': tmpl.id,
                    'sequence': 10,
                    'parameter_id': p_id('APPR'),
                    'name': 'Physical Appearance',
                    'parameter_type': 'text',
                    'test_method': 'Visual Inspection @ 25°C',
                    'expected_text': 'Clear Colorless Volatile Liquid, free from turbidity',
                    'is_mandatory': True,
                },
                {
                    'product_tmpl_id': tmpl.id,
                    'sequence': 20,
                    'parameter_id': p_id('PURITY'),
                    'name': 'Purity / Assay (%)',
                    'parameter_type': 'numeric',
                    'uom_name': '%',
                    'test_method': 'Gas Chromatography (GC)',
                    'min_value': 99.5,
                    'max_value': 100.0,
                    'target_value': '99.8 %',
                    'is_mandatory': True,
                },
                {
                    'product_tmpl_id': tmpl.id,
                    'sequence': 30,
                    'parameter_id': p_id('MOIST'),
                    'name': 'Moisture Content (%)',
                    'parameter_type': 'numeric',
                    'uom_name': '%',
                    'test_method': 'Karl Fischer Titration (ASTM D1364)',
                    'min_value': 0.00,
                    'max_value': 0.05,
                    'target_value': '0.02 %',
                    'is_mandatory': True,
                },
                {
                    'product_tmpl_id': tmpl.id,
                    'sequence': 40,
                    'parameter_id': p_id('SG'),
                    'name': 'Specific Gravity',
                    'parameter_type': 'numeric',
                    'uom_name': 'g/cm³',
                    'test_method': 'ASTM D891 (Pycnometer @ 20°C)',
                    'min_value': 0.898,
                    'max_value': 0.902,
                    'target_value': '0.900 g/cm³',
                    'is_mandatory': True,
                },
                {
                    'product_tmpl_id': tmpl.id,
                    'sequence': 50,
                    'parameter_id': p_id('ODOR'),
                    'name': 'Odor',
                    'parameter_type': 'text',
                    'test_method': 'Olfactory Sensory Evaluation',
                    'expected_text': 'Characteristic pleasant fruity ester odor',
                    'is_mandatory': False,
                },
                {
                    'product_tmpl_id': tmpl.id,
                    'sequence': 60,
                    'parameter_id': p_id('COLOR'),
                    'name': 'Color (APHA)',
                    'parameter_type': 'text',
                    'test_method': 'ASTM D1209 (Platinum-Cobalt / APHA)',
                    'expected_text': 'Colorless (Max 10 APHA)',
                    'is_mandatory': False,
                },
                {
                    'product_tmpl_id': tmpl.id,
                    'sequence': 70,
                    'parameter_id': p_id('PKG'),
                    'name': 'Packaging & Flammability Labeling',
                    'parameter_type': 'boolean',
                    'test_method': 'Airtight Seal & Flammable Liquid Hazard Audit',
                    'is_mandatory': True,
                },
            ])

    _logger.info("Custom Quality Control post_init_hook executed successfully.")
