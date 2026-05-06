# Visual Comparison: Before vs After Fix

## Problem
The user reported that "calculated charges should go under these columns" (referring to the Debit/Credit columns in the journal template).

## Before Fix ❌

When generating journal template for a TAMARA transaction of 199.00 SAR:

```
Journal Entries Generated: 2 lines only

Entry 1: Segment2=3020044 | Entered Debit Amount=199.00  | Entered Credit Amount=(empty)
Entry 2: Segment2=5000104 | Entered Debit Amount=(empty) | Entered Credit Amount=199.00

Result: Charges were calculated (13.42 SAR) but NOT written to the journal template
```

**Issue**: Charges were logged to console but missing from the CSV output file.

## After Fix ✅

Same TAMARA transaction of 199.00 SAR now generates:

```
Journal Entries Generated: 4 lines (Payment + Charges)

PAYMENT ENTRIES:
Entry 1: Segment2=3020044 | Entered Debit Amount=199.00  | Entered Credit Amount=(empty)
Entry 2: Segment2=5000104 | Entered Debit Amount=(empty) | Entered Credit Amount=199.00

CHARGE ENTRIES:
Entry 3: Segment2=3020044 | Entered Debit Amount=13.42   | Entered Credit Amount=(empty)
Entry 4: Segment2=5000104 | Entered Debit Amount=(empty) | Entered Credit Amount=13.42

Result: Charges are now properly written to the journal template CSV file
```

**Charge Calculation**: 1.5 (Fixed) + (199.00 × 5.99%) = 1.5 + 11.92 = 13.42 SAR

## Column Mapping

The charges now correctly appear in these columns:

| Column Name                | Account (Segment2) | Entry Type | Amount Example |
|---------------------------|--------------------|------------|----------------|
| Entered Debit Amount      | 3020044            | Payment    | 199.00         |
| Entered Credit Amount     | 5000104            | Payment    | 199.00         |
| **Entered Debit Amount**  | **3020044**        | **CHARGE** | **13.42**      |
| **Entered Credit Amount** | **5000104**        | **CHARGE** | **13.42**      |

## Complete Example from Test Output

### Batch: MAR-31: TAMARA Vend -MAKKAH-20260331

```csv
Status Code,Ledger ID,Effective Date,Journal Source,Journal Category,Currency Code,Segment1,Segment2,Segment3,Segment4,Entered Debit Amount,Entered Credit Amount,REFERENCE1 (Batch Name)
NEW,300000001418025,2026/03/31,Vend,Vend,SAR,01,3020044,46,1401,199.00,,MAR-31: TAMARA Vend -MAKKAH-20260331
NEW,300000001418025,2026/03/31,Vend,Vend,SAR,01,5000104,46,1401,,199.00,MAR-31: TAMARA Vend -MAKKAH-20260331
NEW,300000001418025,2026/03/31,Vend,Vend,SAR,01,3020044,46,1401,13.4201,,MAR-31: TAMARA Vend -MAKKAH-20260331
NEW,300000001418025,2026/03/31,Vend,Vend,SAR,01,5000104,46,1401,,13.4201,MAR-31: TAMARA Vend -MAKKAH-20260331
```

### Key Points:
- **Lines 1-2**: Payment amount (199.00 SAR)
- **Lines 3-4**: Charge amount (13.42 SAR) - **NOW PRESENT!**
- Same account numbers (3020044, 5000104) used for both payment and charges
- Balanced entries: Total Debits = Total Credits = 212.42 SAR

## Impact on Oracle Fusion

When imported into Oracle Fusion, each transaction will now correctly show:
- **Payment Amount**: 199.00 SAR (what the customer paid)
- **Service Charges**: 13.42 SAR (what TAMARA charges for the service)
- **Total**: 212.42 SAR (properly tracked in the accounting system)

Without this fix, the 13.42 SAR in charges would be lost and not recorded in Oracle Fusion.

## Test Results Summary

✅ Tested with MAKKAH payment file (259 TABBY/TAMARA transactions):
- Before: 518 entries (2 per transaction) - **Charges missing**
- After: 1,036 entries (4 per transaction) - **Charges included**
- All entries balanced (Total Debits = Total Credits)
- Charges follow same debit/credit logic as payments
