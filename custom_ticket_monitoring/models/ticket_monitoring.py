# -*- coding: utf-8 -*-
import datetime
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class TicketMonitoring(models.Model):
    _name = 'ticket.monitoring'
    _description = 'PCPL Operational Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, resolution_deadline asc, id desc'

    # 1. Ticket ID & Timestamps
    name = fields.Char(
        string='Ticket ID',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    create_date = fields.Datetime(string='Created Date/Time', readonly=True)

    # 2. Requester Details
    user_id = fields.Many2one(
        'res.users',
        string='Raised By',
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )
    employee_code = fields.Char(
        string='Employee Code',
        help="Employee ID or Badge number",
    )

    # 3. Department Routing
    origin_department_id = fields.Many2one(
        'ticket.department',
        string='Originating Department',
        required=True,
        tracking=True,
    )
    assigned_department_id = fields.Many2one(
        'ticket.department',
        string='Assigned Department',
        required=True,
        tracking=True,
        index=True,
    )
    is_mis_department = fields.Boolean(
        string='Is MIS Ticket',
        compute='_compute_is_mis_department',
        store=True,
    )

    # 4. Classification
    category_id = fields.Many2one(
        'ticket.category',
        string='Category / Issue Type',
        domain="[('department_id', '=', assigned_department_id)]",
        tracking=True,
    )
    subject = fields.Char(string='Subject / Short Title', required=True, tracking=True)
    description = fields.Text(string='Detailed Description & Business Impact', required=True)

    # 5. Priority & SLAs
    priority = fields.Selection([
        ('p1', 'P1 – Critical (2h Resolution)'),
        ('p2', 'P2 – High (4h Resolution)'),
        ('p3', 'P3 – Medium (24h Resolution)'),
        ('p4', 'P4 – Low (48h Resolution)'),
    ], string='Priority', default='p3', required=True, tracking=True, index=True)

    response_deadline = fields.Datetime(
        string='First Response Deadline',
        compute='_compute_sla_deadlines',
        store=True,
        readonly=False,
        help="SLA deadline for the owner to acknowledge/accept the ticket.",
    )
    resolution_deadline = fields.Datetime(
        string='Target Resolution Deadline',
        compute='_compute_sla_deadlines',
        store=True,
        readonly=False,
        index=True,
        help="SLA target deadline to completely resolve the ticket.",
    )

    # Actual Timestamps
    first_response_date = fields.Datetime(string='First Acknowledged Date', readonly=True, tracking=True)
    resolved_date = fields.Datetime(string='Resolved Date', readonly=True, tracking=True)
    closed_date = fields.Datetime(string='Closure Date', readonly=True, tracking=True)
    resolution_duration_hours = fields.Float(
        string='Resolution Duration (Hours)',
        compute='_compute_duration',
        store=True,
        help="Total hours from ticket creation to verified closure.",
    )

    # SLA Compliance Status
    is_response_breached = fields.Boolean(string='Response SLA Breached', compute='_compute_sla_status', store=True)
    is_resolution_breached = fields.Boolean(string='Resolution SLA Breached', compute='_compute_sla_status', store=True)
    sla_status = fields.Selection([
        ('within_sla', 'Within SLA'),
        ('risk', 'At Risk (>75% Elapsed)'),
        ('breached', 'SLA Breached'),
        ('met', 'SLA Met on Time'),
    ], string='SLA Compliance', compute='_compute_sla_status', store=True, tracking=True)

    # 6. Ownership & Lifecycle
    owner_id = fields.Many2one(
        'res.users',
        string='Assigned Owner',
        tracking=True,
        index=True,
        help="Single accountable employee responsible for resolving this issue.",
    )
    stage_id = fields.Many2one(
        'ticket.stage',
        string='Stage',
        compute='_compute_stage_id',
        store=True,
        readonly=False,
        tracking=True,
        group_expand='_read_group_stage_ids',
    )
    state = fields.Selection([
        ('draft', 'Draft / Submitted'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'Under Review / On Hold'),
        ('resolved', 'Resolved (Pending Verification)'),
        ('closed', 'Closed'),
        ('reopened', 'Reopened'),
    ], string='Status', default='draft', required=True, tracking=True, index=True)

    # 7. Escalation Management
    escalation_level = fields.Selection([
        ('l1', 'L1 – Assigned Owner'),
        ('l2', 'L2 – Department HOD (75% Elapsed)'),
        ('l3', 'L3 – General Manager (SLA Breached)'),
        ('l4', 'L4 – CEO / Managing Director (Critical Impact)'),
    ], string='Escalation Level', default='l1', required=True, tracking=True)
    escalation_reason = fields.Text(string='Escalation Reason / Notes')

    # 8. Resolution & CAPA
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'ticket_issue_attachment_rel',
        'ticket_id', 'attachment_id',
        string='Attached Evidence / Photos',
    )
    action_taken = fields.Text(string='Action & Corrective Steps Taken', tracking=True)
    root_cause = fields.Text(string='Root Cause Analysis (RCA)', tracking=True)
    capa_action = fields.Text(string='Corrective & Preventive Action (CAPA)', tracking=True)
    progress = fields.Integer(string='Progress (%)', default=0, tracking=True)
    hold_reason = fields.Char(string='Hold Reason / Dependency', tracking=True)
    resume_date = fields.Datetime(string='Expected Resume Date', tracking=True)
    pending_from = fields.Char(string='Pending From', tracking=True)
    resolution_evidence_ids = fields.Many2many(
        'ir.attachment',
        'ticket_resolution_attachment_rel',
        'ticket_id', 'attachment_id',
        string='Resolution Evidence',
    )

    # 9. Verification & Satisfaction (Requester)
    is_reopened = fields.Boolean(string='Reopened', default=False, tracking=True)
    reopen_count = fields.Integer(string='Reopen Count', default=0)
    reopen_reason = fields.Text(string='Reopen Reason')
    satisfaction_score = fields.Selection([
        ('1', '★☆☆☆☆ (1 - Very Unsatisfied)'),
        ('2', '★★☆☆☆ (2 - Unsatisfied)'),
        ('3', '★★★☆☆ (3 - Neutral)'),
        ('4', '★★★★☆ (4 - Satisfied)'),
        ('5', '★★★★★ (5 - Very Satisfied)'),
    ], string='Satisfaction Score', tracking=True)
    requester_feedback = fields.Text(string='Requester Feedback / Remarks')

    # 10. Specific MIS Department Fields
    report_name = fields.Char(string='Report Name')
    reporting_period = fields.Selection([
        ('daily', 'Daily MIS'),
        ('weekly', 'Weekly MIS'),
        ('monthly', 'Monthly MIS'),
        ('quarterly', 'Quarterly MIS'),
        ('ad_hoc', 'Ad-hoc / Special MIS'),
    ], string='Reporting Period')
    source_system = fields.Selection([
        ('tally', 'TallyPrime'),
        ('gsheet', 'Google Sheets'),
        ('erp', 'Odoo ERP'),
        ('physical', 'Physical / Register'),
        ('other', 'Other System'),
    ], string='Source System')
    affected_kpi = fields.Char(string='Affected KPI')
    data_owner_id = fields.Many2one('res.users', string='Data Owner / Source SPOC')
    validation_owner_id = fields.Many2one('res.users', string='Validation Owner')

    # ---------------------------------------------------------
    # COMPUTED METHODS
    # ---------------------------------------------------------
    @api.depends('assigned_department_id')
    def _compute_is_mis_department(self):
        for ticket in self:
            code = ticket.assigned_department_id.code if ticket.assigned_department_id else ''
            ticket.is_mis_department = (code.upper() == 'MIS') if code else False

    @api.depends('create_date', 'priority')
    def _compute_sla_deadlines(self):
        # SLA Matrix Configuration (in hours)
        sla_matrix = {
            'p1': {'response_hours': 0.25, 'resolution_hours': 2.0},    # 15m / 2h
            'p2': {'response_hours': 0.50, 'resolution_hours': 4.0},    # 30m / 4h
            'p3': {'response_hours': 2.00, 'resolution_hours': 24.0},   # 2h / 24h
            'p4': {'response_hours': 4.00, 'resolution_hours': 48.0},   # 4h / 48h
        }
        for ticket in self:
            base_time = ticket.create_date or fields.Datetime.now()
            config = sla_matrix.get(ticket.priority, sla_matrix['p3'])
            ticket.response_deadline = base_time + datetime.timedelta(hours=config['response_hours'])
            ticket.resolution_deadline = base_time + datetime.timedelta(hours=config['resolution_hours'])

    @api.depends('create_date', 'closed_date', 'resolved_date')
    def _compute_duration(self):
        for ticket in self:
            end_dt = ticket.closed_date or ticket.resolved_date
            if ticket.create_date and end_dt:
                delta = end_dt - ticket.create_date
                ticket.resolution_duration_hours = round(delta.total_seconds() / 3600.0, 2)
            else:
                ticket.resolution_duration_hours = 0.0

    @api.depends('state', 'first_response_date', 'response_deadline', 'resolved_date', 'closed_date', 'resolution_deadline')
    def _compute_sla_status(self):
        now = fields.Datetime.now()
        for ticket in self:
            # Response SLA check
            if ticket.response_deadline:
                resp_dt = ticket.first_response_date or now
                ticket.is_response_breached = (resp_dt > ticket.response_deadline and not ticket.first_response_date)
            else:
                ticket.is_response_breached = False

            # Resolution SLA check
            if ticket.state in ('closed', 'resolved'):
                end_dt = ticket.resolved_date or ticket.closed_date or now
                if ticket.resolution_deadline and end_dt > ticket.resolution_deadline:
                    ticket.is_resolution_breached = True
                    ticket.sla_status = 'breached'
                else:
                    ticket.is_resolution_breached = False
                    ticket.sla_status = 'met'
            else:
                if ticket.resolution_deadline:
                    if now > ticket.resolution_deadline:
                        ticket.is_resolution_breached = True
                        ticket.sla_status = 'breached'
                    elif ticket.create_date:
                        total_secs = (ticket.resolution_deadline - ticket.create_date).total_seconds()
                        elapsed_secs = (now - ticket.create_date).total_seconds()
                        if total_secs > 0 and (elapsed_secs / total_secs) >= 0.75:
                            ticket.sla_status = 'risk'
                        else:
                            ticket.sla_status = 'within_sla'
                        ticket.is_resolution_breached = False
                    else:
                        ticket.sla_status = 'within_sla'
                        ticket.is_resolution_breached = False
                else:
                    ticket.sla_status = 'within_sla'
                    ticket.is_resolution_breached = False

    @api.depends('state')
    def _compute_stage_id(self):
        for ticket in self:
            stage = self.env['ticket.stage'].search([('state', '=', ticket.state)], limit=1)
            if stage:
                ticket.stage_id = stage.id

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env['ticket.stage'].search([])

    # ---------------------------------------------------------
    # ONCHANGE METHODS
    # ---------------------------------------------------------
    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id:
            if self.category_id.default_priority:
                self.priority = self.category_id.default_priority
            if self.category_id.default_owner_id:
                self.owner_id = self.category_id.default_owner_id

    @api.onchange('assigned_department_id')
    def _onchange_assigned_department_id(self):
        if self.assigned_department_id:
            if not self.owner_id and self.assigned_department_id.hod_id:
                self.owner_id = self.assigned_department_id.hod_id
            if self.category_id and self.category_id.department_id != self.assigned_department_id:
                self.category_id = False

    # ---------------------------------------------------------
    # CRUD OVERRIDES
    # ---------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ticket.monitoring') or _('New')
            if vals.get('owner_id') and vals.get('state', 'draft') == 'draft':
                vals['state'] = 'assigned'
        tickets = super().create(vals_list)
        for t in tickets:
            t._sync_stage_from_state()
            # Post creation notification to chatter
            t.message_post(body=_("Ticket %s created and assigned to %s.") % (t.name, t.assigned_department_id.name))
            if t.owner_id:
                t._notify_assigned_owner()
        return tickets

    def write(self, vals):
        old_owners = {t.id: t.owner_id.id for t in self}
        old_states = {t.id: t.state for t in self} if 'state' in vals else {}
        if 'state' in vals:
            target_state = vals['state']
            stage = self.env['ticket.stage'].search([('state', '=', target_state)], limit=1)
            if stage:
                vals['stage_id'] = stage.id
        res = super().write(vals)
        if 'owner_id' in vals and vals['owner_id']:
            for t in self:
                if t.owner_id and t.owner_id.id != old_owners.get(t.id):
                    t._notify_assigned_owner()
        # Trigger email if state changed directly and not bypassed by action methods
        if 'state' in vals and not self.env.context.get('skip_status_email'):
            for t in self:
                old_s = old_states.get(t.id)
                new_s = vals['state']
                if old_s and old_s != new_s:
                    state_dict = dict(self._fields['state'].selection)
                    old_name = state_dict.get(old_s, old_s)
                    new_name = 'WIP' if new_s == 'in_progress' else ('ON HOLD' if new_s == 'on_hold' else state_dict.get(new_s, new_s))
                    if new_s in ('in_progress', 'on_hold'):
                        t._notify_status_change(old_state_label=old_name, new_state_label=new_name)
                    elif new_s in ('resolved', 'closed'):
                        t._notify_completed()
        return res

    def _sync_stage_from_state(self):
        for t in self:
            stage = self.env['ticket.stage'].search([('state', '=', t.state)], limit=1)
            if stage:
                t.stage_id = stage.id

    def _notify_assigned_owner(self):
        template = self.env.ref('custom_ticket_monitoring.email_template_ticket_assigned', raise_if_not_found=False)
        for ticket in self:
            owner_email = ticket.owner_id.email or ticket.owner_id.partner_id.email
            if not ticket.owner_id or not owner_email:
                continue
            # Ensure assigned owner is added as a follower in chatter
            if ticket.owner_id.partner_id:
                try:
                    ticket.message_subscribe([ticket.owner_id.partner_id.id])
                except Exception as e:
                    _logger.warning("Could not subscribe owner to ticket %s: %s", ticket.name, e)
            # Send assignment email (01 TASK REGISTRATION)
            if template:
                try:
                    email_values = {
                        'email_from': '"Photokina Chemicals Pvt. Ltd." <mis@photokinachem.com>',
                        'reply_to': 'mis@photokinachem.com',
                        'email_to': owner_email,
                        'auto_delete': False,
                    }
                    mail_id = template.sudo().send_mail(
                        ticket.id,
                        force_send=True,
                        raise_exception=True,
                        email_values=email_values,
                    )
                    ticket.message_post(body=_(
                        "📧 <b>Assignment Email Sent</b> to <b>%s</b> &lt;%s&gt;."
                    ) % (ticket.owner_id.name, owner_email))
                except Exception as e:
                    _logger.error("Could not send assignment email for ticket %s: %s", ticket.name, e)
                    ticket.message_post(body=_(
                        "⚠️ <b>Email Notification Failed</b>: %s"
                    ) % str(e))

    def _notify_status_change(self, old_state_label='Assigned', new_state_label='WIP', remarks=None, resume_date=None, progress_pct=None):
        """Send 02 TASK STATUS UPDATE email to assigned owner and requester."""
        template = self.env.ref('custom_ticket_monitoring.email_template_ticket_status_update', raise_if_not_found=False)
        if not template:
            return
        for ticket in self:
            recipients = []
            if ticket.owner_id:
                em = ticket.owner_id.email or ticket.owner_id.partner_id.email
                if em and em not in recipients:
                    recipients.append(em)
            if ticket.user_id:
                em = ticket.user_id.email or ticket.user_id.partner_id.email
                if em and em not in recipients:
                    recipients.append(em)
            if not recipients:
                continue

            email_to_str = ','.join(recipients)
            now_str = fields.Datetime.now().strftime('%d-%m-%Y %H:%M')
            pct = progress_pct or (f"{ticket.progress}%" if ticket.progress else ('50%' if new_state_label == 'WIP' else '25%'))
            rem = remarks or ticket.hold_reason or ticket.escalation_reason or 'Status updated as per operational workflow'
            res_date = resume_date or (ticket.resume_date.strftime('%d-%m-%Y') if ticket.resume_date else 'N/A')

            ctx = {
                'updated_date': now_str,
                'updated_by': self.env.user.name or 'System',
                'old_status': old_state_label,
                'new_status': new_state_label,
                'progress_pct': pct,
                'remarks': rem,
                'resume_date': res_date,
            }
            try:
                email_values = {
                    'email_from': '"Photokina Chemicals Pvt. Ltd." <mis@photokinachem.com>',
                    'reply_to': 'mis@photokinachem.com',
                    'email_to': email_to_str,
                    'auto_delete': False,
                }
                template.sudo().with_context(**ctx).send_mail(
                    ticket.id,
                    force_send=True,
                    raise_exception=True,
                    email_values=email_values,
                )
                ticket.message_post(body=_(
                    "📧 <b>Status Update Email Sent</b> [02 TASK STATUS UPDATE: %s &rarr; %s] to <b>%s</b>."
                ) % (old_state_label, new_state_label, email_to_str))
            except Exception as e:
                _logger.error("Could not send status update email for ticket %s: %s", ticket.name, e)
                ticket.message_post(body=_(
                    "⚠️ <b>Status Email Notification Failed</b>: %s"
                ) % str(e))

    def _notify_completed(self, remarks=None):
        """Send 03 TASK COMPLETED email to assigned owner and requester."""
        template = self.env.ref('custom_ticket_monitoring.email_template_ticket_completed', raise_if_not_found=False)
        if not template:
            return
        for ticket in self:
            recipients = []
            if ticket.owner_id:
                em = ticket.owner_id.email or ticket.owner_id.partner_id.email
                if em and em not in recipients:
                    recipients.append(em)
            if ticket.user_id:
                em = ticket.user_id.email or ticket.user_id.partner_id.email
                if em and em not in recipients:
                    recipients.append(em)
            if not recipients:
                continue

            email_to_str = ','.join(recipients)
            ctx = {
                'remarks': remarks or ticket.requester_feedback or ticket.action_taken or 'Task successfully completed',
            }
            try:
                email_values = {
                    'email_from': '"Photokina Chemicals Pvt. Ltd." <mis@photokinachem.com>',
                    'reply_to': 'mis@photokinachem.com',
                    'email_to': email_to_str,
                    'auto_delete': False,
                }
                template.sudo().with_context(**ctx).send_mail(
                    ticket.id,
                    force_send=True,
                    raise_exception=True,
                    email_values=email_values,
                )
                ticket.message_post(body=_(
                    "📧 <b>Task Completed Email Sent</b> [03 TASK COMPLETED] to <b>%s</b>."
                ) % email_to_str)
            except Exception as e:
                _logger.error("Could not send completed email for ticket %s: %s", ticket.name, e)
                ticket.message_post(body=_(
                    "⚠️ <b>Completion Email Failed</b>: %s"
                ) % str(e))

    def action_send_email_manual(self):
        """Manual button to trigger and test sending the assignment email (01 TASK REGISTRATION)."""
        self.ensure_one()
        if not self.owner_id:
            raise UserError(_("Please assign an Owner before sending email notification."))
        owner_email = self.owner_id.email or self.owner_id.partner_id.email
        if not owner_email:
            raise UserError(_("Assigned Owner %s does not have an email address configured in Users / Contacts.") % self.owner_id.name)
        self._notify_assigned_owner()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Registration Email Dispatched"),
                'message': _("Task Registration Email (01) dispatched to %s (%s). Check Chatter.") % (self.owner_id.name, owner_email),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_send_status_email_manual(self):
        """Manual button to trigger and test sending the status update email (02 TASK STATUS UPDATE)."""
        self.ensure_one()
        current_state = dict(self._fields['state'].selection).get(self.state, self.state)
        new_label = 'WIP' if self.state == 'in_progress' else ('ON HOLD' if self.state == 'on_hold' else current_state)
        self._notify_status_change(old_state_label='Assigned', new_state_label=new_label, remarks=self.hold_reason or 'Manual Status Update Test')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Status Email Dispatched"),
                'message': _("Status Update (02 TASK STATUS UPDATE) notification email dispatched. Check Chatter."),
                'type': 'success',
                'sticky': False,
            }
        }

    # ---------------------------------------------------------
    # LIFECYCLE ACTION METHODS
    # ---------------------------------------------------------
    def action_assign_owner(self):
        self.ensure_one()
        if not self.owner_id:
            raise UserError(_("Please select an Assigned Owner before assigning."))
        self.state = 'assigned'
        self.message_post(body=_("Ticket assigned to %s.") % self.owner_id.name)
        self._notify_assigned_owner()

    def action_accept(self):
        """Step 3: Owner formally acknowledges responsibility within First Response SLA."""
        for ticket in self:
            old_label = 'Draft' if ticket.state == 'draft' else 'Assigned'
            vals = {'state': 'in_progress'}
            if not ticket.first_response_date:
                vals['first_response_date'] = fields.Datetime.now()
            if not ticket.progress:
                vals['progress'] = 25
            ticket.with_context(skip_status_email=True).write(vals)
            ticket.message_post(body=_("Ticket accepted by %s. Work in progress.") % self.env.user.name)
            ticket._notify_status_change(old_state_label=old_label, new_state_label='WIP', remarks='Task accepted. Work in progress.', progress_pct=f"{ticket.progress}%")

    def action_start(self):
        """Start work / in progress."""
        self.action_accept()

    def action_hold(self):
        for ticket in self:
            ticket.with_context(skip_status_email=True).write({'state': 'on_hold'})
            ticket.message_post(body=_("Ticket placed on hold by %s.") % self.env.user.name)
            ticket._notify_status_change(old_state_label='In Progress', new_state_label='ON HOLD', remarks=ticket.hold_reason or 'Ticket placed on hold awaiting dependencies.')

    def action_resume(self):
        for ticket in self:
            vals = {'state': 'in_progress'}
            if not ticket.progress or ticket.progress < 50:
                vals['progress'] = 50
            ticket.with_context(skip_status_email=True).write(vals)
            ticket.message_post(body=_("Ticket resumed to In Progress by %s.") % self.env.user.name)
            ticket._notify_status_change(old_state_label='ON HOLD', new_state_label='WIP', remarks='Task resumed to In Progress.', progress_pct=f"{ticket.progress}%")

    def action_resolve(self):
        """Step 6: Owner documents action taken and marks resolved for requester verification."""
        for ticket in self:
            if not ticket.action_taken:
                raise UserError(_("Please document the 'Action & Corrective Steps Taken' before marking as Resolved."))
            ticket.with_context(skip_status_email=True).write({
                'state': 'resolved',
                'resolved_date': fields.Datetime.now(),
                'progress': 100,
            })
            ticket.message_post(
                body=_("Ticket marked as Resolved by %s. Awaiting requester verification and closure.") % self.env.user.name
            )
            ticket._notify_completed(remarks=ticket.action_taken or 'Task marked as Resolved.')

    def action_verify_close(self):
        """Step 7 & 8: Requester confirms resolution and closes ticket with feedback."""
        for ticket in self:
            ticket.with_context(skip_status_email=True).write({
                'state': 'closed',
                'closed_date': fields.Datetime.now(),
                'progress': 100,
            })
            score_text = dict(self._fields['satisfaction_score'].selection).get(ticket.satisfaction_score, 'Not Rated')
            ticket.message_post(
                body=_("Ticket verified and formally Closed by requester %s. Rating: %s") % (self.env.user.name, score_text)
            )
            ticket._notify_completed(remarks=f"Formally Closed. Rating: {score_text}")

    def action_reopen(self):
        """Requester reopens ticket if issue was not resolved adequately."""
        for ticket in self:
            ticket.write({
                'state': 'reopened',
                'is_reopened': True,
                'reopen_count': ticket.reopen_count + 1,
            })
            ticket.message_post(
                body=_("⚠️ Ticket Reopened by requester %s. Reason: %s") % (self.env.user.name, ticket.reopen_reason or 'No reason provided')
            )

    # ---------------------------------------------------------
    # CRON & AUTOMATED ESCALATION ENGINE
    # ---------------------------------------------------------
    @api.model
    def cron_check_sla_and_escalate(self):
        """Automated background scheduler: scans open tickets, updates SLA, and triggers L2/L3 escalations."""
        open_tickets = self.search([('state', 'not in', ('closed', 'resolved'))])
        now = fields.Datetime.now()

        for ticket in open_tickets:
            # 1. Update SLA breach
            if ticket.resolution_deadline and now > ticket.resolution_deadline:
                ticket.is_resolution_breached = True
                ticket.sla_status = 'breached'
                # L3 Escalation: Breached SLA goes to GM
                if ticket.escalation_level in ('l1', 'l2'):
                    ticket.escalation_level = 'l3'
                    msg = _("🚨 SLA Breached! Ticket escalated to Level 3 (General Manager).")
                    ticket.message_post(body=msg)

            elif ticket.resolution_deadline and ticket.create_date:
                total_secs = (ticket.resolution_deadline - ticket.create_date).total_seconds()
                elapsed_secs = (now - ticket.create_date).total_seconds()
                # L2 Escalation: 75% elapsed without progress goes to HOD
                if total_secs > 0 and (elapsed_secs / total_secs) >= 0.75:
                    ticket.sla_status = 'risk'
                    if ticket.escalation_level == 'l1':
                        ticket.escalation_level = 'l2'
                        msg = _("⚠️ 75% of Resolution SLA elapsed! Ticket escalated to Level 2 (Department HOD).")
                        ticket.message_post(body=msg)
                else:
                    ticket.sla_status = 'within_sla'

            # P1 Critical immediate L4 escalation check if open for more than 1 hour
            if ticket.priority == 'p1' and ticket.create_date:
                age_hours = (now - ticket.create_date).total_seconds() / 3600.0
                if age_hours > 1.0 and ticket.escalation_level != 'l4':
                    ticket.escalation_level = 'l4'
                    msg = _("🔥 Critical P1 issue unresolved for over 1 hour! Escalated to Level 4 (CEO / MD).")
                    ticket.message_post(body=msg)

    # -------------------------------------------------------------------------
    # 15 CORE KPIS MANAGEMENT DASHBOARD API
    # -------------------------------------------------------------------------
    @api.model
    def get_kpi_dashboard_data(self):
        """Returns real-time aggregated metrics for the 15 Core KPIs."""
        if not self.env.user.has_group('custom_ticket_monitoring.group_ticket_dashboard') and not self.env.is_admin():
            raise UserError(_("Access Denied: You do not have permission to view the 15 Core KPIs Management Dashboard."))

        all_tickets = self.search([])
        total_count = len(all_tickets)

        # Status buckets
        closed_tickets = all_tickets.filtered(lambda t: t.state == 'closed')
        resolved_tickets = all_tickets.filtered(lambda t: t.state == 'resolved')
        open_tickets = all_tickets.filtered(lambda t: t.state not in ('closed',))
        active_unresolved = all_tickets.filtered(lambda t: t.state not in ('closed', 'resolved'))

        # Priorities
        p1_tickets = open_tickets.filtered(lambda t: t.priority == 'p1')
        p2_tickets = open_tickets.filtered(lambda t: t.priority == 'p2')
        p3_tickets = open_tickets.filtered(lambda t: t.priority == 'p3')
        p4_tickets = open_tickets.filtered(lambda t: t.priority == 'p4')

        # SLA Statuses
        breached_tickets = open_tickets.filtered(lambda t: t.sla_status == 'breached' or t.is_resolution_breached)
        at_risk_tickets = open_tickets.filtered(lambda t: t.sla_status == 'risk')

        # Completed SLA Compliance %
        completed = all_tickets.filtered(lambda t: t.state in ('resolved', 'closed'))
        if completed:
            within_sla = completed.filtered(lambda t: t.sla_status in ('met', 'within_sla') or (t.resolution_datetime and t.resolution_deadline and t.resolution_datetime <= t.resolution_deadline))
            sla_compliance = round((len(within_sla) / len(completed)) * 100.0, 1)
        else:
            sla_compliance = 100.0

        # Average Resolution Time (Hours)
        with_duration = completed.filtered(lambda t: t.resolution_duration_hours > 0)
        avg_resolution_hours = round(sum(with_duration.mapped('resolution_duration_hours')) / len(with_duration), 1) if with_duration else 0.0

        # Reopening Rate %
        reopened = all_tickets.filtered(lambda t: t.is_reopened or t.reopen_count > 0 or t.state == 'reopened')
        reopen_rate = round((len(reopened) / total_count * 100.0), 1) if total_count else 0.0

        # Customer / Requester Satisfaction Rating (out of 5)
        rated = closed_tickets.filtered(lambda t: t.satisfaction_score and t.satisfaction_score in ('1', '2', '3', '4', '5'))
        avg_satisfaction = round(sum(int(t.satisfaction_score) for t in rated) / len(rated), 1) if rated else 5.0

        # Escalations (L2 HOD, L3 GM, L4 CEO/MD)
        escalated = open_tickets.filtered(lambda t: t.escalation_level in ('l2', 'l3', 'l4'))
        l2_count = len(open_tickets.filtered(lambda t: t.escalation_level == 'l2'))
        l3_count = len(open_tickets.filtered(lambda t: t.escalation_level == 'l3'))
        l4_count = len(open_tickets.filtered(lambda t: t.escalation_level == 'l4'))

        # Operational queues
        pending_verification = len(resolved_tickets)
        on_hold_count = len(open_tickets.filtered(lambda t: t.state == 'on_hold'))
        mis_count = len(open_tickets.filtered(lambda t: t.assigned_department_id.code == 'MIS'))

        # Department Scorecards Breakdown (13 Departments)
        departments = self.env['ticket.department'].search([], order='sequence, name')
        dept_data = []
        for d in departments:
            d_tickets = all_tickets.filtered(lambda t: t.assigned_department_id.id == d.id)
            d_open = d_tickets.filtered(lambda t: t.state not in ('closed',))
            d_breached = d_open.filtered(lambda t: t.sla_status == 'breached' or t.is_resolution_breached)
            d_completed = d_tickets.filtered(lambda t: t.state in ('resolved', 'closed'))
            if d_completed:
                d_within = d_completed.filtered(lambda t: t.sla_status in ('met', 'within_sla') or (t.resolution_datetime and t.resolution_deadline and t.resolution_datetime <= t.resolution_deadline))
                d_sla_rate = round((len(d_within) / len(d_completed)) * 100.0, 1)
            else:
                d_sla_rate = 100.0

            dept_data.append({
                'id': d.id,
                'name': d.name,
                'code': d.code,
                'total': len(d_tickets),
                'open': len(d_open),
                'breached': len(d_breached),
                'sla_rate': d_sla_rate,
                'sla_target': d.sla_target_percent or 95.0,
                'hod_name': d.hod_id.name if d.hod_id else 'Unassigned',
            })

        return {
            'total_tickets': total_count,
            'open_tickets': len(open_tickets),
            'active_unresolved': len(active_unresolved),
            'resolved_tickets': len(resolved_tickets),
            'closed_tickets': len(closed_tickets),
            'breached_tickets': len(breached_tickets),
            'at_risk_tickets': len(at_risk_tickets),
            'p1_tickets': len(p1_tickets),
            'p2_tickets': len(p2_tickets),
            'p3_tickets': len(p3_tickets),
            'p4_tickets': len(p4_tickets),
            'sla_compliance': sla_compliance,
            'avg_resolution_hours': avg_resolution_hours,
            'reopened_tickets': len(reopened),
            'reopen_rate': reopen_rate,
            'avg_satisfaction': avg_satisfaction,
            'rated_count': len(rated),
            'escalated_tickets': len(escalated),
            'l2_count': l2_count,
            'l3_count': l3_count,
            'l4_count': l4_count,
            'pending_verification': pending_verification,
            'on_hold_count': on_hold_count,
            'mis_count': mis_count,
            'departments': dept_data,
        }
