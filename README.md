# Oracle Fusion Financial Integration — AR & Receipt Template Generator

A professional web UI for automating Oracle Fusion Standard Receipt and Miscellaneous Receipt template generation from an already-generated AR Invoice CSV or directly from Odoo sales data.

## Features

### Core Features
- **Single-file upload** — upload only the AR Invoice CSV; reference files are auto-loaded from the server root
- **Dual mode operation**:
  - **AR Invoice Mode**: Upload existing AR Invoice CSV → generate receipts
  - **Generate Mode**: Sales Lines + Payment Lines → generate AR Invoice + receipts
- **Real-time processing log** — live streaming console output as the pipeline runs
- **Standard Receipt generation** — per payment method, per store, per date
- **Miscellaneous Receipt generation** — bank charge receipts from card payments
- **Verification Report** — cross-check summary with match quality metrics
- **One-click ZIP download** — all output files packaged for immediate use

### New Advanced Features ✨

#### 1. **Upload Log Management System** 🆕
- Complete tracking of receipt uploads to Oracle Fusion
- Detailed API request and response logging
- Upload status dashboard with filtering
- Comprehensive error reporting with row-level precision
- Retry tracking and history
- Export upload logs to text reports
- Accessible via "Upload Logs" page in web UI
- REST API for programmatic access

#### 2. **Automatic Invoice Number Sequencing**
- Automatically persists last used invoice numbers
- Auto-continues from previous run without manual input
- Stores transaction numbers, segment 1, and segment 2 sequences
- Enable via "Auto-Increment Invoice Numbers" checkbox in UI

#### 3. **CSV Merger Tool**
- Merge multiple AR Invoice CSV files into one consolidated file
- Automatic duplicate detection and removal
- **Comprehensive Accuracy Report**: Detailed before/after comparison showing:
  - Per-file statistics (rows, transactions, amounts)
  - Duplicate detection with transaction-level details
  - Cross-file duplicate tracking (shows which files contain same transactions)
  - Amount verification (tracks exactly what was removed)
  - Accuracy metrics and verification status
- Accessible via "Merge AR Invoices" mode in web UI
- Command-line: `python csv_merger.py output.csv file1.csv file2.csv ...`

#### 4. **Comprehensive Report Generator**
- **AR Invoice Analysis**: SKU breakdown, discount tracking, store summaries
- **Sub-Inventory Report**: Invoice-wise and total breakdown by sub-inventory
- Detailed validation and accuracy metrics
- JSON and formatted text output
- Accessible via "Generate Reports" mode in web UI
- Command-line: `python report_generator.py ar <ar_invoice.csv>`

#### 5. **Data Validation Tool**
- Validates AR Invoice accuracy and consistency
- Checks SKU/discount item handling
- Verifies amount/quantity sign consistency
- Transaction number sequence validation
- Cross-checks with source data
- Command-line: `python data_validator.py ar <ar_invoice.csv> [source_file]`

## Quick Start

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
| AR Invoice CSV | ✅ Required (AR Mode) | Oracle Fusion AR Invoice CSV (e.g. `AR_Invoice__AJAWEED_05_31_Mar2026.csv`) |
| Sales Lines CSV/XLSX | ✅ Required (Generate Mode) | Odoo sales line items export |
| Payment Lines CSV/XLSX | ✅ Required (Generate Mode) | Odoo payment lines export |
| `RCPT_Mapping_DATA.csv` | Auto-loaded | Customer metadata — must be in server root |
| `Receipt_Methods.csv` | Auto-loaded | Receipt method / bank account mapping — must be in server root |
| `BANK_CHARGES.csv` | Auto-loaded | Card charge rates — must be in server root |

## Configuration

| Setting | Description |
|---------|-------------|
| Organisation Name | Used in processing log and reports (e.g. `AlQurashi-KSA`) |
| Auto-Increment Invoice Numbers | Automatically continue from last run's invoice numbers |
| Transaction Start Seq | BLK- sequence start number (auto-populated if auto-increment enabled) |
| Legacy Segment 1 Start | Flexfield Segment 1 counter (prefix auto-randomised per run) |
| Legacy Segment 2 Start | Flexfield Segment 2 counter (prefix auto-randomised per run) |

## Output Files (inside ZIP)

```
oracle_fusion_output.zip
└── ORACLE_FUSION_OUTPUT/
    ├── AR_Invoice_<ORG>_<DATE>.csv  (if Generate mode)
    ├── Receipts/
    │   ├── Cash/
    │   ├── Mada/
    │   ├── Visa/
    │   ├── MasterCard/
    │   └── Misc/
    └── Verification_Report_<TIMESTAMP>.txt
```

## Command-Line Tools

### CSV Merger
```bash
python csv_merger.py merged_output.csv file1.csv file2.csv file3.csv
```

### Report Generator
```bash
# AR Invoice Analysis
python report_generator.py ar ar_invoice.csv [metadata.csv]

# Sub-Inventory Report
python report_generator.py subinv ar_invoice.csv metadata.csv

# Receipts Analysis
python report_generator.py receipts receipts_directory/
```

### Data Validator
```bash
# Validate AR Invoice
python data_validator.py ar ar_invoice.csv [source_file]

# Validate Receipts
python data_validator.py receipts receipts_directory/ [ar_invoice.csv]
```

## Key Improvements

### Accuracy Enhancements
- ✅ Input row count == Output AR row count (no dropped rows)
- ✅ Empty barcode/SKU treated correctly as discount items
- ✅ Amount and quantity signs always consistent
- ✅ Unit Selling Price always positive
- ✅ Transaction numbers sequential with no gaps
- ✅ Automatic duplicate detection

### Discount Item Handling
- Items with empty barcode/SKU → `Memo Line Name = "Discount Item"`, `Inventory Item Number = ""`
- Items with "discount" in product name → treated as discount items
- Regular items maintain barcode in `Inventory Item Number`
- **Odoo Discount Format**: Discount items from Odoo have negative quantity (-1.0) and positive amount
- **Sign Alignment**: System automatically converts positive discount amounts to negative to reduce invoice totals
- This ensures accurate accounting where discounts reduce the total amount

### Invoice Sequence Management
- Automatically tracks last used invoice numbers
- Persists to `invoice_sequence.json`
- Next run continues seamlessly
- Manual override still available

## Architecture

```
app.py                          Flask web application (API + SSE streaming)
Odoo-export-FBDA-template.py    Oracle Fusion integration engine (processing logic)
csv_merger.py                   CSV file merger utility
report_generator.py             Comprehensive report generator
data_validator.py               Data validation and accuracy checker
invoice_sequence.json           Auto-generated invoice sequence tracker
templates/index.html            Rich single-page web UI
TEST_REPORT.html                Visual test report (viewable at /test-report)
requirements.txt                Python dependencies
```

## Troubleshooting

### Invoice numbers not auto-incrementing
- Ensure "Auto-Increment Invoice Numbers" checkbox is enabled
- Check that `invoice_sequence.json` exists and is writable
- Review verification report for "Invoice sequence persisted" message

### Total amount mismatch
- **IMPORTANT**: AR Invoice totals are based on **payment totals** (what was actually paid), not sales totals
- This ensures perfect accuracy with bank deposits and financial reconciliation
- The system automatically adjusts each invoice's line items proportionally to match its payment total
- For orders with 100% discount but payment (tips/service charges), a "Service Charge" line is added
- Input Sheet Total = sum of all payments (authoritative source)
- AR Invoice Total = payment-adjusted amounts (matches Input Sheet Total exactly)
- **Column Used**: Reads from "Subtotal w/o Tax" (base amounts), then applies payment adjustment factor
- The adjustment factor = (total payments / total sales) ensures AR totals match actual cash collected
- If using Odoo exports, ensure your payment sheet accurately reflects actual cash collected
- Use data validator: `python data_validator.py ar ar_invoice.csv source_file.xlsx`
- Review verification report for detailed breakdown

### Missing SKUs causing issues
- Items without barcodes are automatically treated as discount items
- Check product names for "discount" keyword
- Use report generator to analyze SKU distribution
- Review AR Invoice report for discount/regular item breakdown

## API Endpoints

- `POST /api/session` - Create new processing session
- `POST /api/run` - Start integration pipeline
- `GET /api/stream/<sid>` - Server-sent events stream for progress
- `GET /api/status/<sid>` - Get session status
- `GET /api/download/<sid>` - Download output ZIP
- `POST /api/merge-csv` - Merge multiple AR Invoice CSVs
- `POST /api/generate-report` - Generate comprehensive reports

### Upload Log Management APIs

- `GET /api/upload-logs/history` - Get upload history with filters (status, type, limit)
- `GET /api/upload-logs/details/<id>` - Get detailed upload info including API logs
- `GET /api/upload-logs/stats` - Get summary statistics
- `POST /api/upload-logs/export` - Export logs to text report
- `POST /api/upload-logs/test-upload` - Test upload functionality (mock mode)
- `POST /api/upload-logs/batch-upload` - Upload all receipts from directory

### Web Pages

- `/` - Main application interface
- `/upload-logs` - Upload logs dashboard
- `/test-report` - View test report

See [UPLOAD_LOG_MANAGEMENT_GUIDE.md](UPLOAD_LOG_MANAGEMENT_GUIDE.md) for detailed API documentation.

## License

Proprietary - Internal Use Only