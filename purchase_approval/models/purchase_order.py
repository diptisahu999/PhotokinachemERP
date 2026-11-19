# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    approval_state = fields.Selection([
        ('to_submit', 'Draft / Not Submitted'),
        ('to_approve', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval Status', default='to_submit', copy=False, tracking=True, index=True)

    approver_id = fields.Many2one(
        'res.users',
        string='Concerned Authority',
        domain="[('share', '=', False)]",
        tracking=True,
        help='Select the specific authority or manager responsible for approving this purchase. If left blank, any authorized Purchase Approver can approve.'
    )

    requested_by_id = fields.Many2one(
        'res.users',
        string='Submitted By',
        readonly=True,
        copy=False,
        tracking=True
    )
    request_date = fields.Datetime(
        string='Submission Date',
        readonly=True,
        copy=False,
        tracking=True
    )

    approved_by_id = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        copy=False,
        tracking=True
    )
    approval_date = fields.Datetime(
        string='Approval Date',
        readonly=True,
        copy=False,
        tracking=True
    )

    rejection_reason = fields.Text(
        string='Rejection Reason',
        readonly=True,
        copy=False,
        tracking=True
    )

    approval_notes = fields.Text(
        string='Requester Justification / Notes',
        help='Additional context, justification, or urgency notes for the approving authority.'
    )

    is_approver = fields.Boolean(
        string='Is Current User Approver',
        compute='_compute_is_approver'
    )

    can_send_approval = fields.Boolean(
        string='Can Send for Approval',
        compute='_compute_can_send_approval'
    )

    @classmethod
    def _ensure_approval_columns_exist(cls, env):
        if not getattr(cls, '_approval_columns_verified', False):
            try:
                env.cr.execute("""
                    ALTER TABLE purchase_order ADD COLUMN IF NOT EXISTS approval_state varchar DEFAULT 'to_submit';
                    ALTER TABLE purchase_order ADD COLUMN IF NOT EXISTS approver_id integer;
                    ALTER TABLE purchase_order ADD COLUMN IF NOT EXISTS requested_by_id integer;
                    ALTER TABLE purchase_order ADD COLUMN IF NOT EXISTS request_date timestamp;
                    ALTER TABLE purchase_order ADD COLUMN IF NOT EXISTS approved_by_id integer;
                    ALTER TABLE purchase_order ADD COLUMN IF NOT EXISTS approval_date timestamp;
                    ALTER TABLE purchase_order ADD COLUMN IF NOT EXISTS rejection_reason text;
                    ALTER TABLE purchase_order ADD COLUMN IF NOT EXISTS approval_notes text;
                """)
                cls._approval_columns_verified = True
            except Exception:
                pass

    def init(self):
        super().init()
        self._ensure_approval_columns_exist(self.env)

    def _register_hook(self):
        super()._register_hook()
        self._ensure_approval_columns_exist(self.env)

    @api.depends_context('uid')
    def _compute_is_approver(self):
        current_user = self.env.user
        can_approve = (
            bool(current_user.purchase_approval)
            or current_user.has_group('purchase_approval.group_purchase_approver')
            or current_user.has_group('purchase.group_purchase_manager')
            or self.env.is_superuser()
        )
        for order in self:
            order.is_approver = can_approve

    @api.depends('state', 'approval_state', 'order_line')
    def _compute_can_send_approval(self):
        for order in self:
            order.can_send_approval = (
                order.state in ('draft', 'sent')
                and order.approval_state in ('to_submit', 'rejected')
                and bool(order.order_line)
            )

    def action_send_for_approval(self):
        """
        Sends the RFQ to the concerned authority for approval.
        Updates status, creates an approval activity, and logs in chatter.
        """
        for order in self:
            if not order.order_line:
                raise UserError(_("Cannot submit an empty RFQ. Please add at least one product line."))

            if order.state not in ('draft', 'sent'):
                raise UserError(_("Only draft or sent RFQs can be submitted for approval."))

            order.write({
                'approval_state': 'to_approve',
                'state': 'to approve',
                'requested_by_id': self.env.user.id,
                'request_date': fields.Datetime.now(),
                'rejection_reason': False,
            })

            # Identify target approver users (users with purchase_approval allowed)
            target_users = self.env['res.users'].search([
                ('purchase_approval', '=', True),
                ('active', '=', True),
            ])
            if not target_users:
                approver_group = self.env.ref('purchase_approval.group_purchase_approver', raise_if_not_found=False)
                manager_group = self.env.ref('purchase.group_purchase_manager', raise_if_not_found=False)
                if approver_group and getattr(approver_group, 'user_ids', False):
                    target_users = approver_group.user_ids
                elif manager_group and getattr(manager_group, 'user_ids', False):
                    target_users = manager_group.user_ids

            # Schedule approval activity for target users
            act_type = self.env.ref('purchase_approval.mail_activity_purchase_approval', raise_if_not_found=False)
            act_type_id = act_type.id if act_type else self.env.ref('mail.mail_activity_data_todo').id

            currency_symbol = order.currency_id.symbol or order.currency_id.name or ''
            summary = _("Purchase Approval Required: %s (%s)") % (order.name, order.partner_id.name)
            note = _(
                "Purchase order <b>%s</b> for vendor <b>%s</b> totaling <b>%s %s</b> "
                "submitted by <b>%s</b> requires your review and approval."
            ) % (
                order.name,
                order.partner_id.name,
                f"{order.amount_total:,.2f}",
                currency_symbol,
                self.env.user.name,
            )
            if order.approval_notes:
                note += _("<br/><b>Justification / Notes:</b> %s") % order.approval_notes

            for user in target_users:
                # Avoid duplicate active approval activities for the same user
                existing_act = self.env['mail.activity'].search([
                    ('res_model', '=', 'purchase.order'),
                    ('res_id', '=', order.id),
                    ('user_id', '=', user.id),
                    ('activity_type_id', '=', act_type_id),
                ], limit=1)
                if not existing_act:
                    order.activity_schedule(
                        activity_type_id=act_type_id,
                        summary=summary,
                        note=note,
                        user_id=user.id,
                    )

            # Chatter Notification
            chatter_msg = _(
                "<b>Sent for Purchase Approval</b> by %s.<br/>"
                "<b>Total Amount:</b> %s %s"
            ) % (
                self.env.user.name,
                f"{order.amount_total:,.2f}",
                currency_symbol,
            )
            if order.approval_notes:
                chatter_msg += _("<br/><b>Justification:</b> %s") % order.approval_notes
            order.message_post(body=chatter_msg)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sent for Approval!'),
                'message': _('Purchase Order %s has been submitted for approval.') % self.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_approve_purchase(self):
        """
        Authorized user approves the purchase order.
        Validates authority, marks as approved, records audit trail, and confirms the order.
        """
        for order in self:
            if not order.is_approver:
                raise UserError(_(
                    "⚠️ Permission Denied\n\n"
                    "You do not have the 'Purchase Approval' permission required to approve this order.\n\n"
                    "Only authorized managers with Purchase Approval enabled can approve or confirm purchases."
                ))

            if order.approval_state != 'to_approve':
                raise UserError(_("This order is not waiting for approval."))

            now = fields.Datetime.now()
            order.write({
                'approval_state': 'approved',
                'approved_by_id': self.env.user.id,
                'approval_date': now,
            })

            # Close pending approval activities
            order._close_approval_activities(feedback=_("Approved by %s on %s") % (self.env.user.name, now.strftime('%Y-%m-%d %H:%M')))

            # Post Chatter message
            currency_symbol = order.currency_id.symbol or ''
            order.message_post(body=_(
                "<b>Purchase APPROVED</b> by: <b>%s</b>.<br/>"
                "<b>Approval Date:</b> %s<br/>"
                "<b>Order Total:</b> %s %s"
            ) % (
                self.env.user.name,
                now.strftime('%Y-%m-%d %H:%M:%S'),
                f"{order.amount_total:,.2f}",
                currency_symbol,
            ))

            # Notify requester if requester is different from approver
            if order.requested_by_id and order.requested_by_id != self.env.user:
                order.activity_schedule(
                    activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                    summary=_("Purchase Approved: %s") % order.name,
                    note=_("Your purchase order <b>%s</b> for %s has been APPROVED by <b>%s</b>.") % (
                        order.name,
                        order.partner_id.name,
                        self.env.user.name,
                    ),
                    user_id=order.requested_by_id.id,
                )

            # Directly confirm into active Purchase Order (state = 'purchase')
            # 1. Analytic distribution & supplier validation
            order.order_line._validate_analytic_distribution()
            order._add_supplier_to_product()

            # 2. Transition state directly to 'purchase' and record date_approve
            order.write({
                'state': 'purchase',
                'date_approve': now,
            })
            if order.lock_confirmed_po == 'lock':
                order.write({'locked': True})

            # 3. Create stock picking (warehouse receipt) if stock module is installed
            if hasattr(order, '_create_picking'):
                order._create_picking()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Purchase Approved!'),
                'message': _('Purchase Order %s has been approved and directly confirmed into a Purchase Order.') % self.name,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def action_open_reject_wizard(self):
        """Opens the rejection reason dialog for the concerned authority."""
        self.ensure_one()
        if not self.is_approver:
            raise UserError(_(
                "Access Denied: You do not have 'Purchase Approval' permission to reject this purchase order."
            ))
        return {
            'name': _('Reject Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.approval.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
            },
        }

    def action_cancel_approval_request(self):
        """Requester recalls / cancels the pending approval request."""
        for order in self:
            if order.approval_state != 'to_approve':
                raise UserError(_("Only orders currently waiting for approval can be recalled."))

            order.write({
                'approval_state': 'to_submit',
                'state': 'draft',
            })
            order._close_approval_activities(feedback=_("Approval request cancelled by %s") % self.env.user.name)
            order.message_post(body=_("Purchase approval request was cancelled / recalled by <b>%s</b>.") % self.env.user.name)

    def action_reset_to_draft_approval(self):
        """Allows resetting a rejected purchase back to draft to amend and re-submit."""
        for order in self:
            order.write({
                'approval_state': 'to_submit',
                'state': 'draft',
                'rejection_reason': False,
            })
            order.message_post(body=_("Purchase order reset to draft by <b>%s</b> for revision.") % self.env.user.name)

    def _approval_allowed(self):
        """Returns True if order is approved via purchase_approval workflow or standard rules"""
        if self.approval_state == 'approved':
            return True
        return super()._approval_allowed()

    def button_approve(self, force=False):
        for order in self:
            if not order.is_approver:
                raise UserError(_(
                    "Access Denied: Only users with 'Purchase Approval' allowed can approve this order."
                ))
            now = fields.Datetime.now()
            order.write({
                'approval_state': 'approved',
                'approved_by_id': self.env.user.id,
                'approval_date': now,
                'state': 'purchase',
                'date_approve': now,
            })
            if order.lock_confirmed_po == 'lock':
                order.write({'locked': True})
            if hasattr(order, '_create_picking'):
                order._create_picking()
        return {}

    def button_confirm(self):
        """
        Enforces approval check before confirming:
        - If already approved: confirms normally.
        - If not approved and current user is an authorized approver: auto-approves and confirms.
        - If not approved and user is not an approver: blocks confirmation and instructs them to send for approval.
        """
        for order in self:
            if order.approval_state != 'approved':
                # Check if current user has authority to confirm directly
                if order.is_approver:
                    now = fields.Datetime.now()
                    order.write({
                        'approval_state': 'approved',
                        'approved_by_id': self.env.user.id,
                        'approval_date': now,
                    })
                    order.message_post(body=_(
                        "Purchase Order confirmed directly by authorized authority <b>%s</b>."
                    ) % self.env.user.name)
                else:
                    raise UserError(_(
                        "⚠️ Approval Required\n\n"
                        "This Purchase Order cannot be confirmed directly.\n\n"
                        "You do not have 'Purchase Approval' rights.\n"
                        "Please click the 'Send for Purchase Approval' button to submit it to an authorized manager."
                    ))

        return super().button_confirm()

    def button_cancel(self):
        res = super().button_cancel()
        for order in self:
            order._close_approval_activities(feedback=_("Purchase Order was cancelled."))
        return res

    def _close_approval_activities(self, feedback=""):
        """Clears all pending approval activities for this order."""
        for order in self:
            act_type = self.env.ref('purchase_approval.mail_activity_purchase_approval', raise_if_not_found=False)
            domain = [('res_model', '=', 'purchase.order'), ('res_id', '=', order.id)]
            if act_type:
                domain.append(('activity_type_id', '=', act_type.id))
            activities = self.env['mail.activity'].search(domain)
            if activities:
                activities.action_feedback(feedback=feedback)
