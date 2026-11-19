# Purchase Approval Module for Odoo 19

The **Purchase Approval** (`purchase_approval`) module implements an approval workflow for Request for Quotations (RFQs) and Purchase Orders in Odoo 19.

---

## 📌 Business Workflow

```
[Create RFQ] 
      ↓
[Select Concerned Authority (Optional)] 
      ↓
[Click: "Send for Purchase Approval"] 
      ↓
(Status: "Waiting Approval" | Activity & Notification sent to Approver)
      ↓
  ┌─────────────────────────┴─────────────────────────┐
  ▼                                                   ▼
[Approver Clicks: "Approve Purchase"]       [Approver Clicks: "Reject"]
  * Approval Details Recorded (Who & When)     * Rejection Reason Dialog
  * Auto-Confirms into Purchase Order          * Status: "Rejected"
  * Requester Notified                         * RFQ can be revised & re-submitted
```

---

## 🚀 Key Features

1. **"Send for Purchase Approval" Action**:
   * Prominently displayed on all Draft and Sent RFQs.
   * Locks the standard "Confirm Order" button for regular purchasers until approval is granted.

2. **Concerned Authority Assignment**:
   * Users can route the purchase to a specific authority (`approver_id`), or leave it open for any member of the Purchase Approver / Manager team.
   * Automatic Odoo Activity scheduled directly on the approver's calendar / dashboard.
   * Chatter notification logged with requester name, target authority, and total amount.

3. **Approval & Rejection by Concerned Authority**:
   * **Approve Purchase**: With one click, validates the approval, records the approving manager, captures timestamp, and confirms the RFQ into an active Purchase Order.
   * **Reject**: Opens a popup modal to record a mandatory reason for rejection (e.g., budget exceeded, alternative vendor preferred). The buyer receives an activity notification and can revise the RFQ.
   * **Recall Request**: The buyer can recall an accidental submission before it is approved.

4. **Dedicated Views & Menus**:
   * Direct submenu under **Purchase -> Orders -> Waiting Approval**.
   * Dedicated top-level section: **Purchase -> Purchase Approvals**.
   * Color-coded status badges on RFQ and PO list views.
   * Search filters for "Waiting My Approval", "Waiting Approval", "Approved", and "Rejected".

5. **Security Roles**:
   * **Purchase / User**: Can create RFQs, designate approver, enter justification, and click "Send for Purchase Approval".
   * **Concerned Authority / Purchase Approver** (`purchase_approval.group_purchase_approver`): Authorized to approve or reject purchase requests.
   * **Purchase / Administrator**: Has full approval authority and configuration access.

---

## 📁 Module File Structure

```
purchase_approval/
├── __init__.py
├── __manifest__.py
├── data/
│   └── mail_activity_type_data.xml
├── models/
│   ├── __init__.py
│   └── purchase_order.py
├── security/
│   ├── purchase_approval_security.xml
│   └── ir.model.access.csv
├── views/
│   ├── purchase_order_views.xml
│   └── purchase_approval_menus.xml
├── wizard/
│   ├── __init__.py
│   ├── purchase_approval_reject_wizard.py
│   └── purchase_approval_reject_wizard_views.xml
└── README.md
```

---

## ⚙️ How to Install in Odoo 19

1. In your browser at `http://localhost:9906`, activate Developer Mode (or go directly to **Apps**).
2. Click **Update Apps List** in the top menu.
3. Search for **Purchase Approval**.
4. Click **Activate** / **Install**.
