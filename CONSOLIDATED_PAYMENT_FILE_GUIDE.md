# Consolidated Payment File Generation Guide

## Overview

The system now generates **two types of receipt files**:

1. **Per-Method Files** (existing): Separate CSV files for each payment method
   - `Receipt_Cash.csv`
   - `Receipt_Mada.csv`
   - `Receipt_Visa.csv`
   - `Receipt_MasterCard.csv`

2. **Consolidated File** (NEW): Single CSV file with ALL payment methods merged
   - `Receipt_ALL_CONSOLIDATED.csv`

## Why Use the Consolidated File?

### Benefits

✅ **Single Source of Truth**: All payment methods in one file
✅ **Easier Reconciliation**: Compare totals against bank deposits
✅ **Simplified Upload**: Upload one file instead of multiple files
✅ **Complete Data**: No risk of missing a payment method
✅ **Validation Built-In**: Automatic checks ensure no data loss

### When to Use

- **Oracle Fusion Import**: Upload the consolidated file for complete receipt data
- **Reconciliation**: Match total against bank statements
- **Auditing**: Review all payment methods in one place
- **Reporting**: Generate comprehensive payment reports

## File Structure

### Output Directory Layout

```
ORACLE_FUSION_OUTPUT/
├── AR_Invoices/
│   └── AR_Invoice_<ORG>_<DATE>.csv
└── Receipts/
    ├── Receipt_ALL_CONSOLIDATED.csv    ← NEW! All payment methods merged
    ├── Cash/
    │   └── Receipt_Cash.csv
    ├── Mada/
    │   └── Receipt_Mada.csv
    ├── Visa/
    │   └── Receipt_Visa.csv
    └── MasterCard/
        └── Receipt_MasterCard.csv
```

### Consolidated File Location

📁 **Path**: `Receipts/Receipt_ALL_CONSOLIDATED.csv`
📄 **Format**: Standard Oracle Fusion receipt import format
🔢 **Columns**: Same as per-method files (ReceiptNumber, ReceiptMethod, Amount, etc.)

## Validation Features

### 1. Total Match Validation

The system automatically validates that:
```
Consolidated Total = Sum of Per-Method Totals
```

**Example Output:**
```
═══ CONSOLIDATED FILE VALIDATION ═══
  Consolidated total:           645,149.00 SAR
  Per-method total:             645,149.00 SAR
  Difference:                         0.00 SAR
  Status: ✓ MATCH - Totals are accurate
```

### 2. Negative Amount Detection

The system detects and flags any negative amounts:

**Example Output:**
```
Payment Method Breakdown in Consolidated File:
  Cash             150 rows        245,123.45 SAR  ✓
  Mada             120 rows        198,765.32 SAR  ✓
  Visa              80 rows        132,456.78 SAR  ✓
  MasterCard        60 rows         68,803.45 SAR  ⚠ 2 NEGATIVE AMOUNTS!
```

⚠️ **If you see negative amounts**, this indicates:
- Possible data quality issue in source files
- Refunds or returns that need special handling
- Calculation error that needs investigation

### 3. Per-Method Breakdown

Shows detailed breakdown by payment method:
- **Count**: Number of receipt rows
- **Total**: Total amount for that method
- **Status**: ✓ (OK) or ⚠ (has issues)

## Verification Report

The verification report now includes a dedicated section for consolidated file validation:

### Sample Verification Report

```
════════════════════════════════════════════════════════════════════════════
  CONSOLIDATED FILE CREATED: Receipt_ALL_CONSOLIDATED.csv
    Total rows: 410
    Total amount: 645,149.00 SAR
    Payment methods included: ['Cash', 'Mada', 'MasterCard', 'Visa']

  ═══ CONSOLIDATED FILE VALIDATION ═══
    Consolidated total:           645,149.00 SAR
    Per-method total:             645,149.00 SAR
    Difference:                         0.00 SAR
    Status: ✓ MATCH - Totals are accurate

  Payment Method Breakdown in Consolidated File:
    Cash             150 rows        245,123.45 SAR  ✓
    Mada             120 rows        198,765.32 SAR  ✓
    Visa              80 rows        132,456.78 SAR  ✓
    MasterCard        60 rows         68,803.45 SAR  ✓
════════════════════════════════════════════════════════════════════════════
```

## How to Use

### 1. Generate Files (Web UI)

1. Upload your sales and payment files
2. Click "Generate"
3. Download the output ZIP file

### 2. Extract and Verify

1. Extract the ZIP file
2. Navigate to `ORACLE_FUSION_OUTPUT/Receipts/`
3. Find `Receipt_ALL_CONSOLIDATED.csv`
4. Open the verification report and check validation section

### 3. Import to Oracle Fusion

**Option A: Use Consolidated File**
- Upload `Receipt_ALL_CONSOLIDATED.csv` to Oracle Fusion
- Single upload includes all payment methods

**Option B: Use Per-Method Files**
- Upload each payment method file separately
- Useful if you need to process methods independently

## Troubleshooting

### Issue: Negative Amounts in Cash

**Symptom:**
```
Cash             150 rows         -1,234.56 SAR  ⚠ NEGATIVE TOTAL!
```

**Possible Causes:**
1. Returns or refunds processed as negative payments
2. Data quality issue in source payment file
3. Calculation error in payment aggregation

**Solution:**
1. Review source payment file for negative amounts
2. Check if returns should be processed separately
3. Contact support if issue persists

### Issue: Total Mismatch

**Symptom:**
```
Consolidated total:           645,149.00 SAR
Per-method total:             640,000.00 SAR
Difference:                     5,149.00 SAR
Status: ⚠ MISMATCH - Please review
```

**Possible Causes:**
1. Payment method not included in per-method files
2. Rounding differences
3. Data processing error

**Solution:**
1. Check "Payment Method Breakdown" section
2. Verify all payment methods are listed
3. Review per-method files for completeness
4. Regenerate if necessary

### Issue: Missing Payment Methods

**Symptom:**
```
Payment methods included: ['Cash', 'Mada']
```

Expected: Cash, Mada, Visa, MasterCard

**Solution:**
1. Check source payment file contains all methods
2. Verify payment method names are correct
3. Review "PAYMENT METHOD PROCESSING BREAKDOWN" in verification report

## Best Practices

### ✅ DO

- **Always review verification report** before importing
- **Check for negative amounts** in the breakdown
- **Verify total matches** between consolidated and per-method
- **Keep both file types** for backup and reconciliation
- **Use consolidated file** for Oracle Fusion import

### ❌ DON'T

- **Don't ignore negative amount warnings** - investigate the cause
- **Don't skip verification** - always check the report
- **Don't modify files manually** - regenerate if changes needed
- **Don't import without validation** - ensure totals match

## FAQ

### Q: Do I still get per-method files?
**A:** Yes! Both per-method files AND consolidated file are generated.

### Q: Which file should I import to Oracle Fusion?
**A:** Use `Receipt_ALL_CONSOLIDATED.csv` for a single import of all payment methods, OR use per-method files if you need to process methods separately.

### Q: What if I see negative amounts?
**A:** Review your source payment file. Negative amounts may indicate returns, refunds, or data quality issues.

### Q: How do I know if the file is accurate?
**A:** Check the verification report for:
- ✓ MATCH status
- No negative amount warnings
- All expected payment methods included

### Q: Can I disable per-method files?
**A:** No, both file types are always generated to ensure flexibility.

### Q: What payment methods are included?
**A:** Cash, Mada, Visa, MasterCard, and any other methods defined in your Receipt_Methods.csv file (BNPL methods like TABBY/TAMARA are excluded as they don't generate receipts).

## Technical Details

### File Format

**Columns** (Standard Oracle Fusion format):
```
ReceiptNumber, ReceiptMethod, ReceiptDate, BusinessUnit,
CustomerAccountNumber, CustomerSite, Amount, Currency,
RemittanceBankAccountNumber, AccountingDate
```

### Aggregation Logic

1. Payments aggregated by (Store, Date, Method)
2. One row per unique combination
3. All rows merged into consolidated file
4. Totals validated against per-method files

### Validation Tolerance

- **Total Match**: ±0.01 SAR
- **Negative Detection**: Any amount < 0
- **Row Count**: Exact match required

## Support

If you encounter issues:

1. Check verification report for warnings
2. Review source payment file for data quality
3. Regenerate files with fresh data
4. Create GitHub issue with:
   - Verification report
   - Error symptoms
   - Sample data (if shareable)

---

**Last Updated**: 2026-04-21
**Feature Version**: v2.6.0
**Related Documentation**: RECEIPT_GENERATION_GUIDE.md, ENHANCED_VERIFICATION_GUIDE.md
