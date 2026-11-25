# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

try:
    from odoo.addons.stock.models.stock_move import StockMove as OdooStockMove
except ImportError:
    OdooStockMove = models.Model


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _unlink_if_draft_or_cancel(self):
        if self.env.context.get('force_delete'):
            return
        return super()._unlink_if_draft_or_cancel()

    def _action_cancel(self):
        if self.env.context.get('force_delete'):
            return True
        return super()._action_cancel()

    def unlink(self):
        if self.env.context.get('force_delete'):
            self.with_context(force_delete=True, prefetch_fields=False).mapped('move_line_ids').unlink()
            return super(OdooStockMove, self).unlink()
        return super().unlink()


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _unlink_except_done_or_cancel(self):
        if self.env.context.get('force_delete'):
            return
        return super()._unlink_except_done_or_cancel()
