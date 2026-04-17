# Oracle Fusion Financial Integration — AR & Receipt Template Generator

A professional web UI for automating the Oracle Fusion AR Invoice, Standard Receipt, and Miscellaneous Receipt template generation from Odoo POS exports.

## Features

- **Beautiful drag-and-drop UI** — upload up to 6 files directly in the browser
- **Real-time processing log** — live streaming console output as the pipeline runs
- **AR Invoice generation** — full Oracle Fusion AR CSV with all required columns
- **Standard Receipt generation** — per payment method, per store, per date
- **Miscellaneous Receipt generation** — bank charge receipts from card payments
- **Verification Report** — cross-check summary with match quality metrics
- **One-click ZIP download** — all output files packaged for immediate use

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the web server

```bash
python app.py
```

### 3. Open the UI

Navigate to `http://localhost:5000` in your browser.

## Input Files

| File | Required | Description |
|------|----------|-------------|
| Line Items (Sales) | ✅ Required | Odoo POS order line items XLSX/CSV export |
| Payments | ✅ Required | Odoo POS payment methods XLSX/CSV export |
| Customer Metadata | ✅ Required | RCPT mapping data (Bill-to Account, Site, Business Unit) |
| Registers / Stores | ✅ Required | VendHQ register-to-subinventory mapping |
| Receipt Methods | Optional | Bank account / receipt method mapping (auto-loaded if `Receipt_Methods.csv` present) |
| Bank Charges | Optional | Card charge rates for misc receipt generation (auto-loaded if `BANK_CHARGES.csv` present) |

## Configuration

| Setting | Description |
|---------|-------------|
| Organisation Name | Used in the `Comments` column of AR Invoices (e.g. `AlQurashi-KSA`) |
| Transaction Start Seq | BLK- sequence start number — increment from the previous run's report |
| Legacy Segment 1 Start | Flexfield Segment 1 counter (prefix auto-randomised per run) |
| Legacy Segment 2 Start | Flexfield Segment 2 counter (prefix auto-randomised per run) |

## Output Files (inside ZIP)

```
oracle_fusion_output.zip
└── ORACLE_FUSION_OUTPUT/
    ├── AR_Invoices/
    │   └── AR_Invoice_<ORG>_<DATE>.csv
    ├── Receipts/
    │   ├── Cash/
    │   ├── Mada/
    │   ├── Visa/
    │   ├── MasterCard/
    │   └── Misc/
    └── Verification_Report_<TIMESTAMP>.txt
```

## Architecture

```
app.py                          Flask web application (API + SSE streaming)
Odoo-export-FBDA-template.py    Oracle Fusion integration engine (processing logic)
templates/index.html            Rich single-page web UI
requirements.txt                Python dependencies
```