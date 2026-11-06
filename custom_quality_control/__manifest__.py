# -*- coding: utf-8 -*-
{
    'name': 'QA/QC Management - Purchase & Manufacturing',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Quality',
    'summary': 'Quality Control for Incoming Purchases and Manufacturing Orders with Dynamic Test Parameters & Inventory Release Routing',
    'description': """
QA / QC Management for Purchase Receipts and Manufacturing Orders
==================================================================
This module implements a complete Quality Assurance & Quality Control (QA/QC) system
specifically tailored for incoming raw material purchases and finished manufactured batches:

Key Workflows:
--------------
1. **Purchase Validation -> Quality Control**:
   * Validating a purchase receipt automatically moves products to a dedicated Quality Control location (WH/Quality Control).
   * Products are NOT placed in usable inventory (WH/Stock) until they have been inspected and passed.
   * A Quality Check record is automatically generated for each received product/lot.

2. **Manufacturing Completion -> Quality Control**:
   * Marking a Manufacturing Order (MO) as Done automatically moves finished goods into Quality Control.
   * Products are held in QC until approved by the quality team.
   * A Quality Check record is automatically generated for the finished batch and lot.

3. **Dynamic Test Parameters & Analysis**:
   * Pre-configured master parameters (pH, Viscosity, Specific Gravity, Purity %, Moisture %, Appearance, Color, Odor, etc.).
   * Product templates can define standard quality specifications.
   * During actual testing, analysts can **dynamically add or remove parameters** on the fly.
   * Supports Quantitative (numeric with min/max/target/tolerance), Qualitative (descriptive text), and Conformance (boolean) tests.
   * Real-time automated Pass/Fail calculation based on numerical bounds.

4. **Approval & Inventory Release**:
   * Clicking **Pass**: Marks inspection as Passed and automatically generates and validates an internal stock transfer from Quality Control to Inventory (WH/Stock).
   * Clicking **Fail**: Blocks product release, marks inspection as Failed, and allows one-click transfer to Quarantine / Scrap.
   * Smart buttons on Purchase Orders, Receipts, and Manufacturing Orders for complete visibility.

5. **Certificate of Analysis (COA) / QC Report**:
   * Professional printable PDF report showing tested parameters, specifications, observed values, pass/fail status, and authorized signatures.
    """,
    'author': 'Techvizor',
    'depends': [
        'base',
        'mail',
        'stock',
        'purchase',
        'purchase_stock',
        'mrp',
    ],
    'data': [
        'security/quality_security.xml',
        'security/ir.model.access.csv',
        'data/quality_sequence_data.xml',
        'data/quality_parameter_data.xml',
        'views/quality_parameter_views.xml',
        'views/quality_check_views.xml',
        'views/quality_release_wizard_views.xml',
        'views/product_views.xml',
        'views/purchase_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_picking_qc_wizard_views.xml',
        'views/mrp_production_views.xml',
        'views/stock_warehouse_views.xml',
        'views/quality_menus.xml',
        'report/quality_report.xml',
        'report/quality_check_report_template.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

