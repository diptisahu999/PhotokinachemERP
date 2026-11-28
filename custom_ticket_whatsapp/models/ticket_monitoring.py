# -*- coding: utf-8 -*-
import logging
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TicketMonitoringWhatsapp(models.Model):
    _inherit = 'ticket.monitoring'

    def _get_recipient_mobile(self, user):
        """Extract and sanitize mobile number from user/partner safely."""
        if not user:
            return False
        partner = getattr(user, 'partner_id', False) or user
        raw_number = (
            getattr(user, 'phone', False)
            or getattr(partner, 'mobile', False)
            or getattr(partner, 'phone', False)
            or getattr(user, 'mobile', False)
        )
        config = self.env['ticket.whatsapp.config'].get_config()
        return config.sanitize_mobile(raw_number) if config else False

    def _send_infiq_template(self, template_name, parameters, recipient_mobile, event_label):
        """Low-level helper to dispatch a template message via InfiQ API."""
        config = self.env['ticket.whatsapp.config'].get_config()
        if not config or not config.is_enabled or not config.api_key:
            _logger.info("InfiQ WhatsApp disabled or API key missing. Skipping message for %s.", event_label)
            return False

        if not recipient_mobile:
            _logger.warning("No valid recipient mobile for ticket %s (%s). Skipping WhatsApp.", self.name, event_label)
            return False

        headers = {
            "X-INFIQ-API-KEY": config.api_key.strip(),
            "Content-Type": "application/json",
        }

        body_parameters = [{"type": "text", "text": str(p or '')} for p in parameters]

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_mobile,
            "type": "template",
            "template": {
                "name": template_name.strip(),
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": body_parameters,
                    }
                ]
            }
        }

        try:
            resp = requests.post(config.api_url.strip(), headers=headers, json=payload, timeout=12)
            if resp.status_code in (200, 201):
                self.message_post(body=_(
                    "📱 <b>WhatsApp Sent [%s]</b> to <code>%s</code>.<br/>Template: <code>%s</code>"
                ) % (event_label, recipient_mobile, template_name))
                return True
            else:
                self.message_post(body=_(
                    "⚠️ <b>WhatsApp [%s] Failed</b> (HTTP %s): %s"
                ) % (event_label, resp.status_code, resp.text))
                return False
        except Exception as e:
            _logger.error("Failed to send WhatsApp message via InfiQ: %s", str(e))
            return False

    # -------------------------------------------------------------
    # 1. TASK REGISTRATION NOTIFICATION
    # -------------------------------------------------------------
    def _whatsapp_notify_registered(self):
        """Notification 1: Task registration (Image 1 format: Task ID, Reg Date, From, To, Problem, Priority, Deadline)."""
        config = self.env['ticket.whatsapp.config'].get_config()
        if not config:
            return

        for ticket in self:
            mobile = ticket._get_recipient_mobile(ticket.owner_id)
            if not mobile:
                continue

            priority_label = dict(ticket._fields['priority'].selection).get(ticket.priority, ticket.priority or '')
            deadline_str = ticket.resolution_deadline.strftime('%d-%m-%Y %H:%M') if ticket.resolution_deadline else 'As per SLA'
            reg_date_str = ticket.create_date.strftime('%d-%m-%Y %H:%M') if ticket.create_date else fields.Datetime.now().strftime('%d-%m-%Y %H:%M')
            from_str = f"{ticket.origin_department_id.name or 'N/A'} / {ticket.user_id.name or 'N/A'}"
            to_str = f"{ticket.assigned_department_id.name or 'N/A'} / {ticket.owner_id.name or 'N/A'}"

            params = [
                ticket.name or '',                                   # {{1}} Task ID
                reg_date_str,                                        # {{2}} Registered (Date & Time)
                from_str,                                            # {{3}} From (Dept. / Requester)
                to_str,                                              # {{4}} To (Dept. / Assignee)
                ticket.subject or '',                                # {{5}} Task / Problem
                priority_label,                                      # {{6}} Priority
                deadline_str,                                        # {{7}} Target completion
            ]
            ticket._send_infiq_template(config.template_registered, params, mobile, "Task Registration")

    # -------------------------------------------------------------
    # 2. STATE CHANGES NOTIFICATION (Image 2 format: 02 TASK STATUS UPDATE)
    # -------------------------------------------------------------
    def _whatsapp_notify_status_change(self, new_status, remarks, old_status='Assigned'):
        """Notification 2: State change (WIP, ON HOLD) matching 02 TASK STATUS UPDATE format."""
        config = self.env['ticket.whatsapp.config'].get_config()
        if not config:
            return

        for ticket in self:
            recipients = set()
            owner_mob = ticket._get_recipient_mobile(ticket.owner_id)
            req_mob = ticket._get_recipient_mobile(ticket.user_id)
            if owner_mob:
                recipients.add(owner_mob)
            if req_mob:
                recipients.add(req_mob)

            now_str = fields.Datetime.now().strftime('%d-%m-%Y %H:%M')
            from_to_str = f"{ticket.origin_department_id.name or 'N/A'} / {ticket.assigned_department_id.name or 'N/A'}"
            status_flow = f"{old_status} to {new_status}"
            action_str = ticket.action_taken or remarks or 'Work in progress'
            reason_str = remarks or ticket.escalation_reason or 'Status updated as per workflow'

            params = [
                f"{ticket.name} / {ticket.subject or 'Task'}",       # {{1}} Task ID / Title
                now_str,                                             # {{2}} Updated: Date & Time
                from_to_str,                                         # {{3}} From / To: Requesting Dept. / Responsible Dept.
                ticket.env.user.name or 'System',                    # {{4}} Updated by: Name
                status_flow,                                         # {{5}} Status: Previous to WIP / ON HOLD
                action_str,                                          # {{6}} Action taken: Details
                reason_str,                                          # {{7}} Reason / Remarks: Mandatory
            ]

            for mob in recipients:
                ticket._send_infiq_template(config.template_status, params, mob, f"Status: {new_status}")

    # -------------------------------------------------------------
    # 3. COMPLETION OF TASK NOTIFICATION (Image 2 format: 03 TASK COMPLETED)
    # -------------------------------------------------------------
    def _whatsapp_notify_completed(self, remarks):
        """Notification 3: Task completion matching 03 TASK COMPLETED format."""
        config = self.env['ticket.whatsapp.config'].get_config()
        if not config:
            return

        for ticket in self:
            recipients = set()
            owner_mob = ticket._get_recipient_mobile(ticket.owner_id)
            req_mob = ticket._get_recipient_mobile(ticket.user_id)
            if owner_mob:
                recipients.add(owner_mob)
            if req_mob:
                recipients.add(req_mob)

            start_dt = ticket.first_response_date or ticket.create_date
            start_str = start_dt.strftime('%d-%m-%Y %H:%M') if start_dt else 'N/A'
            finish_dt = ticket.resolved_date or ticket.closed_date or fields.Datetime.now()
            finish_str = finish_dt.strftime('%d-%m-%Y %H:%M')
            target_str = ticket.resolution_deadline.strftime('%d-%m-%Y %H:%M') if ticket.resolution_deadline else 'As per SLA'
            
            # Compute time taken
            if start_dt and finish_dt:
                diff = finish_dt - start_dt
                hours = diff.total_seconds() / 3600.0
                time_taken_str = f"{hours:.1f} Hours" if hours < 24 else f"{hours / 24:.1f} Days ({hours:.1f} Hours)"
            else:
                time_taken_str = f"{ticket.resolution_duration_hours:.1f} Hours" if ticket.resolution_duration_hours else 'On schedule'

            from_to_str = f"{ticket.origin_department_id.name or 'N/A'} / {ticket.assigned_department_id.name or 'N/A'}"
            solution_str = ticket.action_taken or remarks or 'Resolution verified and implemented'
            final_remarks_str = remarks or ticket.requester_feedback or 'Task completed within SLA'

            params = [
                f"{ticket.name} / {ticket.subject or 'Task'}",       # {{1}} Task ID / Title
                ticket.owner_id.name or ticket.env.user.name or 'N/A', # {{2}} Completed by
                from_to_str,                                         # {{3}} From / To
                start_str,                                           # {{4}} Actual start
                finish_str,                                          # {{5}} Actual finish
                target_str,                                          # {{6}} Target
                time_taken_str,                                      # {{7}} Time taken
                solution_str,                                        # {{8}} Solution
                final_remarks_str,                                   # {{9}} Delay reason / Final remarks
            ]

            for mob in recipients:
                ticket._send_infiq_template(config.template_completed, params, mob, "Task Completed")

    # -------------------------------------------------------------
    # CRUD & LIFECYCLE HOOKS
    # -------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        tickets = super().create(vals_list)
        for t in tickets:
            if t.owner_id:
                t._whatsapp_notify_registered()
        return tickets

    def write(self, vals):
        old_states = {t.id: t.state for t in self}
        old_owners = {t.id: t.owner_id.id for t in self}
        res = super().write(vals)

        for t in self:
            # 1. Assignment changed
            if 'owner_id' in vals and vals['owner_id'] and t.owner_id.id != old_owners.get(t.id):
                t._whatsapp_notify_registered()

            # 2. State changed
            if 'state' in vals and vals['state'] != old_states.get(t.id):
                new_state = vals['state']
                old_state_label = dict(t._fields['state'].selection).get(old_states.get(t.id), 'Assigned')
                if new_state == 'in_progress':
                    t._whatsapp_notify_status_change('WIP (In Progress)', vals.get('action_taken') or 'Work started by owner', old_status=old_state_label)
                elif new_state == 'on_hold':
                    t._whatsapp_notify_status_change('ON HOLD', t.escalation_reason or vals.get('escalation_reason') or 'Task placed on hold', old_status=old_state_label)
                elif new_state in ('resolved', 'closed'):
                    t._whatsapp_notify_completed(t.action_taken or vals.get('action_taken') or 'Task completed and verified')
        return res

    def action_assign_owner(self):
        super().action_assign_owner()
        self._whatsapp_notify_registered()

    def action_accept(self):
        super().action_accept()
        self._whatsapp_notify_status_change('WIP (In Progress)', 'Owner formally accepted responsibility')

    def action_hold(self):
        super().action_hold()
        self._whatsapp_notify_status_change('ON HOLD', self.escalation_reason or 'Task suspended on hold')

    def action_resolve(self):
        super().action_resolve()
        self._whatsapp_notify_completed(self.action_taken or 'Resolution submitted for requester verification')

    def action_close(self):
        super().action_close()
        self._whatsapp_notify_completed(self.requester_feedback or 'Task verified and formally closed')

    def action_send_whatsapp_manual(self):
        """Manual trigger button to send WhatsApp assignment alert."""
        self.ensure_one()
        if not self.owner_id:
            raise UserError(_("Please assign an Owner to send WhatsApp notification."))
        mobile = self._get_recipient_mobile(self.owner_id)
        if not mobile:
            raise UserError(_("Assigned Owner %s does not have a valid mobile number configured in Users / Contacts.") % self.owner_id.name)
        self._whatsapp_notify_registered()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("WhatsApp Triggered"),
                'message': _("Notification dispatched to %s (%s). Check Chatter for delivery status.") % (self.owner_id.name, mobile),
                'type': 'info',
                'sticky': False,
            }
        }

    def action_send_whatsapp_status_manual(self):
        """Manual trigger to send WhatsApp Status alert."""
        self.ensure_one()
        status_label = dict(self._fields['state'].selection).get(self.state, self.state)
        self._whatsapp_notify_status_change(status_label, self.action_taken or self.escalation_reason or 'Status alert manually triggered')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("WhatsApp Status Alert Triggered"),
                'message': _("Status notification dispatched. Check Chatter for delivery status."),
                'type': 'info',
                'sticky': False,
            }
        }

    def action_send_whatsapp_completion_manual(self):
        """Manual trigger to send WhatsApp Completion alert."""
        self.ensure_one()
        self._whatsapp_notify_completed(self.action_taken or self.requester_feedback or 'Completion alert manually triggered')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("WhatsApp Completion Alert Triggered"),
                'message': _("Completion notification dispatched. Check Chatter for delivery status."),
                'type': 'info',
                'sticky': False,
            }
        }
