# Oracle Fusion Financial Integration — AR & Receipt Template Generator

A professional web UI for automating Oracle Fusion Standard Receipt and Miscellaneous Receipt template generation from an already-generated AR Invoice CSV.

## Features

- **Single-file upload** — upload only the AR Invoice CSV; reference files are auto-loaded from the server root
- **Real-time processing log** — live streaming console output as the pipeline runs
- **Standard Receipt generation** — per payment method, per store, per date
- **Miscellaneous Receipt generation** — bank charge receipts from card payments
- **Verification Report** — cross-check summary with match quality metrics
- **One-click ZIP download** — all output files packaged for immediate use

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Place reference files in the server root

The following files must be present in the same directory as `app.py` **before** starting the server:

| File | Description |
|------|-------------|
| `RCPT_Mapping_DATA.csv` | Customer metadata (Bill-to Account, Site, Business Unit, Store) |
| `Receipt_Methods.csv` | Bank account / receipt method mapping |
| `BANK_CHARGES.csv` | Card charge rates for misc receipt generation |

### 3. Run the web server

```bash
python app.py
```

### 4. Open the UI

Navigate to `http://localhost:5000` in your browser.

## Input Files

| File | Required | Description |
|------|----------|-------------|
| AR Invoice CSV | ✅ Required | Oracle Fusion AR Invoice CSV (e.g. `AR_Invoice__AJAWEED_05_31_Mar2026.csv`) |
| `RCPT_Mapping_DATA.csv` | Auto-loaded | Customer metadata — must be in server root |
| `Receipt_Methods.csv` | Auto-loaded | Receipt method / bank account mapping — must be in server root |
| `BANK_CHARGES.csv` | Auto-loaded | Card charge rates — must be in server root |

## Configuration

| Setting | Description |
|---------|-------------|
| Organisation Name | Used in processing log and reports (e.g. `AlQurashi-KSA`) |
| Transaction Start Seq | BLK- sequence start number — increment from the previous run's report |
| Legacy Segment 1 Start | Flexfield Segment 1 counter (prefix auto-randomised per run) |
| Legacy Segment 2 Start | Flexfield Segment 2 counter (prefix auto-randomised per run) |

## Output Files (inside ZIP)

```
oracle_fusion_output.zip
└── ORACLE_FUSION_OUTPUT/
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
TEST_REPORT.html                Visual test report (viewable at /test-report)
requirements.txt                Python dependencies
```