# Receipt Generation Issues - Analysis & Fixes

## Date: 2026-04-18

## Issues Identified

### 1. **CRITICAL: AR Invoice and Payment File Mismatch**

**Problem**: The existing AR Invoice file (`AR_Invoice_Import_20260416_024706.csv`) contains data for store "KHMSBNDWOD" while the payment file (`ZAHRAN payment line 5 to 31 March.xlsx`) contains data for store "ZAHRAN".

**Impact**:
- AR Invoice Total: 213,182.52 SAR
- Payment File Total: 702,490.00 SAR
- **Difference: 489,307.48 SAR (70% data loss!)**

**Root Cause**: User is trying to generate receipts from a pre-generated AR Invoice that doesn't match their current payment data.

**Solution**: Generate fresh AR Invoice from ZAHRAN sales + payment files using the "Generate Mode" in the web UI.

**Date-wise Comparison**:
```
Date         AR Total      Payment Total    Difference
2026-03-05    8,151.08      31,311.00      -23,159.92  ⚠ DIFF
2026-03-06    6,074.48      36,866.00      -30,791.52  ⚠ DIFF
2026-03-07    9,442.12      29,577.00      -20,134.88  ⚠ DIFF
... (all dates mismatched)
```

### 2. **Standard Receipt File Organization**

**Current Behavior**: Creates ONE file per (store, date, payment_method) combination
- Example: `Receipt_Cash_ZAHRAN_20260305.csv`
- Example: `Receipt_Mada_ZAHRAN_20260305.csv`

**User Request**: "can you create the one file for one payment method"

**Analysis**: Each receipt file must contain store-specific information:
- Business Unit (different per store)
- Customer Account Number (different per store)
- Customer Site Number (different per store)
- Bank Account Number (different per store AND payment method)

**Current Approach is CORRECT**: Cannot consolidate across stores because each store requires different customer and bank account information.

**However**, we can improve by:
1. Consolidating multiple stores into one file PER PAYMENT METHOD PER DATE (with multiple rows)
2. Adding better file organization and naming

### 3. **Remittance Bank Account Number Mapping**

**Current Logic** (line 1794):
```python
_, bank_acct_number = self.receipt_methods.get_bank_account(store, method)
```

**Potential Issue**: The `get_bank_account()` method searches for store name in the bank account name field. This may fail if:
- Store names don't match exactly
- Store name normalization is inconsistent
- Fallback to method-only lookup returns wrong account

**Verification Needed**:
- Check if `normalise_store()` function properly matches store names
- Verify Receipt_Methods.csv has correct store→bank account mappings
- Add logging to show which bank account is selected for each receipt

### 4. **Miscellaneous Receipt Calculations**

**Current Logic** (lines 1897-1899):
```python
misc_amount = self.bank_charges.calc_misc_amount(total_payment, method, store)
```

**Issues to Check**:
- Verify bank charge percentages in BANK_CHARGES.csv
- Ensure calculation formula is correct: `payment_amount * (charge_rate / 100)`
- Check if charge amounts are being rounded correctly
- Verify OrgId, ReceiptMethodId, and ActivityName are correct for each store/method

## Recommended Fixes

### Fix 1: Improve Standard Receipt File Generation

**Option A: Keep Current (Recommended)**
- Current approach is technically correct
- Each store needs its own receipt due to different business units and accounts
- Just add better logging and validation

**Option B: Consolidate by Payment Method + Date**
- Create one file per (payment_method, date) with MULTIPLE ROWS
- Each row represents a different store
- Risk: Oracle may not accept multi-store receipts

### Fix 2: Add Bank Account Mapping Validation

Add detailed logging to show which bank account is selected:
```python
bank_name, bank_acct_number = self.receipt_methods.get_bank_account(store, method)
vl.add(f"  Store: {store}, Method: {method} → Bank: {bank_name} / Acct: {bank_acct_number}")
```

### Fix 3: Add Misc Receipt Calculation Verification

Add detailed breakdown:
```python
cfg = self.bank_charges.get(method, store)
rate = cfg.get('rate', 0) if cfg else 0
misc_amount = total_payment * (rate / 100)
vl.add(f"  {method} @ {store}: {total_payment:,.2f} × {rate}% = {misc_amount:,.4f}")
```

### Fix 4: Add Comprehensive Validation Report

Create detailed validation showing:
- Date-wise AR totals vs Payment totals
- Receipt totals per payment method
- Bank account mapping details
- Missing/mismatched data

## Instructions for User

### To Fix the Current Issue:

1. **DO NOT use existing AR Invoice file** - it contains wrong data (KHMSBNDWOD store, not ZAHRAN)

2. **Generate fresh AR Invoice** from ZAHRAN data:
   - Go to web UI (http://localhost:5000)
   - Select "Generate Mode" (Sales Lines + Payment Lines)
   - Upload: `ZAHRAN sale line 5 to 31 March.xlsx`
   - Upload: `ZAHRAN payment line 5 to 31 March.xlsx`
   - Set start sequence numbers
   - Click "Run Integration"

3. **This will generate**:
   - Fresh AR Invoice with correct 702,490 SAR total
   - Standard Receipts matching payment totals by date
   - Miscellaneous Receipts for card charges
   - Verification report showing all calculations

4. **Then use AR Invoice Mode** if you need to regenerate receipts later:
   - Upload the freshly generated AR Invoice
   - Upload payment file (optional, for payment method breakdown)
   - Generate receipts

### Verification Steps:

After generation, check verification report for:
- ✓ AR Total matches Payment Total (within 10 SAR rounding)
- ✓ Date-wise totals match
- ✓ Receipt totals per method add up correctly
- ✓ Bank account numbers are store-specific
- ✓ Misc receipts calculated correctly

## Code Improvements Made

1. Enhanced standard receipt logging to show bank account selection
2. Added date-wise comparison in verification report
3. Improved misc receipt calculation logging
4. Added diagnostic script (`debug_receipts.py`) for troubleshooting
5. Better error messages for mismatched data

## Testing Checklist

- [ ] Generate AR Invoice from ZAHRAN sales + payment files
- [ ] Verify AR total matches payment total (702,490 SAR)
- [ ] Verify date-wise totals match
- [ ] Check standard receipts have correct bank accounts per store
- [ ] Verify misc receipts calculate charges correctly
- [ ] Confirm all receipt files are properly organized
- [ ] Review verification report for any warnings

