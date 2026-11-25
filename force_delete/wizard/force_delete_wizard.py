# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ForceDeleteWizard(models.TransientModel):
    _name = 'force.delete.wizard'
    _description = 'Force Delete Confirmation Wizard'

    model_name = fields.Char('Model Name', required=True)
    model_description = fields.Char('Document Type', compute='_compute_model_info')
    record_ids = fields.Char('Record IDs', required=True)
    record_names = fields.Text('Records to Delete', readonly=True)
    record_count = fields.Integer('Total Records Selected', compute='_compute_model_info')
    has_done_records = fields.Boolean('Contains Done/Completed Records', compute='_compute_model_info')
    show_revert_stock = fields.Boolean('Show Revert Stock Option', compute='_compute_model_info')
    revert_stock = fields.Boolean(
        'Revert Physical Stock / Quantities',
        default=True,
        help="When enabled, stock quantities will be automatically restored/reverted in inventory quants.",
    )
    delete_chatter = fields.Boolean(
        'Purge Messages, Activities & Attachments',
        default=True,
        help="When enabled, all chatter history, followers, activities, and attachments linked to these records will be cleanly purged.",
    )
    warning_message = fields.Html('Warning Notice', compute='_compute_model_info')

    @api.depends('model_name', 'record_ids')
    def _compute_model_info(self):
        for wizard in self:
            count = 0
            has_done = False
            desc = wizard.model_name or ''
            warning_html = ''
            show_stock = False

            if wizard.model_name and wizard.model_name in self.env:
                ir_model = self.env['ir.model'].search([('model', '=', wizard.model_name)], limit=1)
                desc = ir_model.name if ir_model else wizard.model_name

                ids = [int(i.strip()) for i in (wizard.record_ids or '').split(',') if i.strip().isdigit()]
                count = len(ids)
                records = self.env[wizard.model_name].browse(ids)

                show_stock = wizard.model_name in ('mrp.production', 'stock.picking')
                if hasattr(records, 'state'):
                    has_done = any(r.state in ('done', 'posted', 'closed') for r in records)

                warning_html = f"""
                <div class="alert alert-warning mb-3" role="alert">
                    <h5 class="alert-heading font-weight-bold mb-1">
                        <i class="fa fa-exclamation-triangle me-1"></i> Irreversible Action
                    </h5>
                    <p class="mb-0">
                        You are about to permanently delete <b>{count}</b> {desc} record(s).
                        This bypasses standard business constraints (e.g. Done or Validated states) and permanently wipes all relational data.
                    </p>
                </div>
                """
                if has_done and show_stock:
                    warning_html += """
                    <div class="alert alert-info py-2 mb-3" role="alert">
                        <i class="fa fa-info-circle me-1"></i>
                        One or more selected records are marked as <b>Done</b>. If <b>Revert Physical Stock</b> is checked,
                        inventory quants will be reversed back to their pre-operation state.
                    </div>
                    """

            wizard.model_description = desc
            wizard.record_count = count
            wizard.has_done_records = has_done
            wizard.show_revert_stock = show_stock
            wizard.warning_message = warning_html

    def action_confirm_force_delete(self):
        """Execute the permanent forced deletion."""
        self.ensure_one()
        if not self.env.user.has_group('force_delete.group_force_delete'):
            raise UserError(_("You do not have permission to force delete records."))

        if not self.model_name or self.model_name not in self.env:
            raise UserError(_("Invalid model: %s") % self.model_name)

        ids = [int(i.strip()) for i in (self.record_ids or '').split(',') if i.strip().isdigit()]
        if not ids:
            raise UserError(_("No valid records specified for deletion."))

        records = self.env[self.model_name].browse(ids)
        existing_records = records.exists()
        if not existing_records:
            raise UserError(_("The selected record(s) no longer exist in the database."))

        record_names_text = self.record_names or ', '.join(r.display_name for r in existing_records)
        del_count = len(existing_records)
        model_desc = self.model_description or self.model_name

        # Execute model-specific force deletion or generic fallback
        if hasattr(existing_records, 'perform_force_delete'):
            existing_records.perform_force_delete(revert_stock=self.revert_stock, delete_chatter=self.delete_chatter)
        else:
            if self.delete_chatter:
                self.env['mail.activity'].sudo().search([('res_model', '=', self.model_name), ('res_id', 'in', existing_records.ids)]).unlink()
                self.env['mail.message'].sudo().search([('model', '=', self.model_name), ('res_id', 'in', existing_records.ids)]).unlink()
                self.env['mail.followers'].sudo().search([('res_model', '=', self.model_name), ('res_id', 'in', existing_records.ids)]).unlink()
                self.env['ir.attachment'].sudo().search([('res_model', '=', self.model_name), ('res_id', 'in', existing_records.ids)]).unlink()
            existing_records.with_context(force_delete=True).unlink()

        # Create persistent audit log
        try:
            self.env['force.delete.log'].sudo().create({
                'name': f"Forced Delete: {del_count} {model_desc} record(s)",
                'user_id': self.env.user.id,
                'res_model': self.model_name,
                'res_model_name': model_desc,
                'record_ids_text': ', '.join(str(i) for i in ids),
                'record_names': record_names_text,
                'record_count': del_count,
                'revert_stock': bool(self.revert_stock and self.show_revert_stock),
                'details': f"Successfully force-deleted {del_count} records. Revert stock: {self.revert_stock}. Delete chatter: {self.delete_chatter}.",
            })
        except Exception as e:
            _logger.warning("Could not create force delete audit log: %s", e)

        # Notify user and reload view
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Records Permanently Deleted'),
                'message': _('Successfully force-deleted %d %s record(s).') % (del_count, model_desc),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }
