/** @odoo-module **/

import { Component, useState, onMounted, onWillStart, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { loadBundle } from "@web/core/assets";

// ============================================================
//  Photokina Dispatch Dashboard — Main OWL Component
// ============================================================
export class DispatchDashboard extends Component {
    static template = "photokina_dispatch.DispatchDashboard";
    static props = ["*"];

    setup() {
        // Read default page from action context if provided (e.g. from top menu)
        const defaultPage = (this.props.action && this.props.action.context && this.props.action.context.default_page) || "analytics";

        // Reactive state
        this.state = useState({
            currentPage: defaultPage,
            period: "all",
            search: "",
            kpi: {
                total: 0,
                on_time: 0,
                late: 0,
                on_time_pct: 0,
                late_pct: 0,
            },
            tableData: [],
            delayBuckets: [],
            loading: false,
            lastRefresh: "",
            currentDate: "",
        });

        // Chart canvas refs
        this.donutChartRef = useRef("donutChart");
        this.barChartRef = useRef("barChart");
        this._donutChart = null;
        this._barChart = null;
        this._searchTimer = null;

        onWillStart(async () => {
            try {
                await loadBundle("web.chartjs_lib");
            } catch (e) {
                console.warn("[DispatchDashboard] Could not load chartjs_lib bundle:", e);
            }
        });

        onMounted(() => {
            this._setCurrentDate();
            // Data fetched once on module open (no auto-refresh polling)
            this.loadData();
        });

        onWillUnmount(() => {
            if (this._searchTimer) clearTimeout(this._searchTimer);
            this._destroyCharts();
        });
    }

    // ------------------------------------------------------------------ //
    //  Date helper
    // ------------------------------------------------------------------ //
    _setCurrentDate() {
        const opts = { weekday: "long", day: "numeric", month: "long", year: "numeric" };
        this.state.currentDate = new Date().toLocaleDateString("en-IN", opts);
    }

    // ------------------------------------------------------------------ //
    //  Data loading (on module open or manual button click)
    // ------------------------------------------------------------------ //
    async loadData() {
        this.state.loading = true;
        try {
            // Fetch KPIs
            const kpi = await rpc("/photokina_dispatch/kpi_data", {
                period: this.state.period,
            });
            if (kpi) {
                this.state.kpi = kpi;
            }

            if (this.state.currentPage === "analytics") {
                const buckets = await rpc("/photokina_dispatch/delay_buckets", {
                    period: this.state.period,
                });
                this.state.delayBuckets = buckets || [];
                // Render charts after DOM updates
                setTimeout(() => this._renderCharts(), 120);
            } else {
                const rows = await rpc("/photokina_dispatch/delivery_table", {
                    period: this.state.period,
                    search: this.state.search,
                });
                this.state.tableData = rows || [];
            }

            this.state.lastRefresh = new Date().toLocaleTimeString("en-IN");
        } catch (err) {
            console.error("[DispatchDashboard] loadData error:", err);
        } finally {
            this.state.loading = false;
        }
    }

    // ------------------------------------------------------------------ //
    //  Charts (Chart.js)
    // ------------------------------------------------------------------ //
    _destroyCharts() {
        if (this._donutChart) {
            this._donutChart.destroy();
            this._donutChart = null;
        }
        if (this._barChart) {
            this._barChart.destroy();
            this._barChart = null;
        }
    }

    _renderCharts() {
        const ChartClass = window.Chart;
        if (!ChartClass) {
            console.warn("[DispatchDashboard] Chart.js not available yet");
            return;
        }

        const donutEl = this.donutChartRef.el;
        const barEl = this.barChartRef.el;
        if (!donutEl || !barEl) return;

        this._destroyCharts();

        const kpi = this.state.kpi;
        const buckets = this.state.delayBuckets;

        // ---- Donut chart ----
        this._donutChart = new ChartClass(donutEl, {
            type: "doughnut",
            data: {
                labels: ["On-Time", "Late"],
                datasets: [{
                    data: [kpi.on_time || 0, kpi.late || 0],
                    backgroundColor: ["#22c55e", "#ef4444"],
                    borderWidth: 3,
                    borderColor: "#fff",
                    hoverOffset: 6,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "68%",
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ` ${ctx.label}: ${ctx.parsed} orders`,
                        },
                    },
                },
            },
        });

        // ---- Bar chart ----
        const bucketColors = {
            "0 Days":   "#22c55e",
            "1-3 Days": "#eab308",
            "4-7 Days": "#3b82f6",
            "8-14 Days":"#ec4899",
            "15+ Days": "#f97316",
        };

        const labels = buckets.map((b) => b.label);
        const counts = buckets.map((b) => b.count);
        const colors = labels.map((l) => bucketColors[l] || "#667eea");

        this._barChart = new ChartClass(barEl, {
            type: "bar",
            data: {
                labels,
                datasets: [{
                    label: "Dispatches",
                    data: counts,
                    backgroundColor: colors,
                    borderRadius: 6,
                    barThickness: 36,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ` ${ctx.parsed.y} orders`,
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(0,0,0,0.05)" },
                        ticks: { precision: 0 },
                    },
                    x: {
                        grid: { display: false },
                    },
                },
            },
        });
    }

    // ------------------------------------------------------------------ //
    //  Event handlers
    // ------------------------------------------------------------------ //
    switchPage(page) {
        if (this.state.currentPage !== page) {
            this.state.currentPage = page;
            this._destroyCharts();
            this.loadData();
        }
    }

    onPeriodChange(ev) {
        this.state.period = ev.target.value;
        this.loadData();
    }

    onSearchChange() {
        clearTimeout(this._searchTimer);
        this._searchTimer = setTimeout(() => this.loadData(), 400);
    }

    // ------------------------------------------------------------------ //
    //  CSV export
    // ------------------------------------------------------------------ //
    exportCSV() {
        const rows = this.state.tableData;
        if (!rows.length) {
            alert("No data to export.");
            return;
        }
        const headers = ["#", "Order No", "Company Name", "Proposed Date", "Actual Dispatch Date", "Days Delay", "Is Late"];
        const lines = [headers.join(",")];
        rows.forEach((r, i) => {
            lines.push([
                i + 1,
                `"${r.order_no}"`,
                `"${r.company}"`,
                r.proposed_date,
                `"${r.actual_date}"`,
                r.days_delay,
                r.is_late ? "Yes" : "No",
            ].join(","));
        });
        const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `photokina_dispatch_report_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }
}

// Register as a client action
registry.category("actions").add("photokina_dispatch.DispatchDashboard", DispatchDashboard);
