# Journal Template Generation Guide

## Overview

The Journal Template Generation feature automatically creates Oracle Fusion Journal Import templates from AR Invoice data. This feature is specifically designed to handle TAMARA and TABBY payment method transactions that require journal entries for proper accounting.

## Key Features

- **Automatic TAMARA/TABBY Detection**: Filters transactions by payment method
- **Debit/Credit Entry Generation**: Creates balanced journal entries with proper account mapping
- **Configurable Account Mapping**: Uses separate CSV files for account segment configuration
- **Business Unit Support**: Supports multiple business units with different ledgers
- **Batch Management**: Automatically organizes entries into batches

## Configuration Files

### 1. JOURNAL_CONFIG.csv

Contains business unit-specific journal configuration:

| Column | Description | Example |
|--------|-------------|---------|
| Business Unit | Name of the business unit | Alqurashi KSA |
| Ledger ID | Oracle ledger identifier | 300000001418025 |
| Journal Source | Journal source code (case sensitive) | Vend |
| Journal Category | Journal category code (case sensitive) | Vend |
| Currency Code | Currency code | SAR |
| Segment1 | Default Segment1 value | 1 |

**Example:**
```csv
Business Unit,Ledger ID,Journal Source,Journal Category,Currency Code,Segment1
Alqurashi KSA,300000001418025,Vend,Vend,SAR,1
```

### 2. JOURNAL_ACCOUNT_MAPPING.csv

Contains payment method-specific account mappings:

| Column | Description | Example |
|--------|-------------|---------|
| Payment Method | Payment method name (TAMARA/TABBY) | TAMARA |
| Business Unit | Business unit name | Alqurashi KSA |
| Debit Account | Debit account number | 69011 |
| Credit Account | Credit account number | 609012 |
| Segment1-7 | Account segment values | 1,,,,,, |

**Example:**
```csv
Payment Method,Business Unit,Debit Account,Credit Account,Segment1,Segment2,Segment3,Segment4,Segment5,Segment6,Segment7
TAMARA,Alqurashi KSA,69011,609012,1,,,,,,
TABBY,Alqurashi KSA,69011,609012,1,,,,,,
```

## How It Works

### Process Flow

1. **Data Loading**: Loads AR Invoice data with payment methods
2. **Filtering**: Identifies TAMARA and TABBY transactions
3. **Grouping**: Groups transactions by:
   - Transaction Number (Order Ref)
   - Payment Method
   - Transaction Date
4. **Entry Generation**: For each transaction, creates:
   - One DEBIT entry (using Debit Account from mapping)
   - One CREDIT entry (using Credit Account from mapping)
5. **Template Creation**: Generates complete Oracle Fusion Journal Import template

### Field Mapping

The following fields are automatically populated:

| Field | Source | Example |
|-------|--------|---------|
| Status Code | Constant | "NEW" |
| Ledger ID | JOURNAL_CONFIG.csv | 300000001418025 |
| Effective Date of Transaction | Transaction Date from AR Invoice | 2026/03/30 |
| Journal Source | JOURNAL_CONFIG.csv | "Vend" |
| Journal Category | JOURNAL_CONFIG.csv | "Vend" |
| Currency Code | JOURNAL_CONFIG.csv | "SAR" |
| Journal Entry Creation Date | Transaction Date from AR Invoice | 2026/03/30 |
| Actual Flag | Constant | "A" |
| Segment1 | JOURNAL_ACCOUNT_MAPPING.csv | "1" |
| Segment2 | Debit/Credit Account from mapping | "69011" or "609012" |
| Entered Debit Amount | Transaction amount (for debit entry) | 65.22 |
| Entered Credit Amount | Transaction amount (for credit entry) | 65.22 |
| Converted Debit Amount | Same as Entered Debit Amount | 65.22 |
| Converted Credit Amount | Same as Entered Credit Amount | 65.22 |
| REFERENCE1 (Batch Name) | Auto-generated | "M27 Tamara sample - 1" |
| REFERENCE4 (Journal Entry Name) | Auto-generated | "Journal Import 1 sample - 1" |
| Interface Group Identifier | Configuration parameter | 114 |
| Period Name | Configuration parameter | "Mar-26" |
| END | Constant | "END" |

All other fields are left empty as per Oracle Fusion requirements.

## Usage

### Via Web UI

1. **Upload Files**: Upload Sales Lines and Payment Lines files (in Sales+Payment mode) or AR Invoice (in AR Invoice mode)
2. **Enable Journal Generation**: Check the "Generate Journal Template" checkbox
3. **Configure Parameters**:
   - **Period Name**: e.g., "Mar-26" (default)
   - **Interface Group ID**: e.g., "114" (default)
4. **Run**: Click "Generate" to process

### Via API

```python
POST /api/run
{
    "mode": "sales_payment",
    "generate_journal": "true",
    "period_name": "Mar-26",
    "interface_group_id": "114",
    ...
}
```

### Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `generate_journal` | Enable journal template generation | "false" |
| `period_name` | Oracle period name (e.g., "Mar-26") | "Mar-26" |
| `interface_group_id` | Unique identifier for the file | "114" |

## Output

### File Name
```
Journal_Import_Template_YYYYMMDD_HHMMSS.csv
```

Example: `Journal_Import_Template_20260421_153045.csv`

### File Location
The journal template file is saved in the output directory:
```
ORACLE_FUSION_OUTPUT/
├── Journal_Import_Template_20260421_153045.csv
├── AR_Invoice_ALQURASHI_KSA_05_31_Mar2026.csv (if generated)
├── Receipts/
│   ├── Cash/
│   ├── Mada/
│   └── ...
└── Verification_Report_20260421_153045.txt
```

### Example Output Structure

For a transaction with amount 65.22:

**Debit Entry:**
```csv
Status Code: NEW
Ledger ID: 300000001418025
Effective Date of Transaction: 2026/03/30
...
Segment1: 1
Segment2: 69011
...
Entered Debit Amount: 65.22
Entered Credit Amount:
...
```

**Credit Entry:**
```csv
Status Code: NEW
Ledger ID: 300000001418025
Effective Date of Transaction: 2026/03/30
...
Segment1: 1
Segment2: 609012
...
Entered Debit Amount:
Entered Credit Amount: 65.22
...
```

## Statistics

The system provides the following statistics:
- **Journal Entries**: Total number of journal entry lines generated
- **Transactions**: Number of unique transactions (entries ÷ 2)
- **0 (No TAMARA/TABBY transactions)**: Shown when no qualifying transactions found

## Troubleshooting

### No Journal Entries Generated

**Issue**: The output shows "0 (No TAMARA/TABBY transactions)"

**Solutions**:
1. Verify AR Invoice contains transactions with Receipt Method Name = "TAMARA" or "TABBY"
2. Check that payment methods are spelled correctly (case insensitive)
3. Review the AR Invoice CSV to ensure data was loaded properly

### Missing Account Mapping

**Issue**: Warning message "No account mapping found for [PAYMENT_METHOD]"

**Solutions**:
1. Ensure `JOURNAL_ACCOUNT_MAPPING.csv` exists in the server root
2. Verify the payment method exists in the mapping file
3. Check Business Unit matches exactly (case sensitive)

### Configuration File Not Found

**Issue**: Error loading configuration files

**Solutions**:
1. Ensure both `JOURNAL_CONFIG.csv` and `JOURNAL_ACCOUNT_MAPPING.csv` are in the server root
2. Verify file names are spelled correctly (case sensitive)
3. Check file permissions (must be readable)

## Advanced Configuration

### Adding New Payment Methods

To add support for additional payment methods:

1. Edit `JOURNAL_ACCOUNT_MAPPING.csv`
2. Add a new row with:
   - Payment Method name (e.g., "STC PAY")
   - Business Unit
   - Debit Account number
   - Credit Account number
   - Segment values

3. Save the file

4. The system will automatically recognize the new payment method

### Adding New Business Units

To support additional business units:

1. Edit `JOURNAL_CONFIG.csv`
2. Add a new row with business unit details
3. Edit `JOURNAL_ACCOUNT_MAPPING.csv`
4. Add account mappings for the new business unit
5. Save both files

### Customizing Batch Names

Batch names follow this pattern:
```
M27 {PaymentMethod} sample - {BatchNumber}
```

Journal Entry names follow:
```
Journal Import 1 sample - {EntryNumber}
```

To customize these patterns, modify the `generate_journal_template()` function in `Odoo-export-FBDA-template.py`.

## Best Practices

1. **Unique Interface Group IDs**: Use a different Interface Group Identifier for each file to avoid conflicts
2. **Period Name**: Ensure the period name matches the Oracle GL period (e.g., "Mar-26" for March 2026)
3. **Account Validation**: Verify account numbers in the mapping file are valid in Oracle
4. **Regular Backups**: Keep backups of configuration files
5. **Test First**: Test with a small dataset before processing large batches

## Integration with Existing Workflows

The journal template generation integrates seamlessly with:

- **AR Invoice Generation**: Automatically processes AR Invoice data
- **Receipt Generation**: Works alongside standard and misc receipt generation
- **Verification Reports**: Journal statistics included in verification reports
- **ZIP Download**: Journal template included in the output ZIP file

## API Reference

### generate_journal_template()

```python
def generate_journal_template(
    self,
    journal_config_path: str = "",
    account_mapping_path: str = "",
    period_name: str = "Mar-26",
    interface_group_id: int = 114,
) -> pd.DataFrame
```

**Parameters:**
- `journal_config_path`: Path to business unit configuration (defaults to JOURNAL_CONFIG.csv in repo root)
- `account_mapping_path`: Path to account mapping configuration (defaults to JOURNAL_ACCOUNT_MAPPING.csv in repo root)
- `period_name`: Oracle GL period name (e.g., "Mar-26")
- `interface_group_id`: Unique identifier for this journal import file

**Returns:**
- DataFrame with complete journal template (empty if no TAMARA/TABBY transactions found)

### save_journal_template()

```python
def save_journal_template(self, journal_df: pd.DataFrame)
```

**Parameters:**
- `journal_df`: DataFrame containing journal entries

**Side Effects:**
- Saves CSV file to output directory with timestamp
- Prints confirmation message

## Version History

- **v1.0**: Initial journal template generation feature
  - Support for TAMARA and TABBY payment methods
  - Configurable account mapping
  - Business unit configuration
  - Automatic batch organization
