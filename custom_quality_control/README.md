# QA / QC Management for Purchase & Manufacturing (Odoo 19)

A comprehensive Quality Assurance and Quality Control (QA/QC) module for Odoo 19 Community Edition tailored for incoming raw material purchases and finished manufactured batches.

---

## Key Features & Business Workflows

### 1. Purchase Validation -> Dynamic Routing to Quality Control
* **Validation Popup Notification**: Touching/clicking **Validate** on an incoming receipt automatically intercepts the receipt and moves the products into **Quality Control** (`WH/Quality Control`).
* **Immediate Feedback**: A modal dialog pops up titled **"Order Successfully Sent to QA/QC!"** summarizing:
  * Receipt reference and destination QC staging location.
  * Assurance that products have **NOT** been added to inventory stock.
  * Direct one-click button: **"Open QA/QC Inspection"** to jump straight into testing.
* Products are held in Quality Control until approved by the quality team.

### 2. Manufacturing Completion -> Quality Control
* When a Manufacturing Order (MO) is completed (`Mark as Done`), finished goods are routed into Quality Control.
* Finished goods are quarantined from inventory until the QA/QC team tests and passes the batch.
* Inspection checks are created automatically with the batch/lot details.

### 3. Dynamic Chemical Parameters & On-the-Fly Customization
* **Distinct Parameters per Chemical Category**:
  * **Resins / Polymers** (e.g., `Photopolymer Resin PK-100`):
    * Physical Appearance (`Clear Amber Viscous Liquid`)
    * Viscosity (`2500 - 3500 cP`)
    * Solid Content / Non-Volatile (`98.0 - 100.0 %`)
    * Specific Gravity (`1.10 - 1.15 g/cm³`)
    * Color (`Amber / Light Yellow`)
    * pH Value (`6.5 - 7.5`)
    * Packaging & UN Label Audit
  * **Solvents / Esters** (e.g., `Solvent Ethyl Acetate (Pure Grade)`):
    * Physical Appearance (`Clear Colorless Volatile Liquid`)
    * Purity / Assay (`99.5 - 100.0 %`)
    * Moisture Content (`0.00 - 0.05 %`)
    * Specific Gravity (`0.898 - 0.902 g/cm³`)
    * Odor (`Characteristic fruity ester odor`)
    * Color (`Max 10 APHA`)
    * Packaging & Flammability Labeling Audit
  * **Pigments / Inks / Pastes**:
    * Dispersion/Fineness, Solid Content %, Moisture %, Color Match, Packaging.
  * **General Chemicals**:
    * Appearance, Purity %, Specific Gravity, pH Value, Packaging.
* **Completely Dynamic**:
  * Quality analysts can **add, remove, or modify parameters on the fly** for any inspection batch.
  * Auto-evaluates **Pass / Fail** as numerical test results are entered against min/max limits.

### 4. Approval & Dynamic Inventory Release
* **Release Only After Passing**:
  * Clicking **Pass (Approved)**:
    * Automatically validates and moves the approved products from `WH/Quality Control` into regular stock inventory (`WH/Stock` or any chosen warehouse location).
  * **Dynamic Warehouse & Location**:
    * The destination warehouse and storage location (rack, shelf, bin, tank) can be changed dynamically on the check or via the **Release to Dynamic Storage Location** wizard.
* **Fail (Reject)**:
  * Material is blocked and stays segregated.
  * One-click transfer to **Quarantine** (`WH/Quarantine`) or scrap.

### 5. Visibility & Navigation
* **Sidebar App**: Directly accessible in the left navigation sidebar under the exact name **QA/QC**.
* **Smart Buttons & Badges**:
  * Purchase Receipts: Shows status badge (`QC Required on Validation` in draft/ready -> `Under QA/QC Testing` in done -> `All Passed (In Stock)`).
  * Smart button links directly to the QA/QC checks.
* **Certificate of Analysis (COA) Report**: Printable lab certificate with tested parameters, specifications, measured values, and signature blocks.
