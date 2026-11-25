# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_force_delete(self):
        """Triggered from the Actions dropdown menu to open Force Delete confirmation wizard."""
        if not self:
            raise UserError(_("Please select at least one Invoice / Journal Entry to force delete."))
        if not self.env.user.has_group('force_delete.group_force_delete'):
            raise UserError(_("You do not have permission to force delete records."))

        names = [f"• {move.name or move.ref or 'Draft Move'} ({move.partner_id.name or 'No Partner'} - State: {move.state})" for move in self]
        wizard_view = self.env.ref('force_delete.view_force_delete_wizard_form', raise_if_not_found=False)
        return {
            'name': _('Force Delete Invoices / Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'force.delete.wizard',
            'view_mode': 'form',
            'view_id': wizard_view.id if wizard_view else False,
            'views': [(wizard_view.id if wizard_view else False, 'form')],
            'target': 'new',
            'context': {
                'default_model_name': self._name,
                'default_record_ids': ','.join(str(i) for i in self.ids),
                'default_record_names': '\n'.join(names),
            }
        }

    def _unlink_forbid_parts_of_chain(self):
        if self.env.context.get('force_delete'):
            return
        return super()._unlink_forbid_parts_of_chain()

    def perform_force_delete(self, revert_stock=True, delete_chatter=True):
        """Forcibly delete journal entries / invoices."""
        if not self.env.user.has_group('force_delete.group_force_delete'):
            raise UserError(_("You do not have permission to force delete records."))

        for move in self:
            _logger.info("Force deleting Account Move %s (ID: %s, State: %s)...", move.name, move.id, move.state)
            if move.state == 'posted':
                try:
                    move.button_draft()
                except Exception as e:
                    _logger.warning("Could not reset move %s to draft: %s", move.id, e)

            move.line_ids.with_context(force_delete=True).unlink()

            if delete_chatter:
                self.env['mail.activity'].sudo().search([('res_model', '=', 'account.move'), ('res_id', '=', move.id)]).unlink()
                self.env['mail.message'].sudo().search([('model', '=', 'account.move'), ('res_id', '=', move.id)]).unlink()
                self.env['ir.attachment'].sudo().search([('res_model', '=', 'account.move'), ('res_id', '=', move.id)]).unlink()

            move.with_context(force_delete=True).unlink()

        return True
