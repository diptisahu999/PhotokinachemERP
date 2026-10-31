# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.tools.float_utils import float_round


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _compute_bom_price(self, bom, boms_to_recompute=False):
        self.ensure_one()
        if not bom:
            return 0.0
        if not boms_to_recompute:
            boms_to_recompute = []
        total = 0.0
        for opt in bom.operation_ids:
            if opt._skip_operation_line(self):
                continue
            total += opt.cost

        for line in bom.bom_line_ids:
            if line._skip_bom_line(self):
                continue

            # Compute recursive if line has `child_line_ids`
            if line.child_bom_id and line.child_bom_id in boms_to_recompute:
                child_total = line.product_id._compute_bom_price(line.child_bom_id, boms_to_recompute=boms_to_recompute)
                total += line.product_id.uom_id._compute_price(child_total, line.product_uom_id) * line.product_qty
            else:
                price = self.env['stock.move']._get_move_component_price(
                    line.product_id, line.product_uom_id, bom.company_id, date=fields.Date.today()
                )
                total += price * line.product_qty

        if bom.byproduct_ids:
            byproduct_cost_share = sum(bom.byproduct_ids.mapped('cost_share'))
            if byproduct_cost_share:
                total *= float_round(1 - byproduct_cost_share / 100, precision_rounding=0.0001)

        return bom.product_uom_id._compute_price(total / (bom.product_qty or 1.0), self.uom_id)
