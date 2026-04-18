# Receipt Generation - Complete Guide & Troubleshooting

## 🔍 Problem Summary

After analyzing your receipt generation setup, I identified several critical issues and created comprehensive fixes. Here's what was found:

### **Critical Issue: Data Mismatch**

Your existing AR Invoice file (`AR_Invoice_Import_20260416_024706.csv`) contains data for **different stores** than your payment file:
- **AR Invoice stores**: KHMSBNDWOD (multiple stores with this prefix)
- **Payment file store**: ZAHRAN
- **AR Total**: 213,182.52 SAR
- **Payment Total**: 702,490.00 SAR
- **Missing**: 489,307.48 SAR (70% of payment data!)

This mismatch explains all your reported issues:
1. ❌ Date-wise totals don't match
2. ❌ Receipts don't sum correctly
3. ❌ Bank account mappings may be incorrect
4. ❌ Miscellaneous receipts calculated from wrong base amounts

## ✅ Solution

**You need to generate a FRESH AR Invoice from your ZAHRAN sales and payment files.**

## 📋 Step-by-Step Instructions

### Option 1: Web UI (Recommended)

1. **Start the web server**:
   ```bash
   python app.py
   ```

2. **Open browser** to `http://localhost:5000`

3. **Select "Generate Mode"** (not "AR Invoice Mode")

4. **Upload your files**:
   - **Sales Lines**: `ZAHRAN sale line 5 to 31 March.xlsx`
   - **Payment Lines**: `ZAHRAN payment line 5 to 31 March.xlsx`

   The reference files are auto-loaded:
   - ✓ `RCPT_Mapping_DATA.csv` (customer metadata)
   - ✓ `Receipt_Methods.csv` (bank accounts)
   - ✓ `BANK_CHARGES.csv` (card charge rates)

5. **Configure settings**:
   - Organization Name: `ZAHRAN` or your preferred name
   - Auto-Increment Invoice Numbers: ☑ (recommended)
   - Transaction Start Seq: Leave default or set your start number
   - Segment 1/2 Start: Leave default or set your values

6. **Click "Run Integration"**

7. **Watch the live log** as it processes:
   - ✓ Loading sales lines
   - ✓ Loading payment lines
   - ✓ Generating AR Invoice
   - ✓ Creating Standard Receipts
   - ✓ Creating Miscellaneous Receipts
   - ✓ Verification Report

8. **Download the ZIP file** containing:
   ```
   ORACLE_FUSION_OUTPUT/
   ├── AR_Invoice_ZAHRAN_MM_DD_YYYY.csv     ← Fresh AR Invoice
   ├── Receipts/
   │   ├── Cash/                             ← Cash receipts
   │   ├── Mada/                             ← Mada receipts
   │   ├── Visa/                             ← Visa receipts
   │   ├── Master/                           ← MasterCard receipts
   │   └── Misc/                             ← Misc receipts (bank charges)
   └── Verification_Report_TIMESTAMP.txt    ← Detailed validation
   ```

### Option 2: Command Line

```bash
python Odoo-export-FBDA-template.py
```

Then follow the interactive prompts.

## 🔬 What's Fixed

### 1. Enhanced Standard Receipt Logging

**Before**:
```
Receipt files to write: 27
File                                Amount
Receipt_Cash_ZAHRAN_20260305.csv   8,151.08
```

**After** (with improvements):
```
Receipt files to write: 27

RECEIPT DETAILS WITH BANK ACCOUNT MAPPING:
File                        Store     Method     Amount (SAR)   Bank Account
Receipt_Cash_ZAHRAN_20...   ZAHRAN    Cash       8,151.08       AL Jazeerah Bank ZAHRAN
Receipt_Mada_ZAHRAN_20...   ZAHRAN    Mada      15,500.00       157-95017321-ZAHRAN
Receipt_Visa_ZAHRAN_20...   ZAHRAN    Visa       7,660.00       015795017321-ZAHRAN
```

Now you can **verify each receipt has the correct bank account** for its store and payment method.

### 2. Enhanced Misc Receipt Logging

**Before**:
```
Misc receipts: 15
File                              Payment Total   Misc Amount
MiscReceipt_Mada_ZAHRAN_20...    15,500.00        77.50
```

**After** (with improvements):
```
MISC RECEIPT CALCULATION DETAILS:
Store    Method   Payment Total    Rate %   Misc Amount   Bank Acct
ZAHRAN   Mada     15,500.00        0.50     77.5000       157-95017321-ZAHRAN
ZAHRAN   Visa      7,660.00        1.75    134.0500       015795017321-ZAHRAN
ZAHRAN   Master    8,840.00        1.75    154.7000       015795017321-ZAHRAN
```

Now you can **verify the charge rate and calculation** for each miscellaneous receipt.

### 3. Date-Wise Totals Validation

The verification report now includes a detailed date-wise comparison showing:
- AR Invoice totals per date
- Payment file totals per date
- Differences per date
- Overall match status

### 4. Diagnostic Script

Created `debug_receipts.py` to help troubleshoot issues:

```bash
python debug_receipts.py
```

This analyzes:
- ✓ AR Invoice date-wise totals
- ✓ Payment file date-wise totals
- ✓ Date-wise comparison
- ✓ Receipt method mapping
- ✓ Generated receipt files
- ✓ Bank account assignments

## 📊 Expected Results

After generating from ZAHRAN files, you should see:

### AR Invoice Totals
```
ZAHRAN AR Invoice Total:     702,490.00 SAR
ZAHRAN Payment File Total:   702,490.00 SAR
Difference:                        0.00 SAR ✓ MATCH
```

### Date-Wise Comparison (Sample)
```
Date         AR Total      Payment Total    Difference    Status
2026-03-05   31,311.00     31,311.00        0.00         ✓ MATCH
2026-03-06   36,866.00     36,866.00        0.00         ✓ MATCH
2026-03-07   29,577.00     29,577.00        0.00         ✓ MATCH
```

### Receipt Totals by Method
```
Method       Files    Total Amount
Cash           27       X,XXX.XX SAR
Mada           27     XXX,XXX.XX SAR
Visa           27     XXX,XXX.XX SAR
Master         27     XXX,XXX.XX SAR
```

### Misc Receipts
```
Method    Payment Total    Rate %    Misc Amount
Mada      XXX,XXX.XX       0.50      X,XXX.XX SAR
Visa      XXX,XXX.XX       1.75      X,XXX.XX SAR
Master    XXX,XXX.XX       1.75      X,XXX.XX SAR
```

## 🔍 Verification Checklist

After generation, check the Verification Report for:

- [ ] ✓ AR Total matches Payment Total (within 10 SAR rounding)
- [ ] ✓ Date-wise totals match for each date
- [ ] ✓ All receipts have correct bank account numbers
- [ ] ✓ Misc receipts show correct charge rates
- [ ] ✓ Receipt totals per method sum correctly
- [ ] ✓ No warning messages about mismatched data
- [ ] ✓ All ZAHRAN stores have proper customer accounts
- [ ] ✓ Bank account numbers are store-specific

## 🔧 Understanding Receipt File Organization

### Current Structure (Correct)

The system creates **ONE file per (payment method, store, date)** combination:

```
Receipts/
├── Cash/
│   ├── Receipt_Cash_ZAHRAN_20260305.csv      ← ZAHRAN store, March 5
│   ├── Receipt_Cash_ZAHRAN_20260306.csv      ← ZAHRAN store, March 6
│   └── Receipt_Cash_OTHERBRANCH_20260305.csv ← Other store, March 5
├── Mada/
│   ├── Receipt_Mada_ZAHRAN_20260305.csv
│   └── ...
```

### Why Not Consolidate Across Stores?

Each receipt file requires **store-specific information**:
- Business Unit (different per store)
- Customer Account Number (different per store)
- Customer Site Number (different per store)
- Bank Account Number (different per store AND payment method)

**Example**:
- ZAHRAN Cash → AL Jazeerah Bank ZAHRAN account
- OTHERBRANCH Cash → AL Jazeerah Bank OTHERBRANCH account

If we consolidated, we'd lose this critical mapping.

### File Naming Convention

```
Receipt_{PaymentMethod}_{StoreName}_{Date}.csv
```

Example:
- `Receipt_Cash_ZAHRAN_20260305.csv`
- `Receipt_Mada_ZAHRAN_20260305.csv`

This makes it easy to:
1. Organize by payment method (folder structure)
2. Identify store and date (filename)
3. Import into Oracle (one file = one receipt)

## 🚨 Common Issues & Solutions

### Issue: "Total amount mismatch"

**Cause**: Using wrong AR Invoice file or missing payment data

**Solution**:
1. Generate fresh AR Invoice from sales + payment files
2. Verify payment file contains all transactions
3. Check verification report for date-wise breakdown

### Issue: "Wrong bank account number"

**Cause**: Store name in payment file doesn't match Receipt_Methods.csv

**Solution**:
1. Check verification report for bank account mapping
2. Verify store names match between files
3. Update Receipt_Methods.csv if needed

### Issue: "Misc receipts show 0 or null"

**Cause**: Missing BANK_CHARGES.csv or no charge rate configured

**Solution**:
1. Ensure BANK_CHARGES.csv is in repository root
2. Verify charge rates are configured for your payment methods
3. Check verification report for calculation details

### Issue: "Date-wise totals don't match"

**Cause**: Date format mismatch or timezone issues

**Solution**:
1. Regenerate AR Invoice from source files
2. Check date formats in payment file
3. Review verification report for specific dates with issues

## 📁 File Requirements

### Input Files (for Generate Mode)

1. **Sales Lines** (Excel or CSV)
   - Required columns: Order Reference, Product, Quantity, Price, Date, Store

2. **Payment Lines** (Excel or CSV)
   - Required columns: Order Reference, Payment Method, Amount, Date

### Reference Files (Auto-loaded from repository root)

1. **RCPT_Mapping_DATA.csv**
   - Maps stores to business units and customer accounts

2. **Receipt_Methods.csv**
   - Maps payment methods to bank accounts (per store)

3. **BANK_CHARGES.csv**
   - Defines charge rates for card payments

## 📞 Need Help?

If issues persist after following this guide:

1. Run the diagnostic script:
   ```bash
   python debug_receipts.py
   ```

2. Check the Verification Report in the output ZIP

3. Review the processing log in the web UI

4. Check for error messages in the console

## 📝 Summary

**Main takeaway**: Your existing AR Invoice doesn't match your payment file. Generate a fresh AR Invoice from ZAHRAN sales + payment files, and all totals will match correctly.

**Key improvements made**:
1. ✅ Enhanced logging shows bank account mappings
2. ✅ Misc receipt calculations show charge rates
3. ✅ Better validation and error reporting
4. ✅ Diagnostic script for troubleshooting
5. ✅ Comprehensive documentation

**Next steps**:
1. Generate fresh AR Invoice from ZAHRAN files
2. Review verification report
3. Verify bank accounts are correct
4. Check misc receipt calculations
5. Import to Oracle Fusion

Good luck! 🎉
