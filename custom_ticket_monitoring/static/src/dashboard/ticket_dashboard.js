/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

export class TicketKpiDashboard extends Component {
    static template = "custom_ticket_monitoring.TicketKpiDashboard";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            loading: true,
            kpis: {
                total_tickets: 0,
                open_tickets: 0,
                active_unresolved: 0,
                resolved_tickets: 0,
                closed_tickets: 0,
                breached_tickets: 0,
                at_risk_tickets: 0,
                p1_tickets: 0,
                p2_tickets: 0,
                p3_tickets: 0,
                p4_tickets: 0,
                sla_compliance: 100.0,
                avg_resolution_hours: 0.0,
                reopened_tickets: 0,
                reopen_rate: 0.0,
                avg_satisfaction: 5.0,
                rated_count: 0,
                escalated_tickets: 0,
                l2_count: 0,
                l3_count: 0,
                l4_count: 0,
                pending_verification: 0,
                on_hold_count: 0,
                mis_count: 0,
                departments: [],
            },
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call("ticket.monitoring", "get_kpi_dashboard_data", []);
            this.state.kpis = data;
        } catch (error) {
            console.error("Failed to load KPI dashboard data:", error);
        } finally {
            this.state.loading = false;
        }
    }

    openAction(name, domain = [], context = {}) {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "ticket.monitoring",
            name: name,
            views: [
                [false, "list"],
                [false, "kanban"],
                [false, "form"],
                [false, "pivot"],
            ],
            domain: domain,
            context: context,
        });
    }

    openAllTickets() {
        return this.openAction("All Operational Tickets", []);
    }

    openOpenTickets() {
        return this.openAction("Open Active Tickets", [["state", "!=", "closed"]]);
    }

    openBreachedTickets() {
        return this.openAction("Overdue / SLA Breached Tickets", [
            ["sla_status", "=", "breached"],
            ["state", "not in", ["closed", "resolved"]],
        ]);
    }

    openP1Tickets() {
        return this.openAction("Critical (P1) Tickets", [
            ["priority", "=", "p1"],
            ["state", "!=", "closed"],
        ]);
    }

    openReopenedTickets() {
        return this.openAction("Reopened Tickets", [
            "|",
            ["is_reopened", "=", true],
            ["reopen_count", ">", 0],
        ]);
    }

    openPendingVerification() {
        return this.openAction("Pending Verification", [["state", "=", "resolved"]]);
    }

    openOnHoldTickets() {
        return this.openAction("On Hold Tickets", [["state", "=", "on_hold"]]);
    }

    openEscalatedTickets() {
        return this.openAction("Escalated Tickets", [
            ["escalation_level", "in", ["l2", "l3", "l4"]],
            ["state", "!=", "closed"],
        ]);
    }

    openMisTickets() {
        return this.openAction("MIS Department Tickets", [
            ["assigned_department_id.code", "=", "MIS"],
        ]);
    }

    openPivot() {
        return this.actionService.doAction("custom_ticket_monitoring.action_ticket_monitoring_dashboard");
    }

    openGraph() {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "ticket.monitoring",
            name: "Ticket Analytics Graphs",
            views: [
                [false, "graph"],
                [false, "pivot"],
                [false, "list"],
            ],
        });
    }

    openDepartmentScorecards() {
        return this.actionService.doAction("custom_ticket_monitoring.action_ticket_department");
    }

    createTicket() {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "ticket.monitoring",
            name: "New Operational Ticket",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openDepartmentTickets(dept) {
        return this.openAction(`${dept.name} Tickets`, [["assigned_department_id", "=", dept.id]], {
            default_assigned_department_id: dept.id,
        });
    }
}

registry.category("actions").add("ticket_kpi_dashboard", TicketKpiDashboard);
