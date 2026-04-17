# Discount Item Sign Alignment Fix - Summary

## Issue Description

When generating AR Invoices from Odoo sales data, there was a **30,800.44 SAR mismatch** between:
- **Input Sheet Total**: 610,849.12 SAR (from raw Odoo data)
- **AR Invoice Total**: 580,048.68 SAR (after sign alignment)

### Root Cause

Odoo exports discount items in a specific format:
- **Quantity**: Negative (e.g., -1.0)
- **Amount**: Positive (e.g., +253.93 SAR)
- **Barcode**: Empty
- **Product Name**: Contains "discount" (e.g., "100.0% discount on total amount")

The AR Invoice generation code had sign alignment logic that correctly flipped these positive amounts to negative (to reduce the invoice total), but the **Input Sheet Total calculation was using raw amounts without this alignment**.

### Data Analysis

- Total affected rows: **49 out of 12,344** (0.4%)
- All 49 rows were discount items with empty barcodes
- Total discount amount: **15,400.22 SAR**
- After sign flip: **-15,400.22 SAR**
- Impact on total: **30,800.44 SAR** (difference between +15,400.22 and -15,400.22)

## Solution Implemented

Updated the Input Sheet Total calculation in two files to apply the same sign alignment logic:

### 1. app.py (Line 178-193)
```python
def calculate_adjusted_amount(row):
    """
    Apply sign alignment for discount items from Odoo.
    Odoo exports discount items with negative qty and positive amt.
    We flip the amount to negative to reduce the invoice total.
    """
    qty = mod.safe_float(row.get("Quantity", 0))
    amt = mod.safe_float(row.get("Subtotal w/o Tax", 0))
    # Sign alignment for discount items: negative qty + positive amt → negative amt
    if qty < 0 and amt > 0:
        return -amt
    return amt

input_total = float(
    integration.line_items.apply(calculate_adjusted_amount, axis=1).sum()
)
```

### 2. test_ar_generation.py (Line 131-142)
Applied the same logic for consistency in test files.

## Verification Results

### Before Fix
```
AR Invoice Lines:        12,344
AR Invoice Total:    580,048.68 SAR
Input Sheet Total:   610,849.12 SAR
Total Match:         ⚠ DIFF 30,800.44
```

### After Fix
```
AR Invoice Lines:        12,344
AR Invoice Total:    580,048.68 SAR
Input Sheet Total:   580,048.68 SAR
Total Match:         ✓ MATCH
```

## Testing

Comprehensive tests passed:
- ✅ Sign alignment correctly handles 49 discount items
- ✅ Input Sheet Total matches AR Invoice Total (0.00 SAR difference)
- ✅ No rows dropped during processing
- ✅ All 12,344 rows accounted for
- ✅ Security scan: No alerts found
- ✅ Code review: All feedback addressed

## Documentation Updates

Updated **README.md** with:
1. Explanation of Odoo discount item format (negative qty + positive amt)
2. Sign alignment logic for discount items
3. Troubleshooting guidance for total amount mismatches
4. Note that both totals now use consistent calculation

## Why This Fix Is Correct

The sign alignment logic is **correct behavior** because:

1. **Discounts should reduce totals**: When a customer receives a 253.93 SAR discount, it should **subtract** from the invoice total, not add to it.

2. **Oracle Fusion expects correct signs**: AR Invoice amounts must have proper signs where:
   - Regular sales = positive amounts
   - Discounts = negative amounts
   - Returns = negative amounts

3. **Odoo format is unconventional**: While Odoo exports discount items with positive amounts, the semantic meaning is that they reduce the total. The negative quantity indicates this reduction.

4. **Consistency across calculations**: Both Input Sheet Total and AR Invoice Total now apply the same logic, ensuring accurate comparison.

## Business Impact

- ✅ Accurate invoice totals matching accounting requirements
- ✅ Proper discount handling in Oracle Fusion
- ✅ No more false mismatch warnings in the UI
- ✅ Clear audit trail with verification reports

## Files Modified

1. `app.py` - Updated Input Sheet Total calculation
2. `test_ar_generation.py` - Updated test Input Sheet Total calculation
3. `README.md` - Added documentation about discount item handling
4. `DISCOUNT_ITEM_FIX_SUMMARY.md` - This summary document

## Related Code

The AR Invoice generation logic (already correct):
- Location: `Odoo-export-FBDA-template.py`, lines 1483-1489
- This code was already correct and is now mirrored in the Input Sheet Total calculation

---

**Date**: 2026-04-17  
**Repository**: MUSTAQ-AHAMMAD/miss-receipt-template  
**Branch**: copilot/fix-invoice-output-mismatch
