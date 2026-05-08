# Fix: Separate Positive and Negative Amounts in Daily Aggregation

## Issue

When aggregating transactions by day for charge calculation, positive and negative amounts (refunds) were being netted together BEFORE calculating charges. This resulted in incorrect charge calculations that missed refund charge reversals.

### Example Problem

**March 13, 2026 - TABBY:**
- Positive transactions: 10 × various amounts = 2,417 SAR
- Negative (refund): 1 × -199 SAR

**Incorrect behavior (before fix):**
- Net amount: 2,417 - 199 = 2,218 SAR
- Single charge: 1.00 + (2,218 × 0.05) = 111.90 SAR
- **Missing**: Separate refund charge reversal

**Correct behavior (after fix):**
- Positive charge: 1.00 + (2,417 × 0.05) = 121.85 SAR
- Negative charge (reversal): 1.00 + (199 × 0.05) = 10.95 SAR
- Total: 132.80 SAR
- **Difference**: 20.90 SAR undercharged

## Solution

Modified the daily aggregation logic to add a "Sign" column before grouping. This ensures positive and negative amounts are grouped separately:

```python
# Add a "Sign" column to separate positive and negative amounts
temp_df["Amount Sign"] = temp_df["Transaction Line Amount"].apply(
    lambda x: "positive" if x >= 0 else "negative"
)

# Group by Payment Method + Date + Sign (not just Method + Date)
group_cols = ["Receipt Method Name", "Transaction Date", "Amount Sign"]
```

This change ensures:
1. Positive amounts are summed separately from negative amounts
2. Each group gets its own charge calculation with the fixed fee
3. Negative amounts generate reversal journal entries (3-series CREDIT, 5-series DEBIT)

## Impact

### MAKKAH Payment File (March 2026)
- **2 refund transactions** affecting 2 days:
  - March 13: TABBY refund -199 SAR
  - March 6: TAMARA refund -149 SAR

### Before Fix:
- Total charges: 3,455.49 SAR
- Missing refund charge reversals

### After Fix:
- Total charges: 3,490.56 SAR
- Includes separate entries for refunds
- **Additional charges captured**: 35.07 SAR

### Breakdown:
- March 13 TABBY:
  - Positive: 121.85 SAR (was 111.90 SAR) → +9.95 SAR
  - Negative: 10.95 SAR (new reversal entry)

- March 6 TAMARA:
  - Positive: 76.90 SAR (was 70.56 SAR) → +6.34 SAR
  - Negative: 7.83 SAR (new reversal entry)

## Files Modified

1. **Odoo-export-FBDA-template.py** - Three locations:
   - Lines 4319-4341: Payment-file-only path
   - Lines 4383-4405: AR Invoice enrichment path
   - Lines 4407-4423: AR Invoice-only path

## Verification

Generated journal now shows:
- ✅ Separate entries for positive and negative amounts on same day
- ✅ Reversal format for negative charges (3020044 CREDIT, 5000104 DEBIT)
- ✅ Correct total charges including refund reversals
- ✅ 4 reversal entry lines (2 for each refund: debit+credit pair)

## Accounting Impact

This fix ensures refunds are properly accounted for:
- Sales charges: Normal debit/credit entries
- Refund charges: Reversal entries that correctly reverse the original charge
- Net effect: More accurate representation of actual service provider charges
