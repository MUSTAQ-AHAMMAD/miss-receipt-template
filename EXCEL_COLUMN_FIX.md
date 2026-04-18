# Excel Column Value Discrepancy - Fix Summary

## Issue Report Date: 2026-04-18

## User's Reported Issue

User reported: "picking completely wrong value not picking up my system value which is causing the descripency"

The user noticed that when comparing the generated AR Invoice Excel with their input Excel sheet, the system was picking the wrong column values.

---

## Root Cause Analysis

### The Problem

The column mapping configuration in `Odoo-export-FBDA-template.py` (lines 650-664) was **incorrectly prioritizing** the tax-inclusive column:

**OLD (WRONG) Priority:**
```python
"Subtotal w/o Tax": [
    "Order Lines/Subtotal",          # Tax-inclusive (PRIMARY) ❌
    "Subtotal",                      # Tax-inclusive fallback
    "Order Lines/Subtotal w/o Tax",  # Tax-exclusive (3rd choice) ❌
    ...
]
```

### What This Caused

When the system read the Excel file with both columns present:
- `Order Lines/Subtotal` = 702,413.13 SAR (WITH tax)
- `Order Lines/Subtotal w/o Tax` = 610,849.12 SAR (WITHOUT tax)

The system would:
1. **Pick the WRONG column** (`Order Lines/Subtotal` with tax)
2. Read 702,413.13 SAR instead of 610,849.12 SAR
3. Apply minimal adjustment (1.000109×) to match payment total
4. Create confusion when users compared values

### Why This Was Wrong

The correct accounting logic should be:
1. Read **base amounts** (without tax)
2. Calculate **adjustment factor** = payment total ÷ sales total
3. Apply factor to scale amounts to match actual cash collected

By reading amounts that already included tax, the adjustment factor became nearly 1.0, which:
- Made the calculation meaningless
- Created discrepancies when users checked Excel values
- Did not properly reflect the payment adjustment logic

---

## The Fix

### Changes Made

#### 1. **Odoo-export-FBDA-template.py** (lines 654-661)

**NEW (CORRECT) Priority:**
```python
"Subtotal w/o Tax": [
    "Order Lines/Subtotal w/o Tax",  # Tax-exclusive (PRIMARY) ✅
    "Order Lines/Subtotal excl tax",
    "Order Lines/Price excl. tax",
    "Subtotal w/o Tax",
    "Order Lines/Subtotal",          # Tax-inclusive (fallback only) ✅
    "Subtotal",                      # Generic fallback
]
```

**Updated Comments:**
```python
# Line item amounts should be read WITHOUT tax, then adjusted by payment factor.
# This ensures we're working with base amounts and the payment adjustment
# correctly scales them to match actual cash collected (which includes tax).
# The system will calculate: adjusted_amount = base_amount * (payment_total / sales_total)
```

#### 2. **README.md** (line 193)

Updated documentation:
```markdown
- **Column Used**: Reads from "Subtotal w/o Tax" (base amounts), then applies payment adjustment factor
- The adjustment factor = (total payments / total sales) ensures AR totals match actual cash collected
```

---

## Impact & Results

### Before Fix (WRONG)
```
Excel Column Read:     "Order Lines/Subtotal" (WITH tax)
Sales Total Read:      702,413.13 SAR
Payment Total:         702,490.00 SAR
Adjustment Factor:     1.000109 ← Nearly 1.0, meaningless!
User Experience:       "Picking wrong value from Excel" ❌
```

### After Fix (CORRECT)
```
Excel Column Read:     "Order Lines/Subtotal w/o Tax" (WITHOUT tax)
Sales Total Read:      610,849.12 SAR
Payment Total:         702,490.00 SAR
Adjustment Factor:     1.150022 ← Meaningful 15% scale-up!
User Experience:       Correct values from Excel ✅
```

---

## Verification

### Test Results

Using the Zaharan test files:
```
Sales (WITHOUT tax):   610,849.12 SAR ← Now correctly reads this
Sales (WITH tax):      702,413.13 SAR ← Previously (wrongly) read this
Payment total:         702,490.00 SAR

OLD adjustment factor: 1.000109 (wrong - barely any adjustment)
NEW adjustment factor: 1.150022 (correct - 15% scale-up for tax)
```

### Column Mapping Verified

```
Current "Subtotal w/o Tax" priority:
  1. "Order Lines/Subtotal w/o Tax"  ← PRIMARY (correct!) ✅
  2. "Order Lines/Subtotal excl tax"
  3. "Order Lines/Price excl. tax"
  4. "Subtotal w/o Tax"
  5. "Order Lines/Subtotal"          ← Fallback only
  6. "Subtotal"
```

---

## Technical Explanation

### Why This Fix Is Correct

1. **Proper Base Amounts**: System now reads amounts WITHOUT tax, which are the true base values

2. **Meaningful Adjustment**: The payment adjustment factor (1.15×) now properly reflects:
   - Tax addition (~15% in KSA)
   - Any discounts or adjustments
   - Final amounts match actual cash collected

3. **User Clarity**: When users check Excel:
   - System reads from "Subtotal w/o Tax" column (visible and verifiable)
   - Values match what users expect to see
   - No more "picking wrong value" confusion

4. **Accounting Accuracy**:
   - AR Invoice amounts = base amounts × payment adjustment factor
   - Final AR total still matches payment total exactly
   - All verification checks continue to pass

---

## Files Changed

1. **Odoo-export-FBDA-template.py**
   - Lines 650-661: Fixed column mapping priority
   - Changed from tax-inclusive to tax-exclusive as primary

2. **README.md**
   - Line 193: Updated documentation
   - Explained correct column usage and adjustment factor

---

## Commit Details

**Commit Hash**: `2a2fbc6`
**Branch**: `claude/fix-excel-value-discrepancy`
**Message**: "Fix Excel column mapping: prioritize tax-exclusive amounts"

---

## User Action Required

### For Existing Users

1. **Pull Latest Code**:
   ```bash
   git pull origin main
   ```

2. **Regenerate Reports**:
   - Re-upload your Excel files
   - Generate AR Invoice again
   - System will now read correct column values

3. **Verify**:
   - Check verification report
   - AR total should still match payment total
   - Column resolution log will show "Order Lines/Subtotal w/o Tax" as selected

### What to Expect

- **Same Accuracy**: AR totals still match payment totals (within <10 SAR)
- **Correct Values**: System now reads from tax-exclusive column
- **Better Adjustment**: Adjustment factor is meaningful (~1.15× for 15% tax)
- **No Confusion**: Values match what you see in Excel

---

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Column Read** | "Subtotal" (WITH tax) ❌ | "Subtotal w/o Tax" ✅ |
| **Sales Total** | 702,413.13 SAR | 610,849.12 SAR |
| **Adjustment Factor** | 1.000109 (meaningless) | 1.150022 (meaningful) |
| **User Experience** | "Wrong values from Excel" | Correct values ✅ |
| **AR Accuracy** | Matches payments ✅ | Matches payments ✅ |

**Status**: ✅ **FIXED**
**Impact**: Resolves user's "picking wrong value" complaint
**Accuracy**: Maintained - AR totals still match payment totals
**Improvement**: System now reads correct Excel column and applies meaningful adjustment factor

---

**Document Created**: 2026-04-18
**Fix Applied**: 2026-04-18
**Related Commit**: 2a2fbc6
