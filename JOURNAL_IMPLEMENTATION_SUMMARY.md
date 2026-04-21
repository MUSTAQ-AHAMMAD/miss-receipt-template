# Journal Template Generation - Quick Reference

## What Was Implemented

A new feature that automatically generates Oracle Fusion Journal Import templates from AR Invoice data for TAMARA and TABBY payment method transactions.

## Files Created

1. **JOURNAL_CONFIG.csv** - Business unit configuration
   - Contains: Ledger ID, Journal Source, Journal Category, Currency Code, Segment1
   - Currently configured for: Alqurashi KSA

2. **JOURNAL_ACCOUNT_MAPPING.csv** - Account segment mapping
   - Contains: Payment Method, Business Unit, Debit Account (69011), Credit Account (609012), Segments 1-7
   - Currently configured for: TAMARA and TABBY

3. **JOURNAL_TEMPLATE_GENERATION_GUIDE.md** - Comprehensive documentation
   - Complete usage guide
   - Configuration examples
   - Troubleshooting
   - API reference

## Files Modified

1. **Odoo-export-FBDA-template.py**
   - Added `generate_journal_template()` method
   - Added `save_journal_template()` method
   - Filters AR Invoice data for TAMARA/TABBY transactions
   - Creates balanced debit/credit journal entries

2. **app.py**
   - Integrated journal generation in both AR Invoice and Sales+Payment modes
   - Added configuration parameters: `generate_journal`, `period_name`, `interface_group_id`
   - Added progress tracking for journal generation

3. **README.md**
   - Added journal template generation to core features
   - Listed new configuration files
   - Added configuration settings
   - Updated output file structure

## How to Use

### Web UI (Recommended)

1. Upload your files (AR Invoice or Sales Lines + Payment Lines)
2. Check the "Generate Journal Template" checkbox
3. Configure:
   - Period Name: "Mar-26" (or your period)
   - Interface Group ID: "114" (or unique number)
4. Click "Generate"
5. Download the ZIP file containing `Journal_Import_Template_YYYYMMDD_HHMMSS.csv`

### API

```bash
POST /api/run
Content-Type: multipart/form-data

mode=sales_payment
generate_journal=true
period_name=Mar-26
interface_group_id=114
# ... other parameters
```

## What the Feature Does

1. **Filters Transactions**: Identifies all TAMARA and TABBY transactions from AR Invoice data
2. **Groups Data**: Groups by Transaction Number, Payment Method, and Transaction Date
3. **Creates Entries**: For each transaction, creates:
   - One DEBIT entry with account 69011
   - One CREDIT entry with account 609012
4. **Generates Template**: Creates complete Oracle Fusion Journal Import CSV with all required columns

## Field Mapping (Key Fields)

| Field | Value | Source |
|-------|-------|--------|
| Status Code | "NEW" | Constant |
| Ledger ID | 300000001418025 | JOURNAL_CONFIG.csv |
| Journal Source | "Vend" | JOURNAL_CONFIG.csv |
| Journal Category | "Vend" | JOURNAL_CONFIG.csv |
| Effective Date | Order date | AR Invoice |
| Currency Code | "SAR" | JOURNAL_CONFIG.csv |
| Actual Flag | "A" | Constant |
| Segment1 | "1" | JOURNAL_ACCOUNT_MAPPING.csv |
| Segment2 (Debit) | "69011" | JOURNAL_ACCOUNT_MAPPING.csv |
| Segment2 (Credit) | "609012" | JOURNAL_ACCOUNT_MAPPING.csv |
| Entered Debit Amount | Order total | AR Invoice (debit entry only) |
| Entered Credit Amount | Order total | AR Invoice (credit entry only) |
| REFERENCE1 | Batch name | Auto-generated |
| REFERENCE4 | Journal entry name | Auto-generated |
| Interface Group Identifier | 114 | Configuration parameter |
| Period Name | "Mar-26" | Configuration parameter |
| END | "END" | Constant |

## Example Output

For a TAMARA transaction of 65.22 SAR on 2026-03-30:

**Two entries are created:**

1. **Debit Entry:**
   - Status Code: NEW
   - Segment2: 69011
   - Entered Debit Amount: 65.22
   - Entered Credit Amount: (empty)

2. **Credit Entry:**
   - Status Code: NEW
   - Segment2: 609012
   - Entered Debit Amount: (empty)
   - Entered Credit Amount: 65.22

## Configuration Files Location

Both files must be in the same directory as `app.py`:
```
/home/runner/work/miss-receipt-template/miss-receipt-template/
├── JOURNAL_CONFIG.csv
├── JOURNAL_ACCOUNT_MAPPING.csv
├── app.py
└── Odoo-export-FBDA-template.py
```

## Customization

### To Add New Payment Methods:
Edit `JOURNAL_ACCOUNT_MAPPING.csv` and add a new row with the payment method details.

### To Add New Business Units:
1. Edit `JOURNAL_CONFIG.csv` - add business unit row
2. Edit `JOURNAL_ACCOUNT_MAPPING.csv` - add account mappings for the new business unit

### To Change Account Numbers:
Edit `JOURNAL_ACCOUNT_MAPPING.csv` and update the Debit Account and Credit Account columns.

## Integration Points

The journal generation feature integrates at these points:

1. **After AR Invoice Generation** (Sales+Payment mode)
   - AR Invoice is generated first
   - Then journal template is created from AR data

2. **After AR Invoice Loading** (AR Invoice mode)
   - AR Invoice is loaded from file
   - Then journal template is created from AR data

3. **Before Verification Report** (Both modes)
   - Journal template is generated
   - Statistics are added to verification report

## Statistics Provided

When journal generation is enabled, the UI shows:
- **Journal Entries**: Total number of journal lines (debit + credit)
- **Transactions**: Number of unique transactions (entries ÷ 2)

Example output:
```
Journal Entries: 45 transactions
```

Or if no TAMARA/TABBY transactions found:
```
Journal Entries: 0 (No TAMARA/TABBY transactions)
```

## Testing

To test the feature:

1. **Use existing AR Invoice with TAMARA/TABBY**:
   - Upload `AR_Invoice__AJAWEED_05_31_Mar2026.csv` (or any AR Invoice with TAMARA/TABBY)
   - Enable "Generate Journal Template"
   - Check the output ZIP for `Journal_Import_Template_*.csv`

2. **Use Sales+Payment data**:
   - Upload Sales Lines and Payment Lines that include TAMARA/TABBY payments
   - Enable "Generate Journal Template"
   - Check the generated journal template

## Troubleshooting

### No journal entries generated?
- Check that AR Invoice contains Receipt Method Name = "TAMARA" or "TABBY"
- Verify the configuration files exist and are readable

### Wrong account numbers?
- Edit `JOURNAL_ACCOUNT_MAPPING.csv`
- Update Debit Account and Credit Account columns

### Different business unit?
- Edit both configuration files
- Add/update the business unit details

## Next Steps

The user mentioned they will provide:
1. Sample template with data
2. Account number mapping details
3. Any other major configuration details

Once these are provided, you can:
1. Update `JOURNAL_ACCOUNT_MAPPING.csv` with actual account numbers
2. Add any additional segment mappings
3. Update `JOURNAL_CONFIG.csv` if different business units are needed
4. Adjust field mappings if required

## Summary

✅ **Completed:**
- Journal template generation functionality
- Configuration file structure
- Integration with existing workflows
- Documentation
- Web UI support
- API support

📋 **Ready for:**
- User testing
- Configuration updates based on user's sample data
- Additional payment methods if needed
- Additional business units if needed
