# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseApprovalRejectWizard(models.TransientModel):
    _name = 'purchase.approval.reject.wizard'
    _description = 'Purchase Approval Rejection Wizard'

    order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
        readonly=True
    )
    rejection_reason = fields.Text(
        string='Reason for Rejection',
        required=True,
        help='State clearly why this purchase request cannot be approved (e.g. Budget exceeded, Incorrect specifications, Price too high).'
    )

    def action_confirm_reject(self):
        """Confirms rejection with reason and informs the requester."""
        self.ensure_one()
        order = self.order_id

        if not order.is_approver:
            raise UserError(_("Access Denied: You do not have 'Purchase Approval' permission to reject this purchase order."))

        if not self.rejection_reason or not self.rejection_reason.strip():
            raise UserError(_("Please provide a valid reason for rejecting this purchase order."))

        reason = self.rejection_reason.strip()
        now = fields.Datetime.now()

        order.write({
            'approval_state': 'rejected',
            'state': 'draft',
            'rejection_reason': reason,
        })

        # Close approval activities
        order._close_approval_activities(feedback=_("Rejected by %s on %s: %s") % (self.env.user.name, now.strftime('%Y-%m-%d %H:%M'), reason))

        # Post in chatter
        order.message_post(body=_(
            "<b>Purchase Order REJECTED</b> by: <b>%s</b>.<br/>"
            "<b>Rejection Reason:</b> %s<br/>"
            "The RFQ has been returned to Draft for modification or review."
        ) % (self.env.user.name, reason))

        # Notify requester
        if order.requested_by_id and order.requested_by_id != self.env.user:
            order.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                summary=_("Purchase Order Rejected: %s") % order.name,
                note=_(
                    "Your purchase request for <b>%s</b> has been <b>REJECTED</b> by <b>%s</b>.<br/>"
                    "<b>Reason:</b> %s"
                ) % (order.name, self.env.user.name, reason),
                user_id=order.requested_by_id.id,
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Purchase Rejected'),
                'message': _('Purchase Order %s has been rejected and returned to draft.') % order.name,
                'type': 'warning',
                'sticky': False,
            }
        }
