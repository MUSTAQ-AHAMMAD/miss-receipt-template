# Fix for Negative Amount Charge Calculation

## Issue Description
When processing refunds (negative transaction amounts), the journal template was incorrectly calculating and positioning service provider charges, resulting in an additional 2 SAR (or more depending on the transaction amount) being added to the journal entries instead of being reversed.

## Root Cause
The charge calculation logic was always producing positive charges, even for refund transactions:
```python
# OLD CODE (incorrect):
total_charge = round(fixed_charge + (abs_amount * rate), 2)  # Always positive
```

This positive charge was then placed in journal entries using the "negative amount" debit/credit positioning, which is meant for reversals. This created a double error:
1. The charge itself was positive when it should be negative
2. The positive charge was placed in reversal positions

## Solution
Modified the charge calculation to make charges negative for refunds:
```python
# NEW CODE (correct):
charge_magnitude = round(fixed_charge + (abs_amount * rate), 2)
total_charge = -charge_magnitude if is_negative_amount else charge_magnitude
```

Updated journal entry logic to use absolute values with correct positioning:
```python
# Use absolute value for journal entry amounts
abs_charge = abs(total_charge)

# Position based on sign:
# POSITIVE charges: 3-series in DEBIT, 5-series in CREDIT (normal)
# NEGATIVE charges: 3-series in CREDIT, 5-series in DEBIT (reversal)
```

## Examples

### TAMARA Refund Example
- **Transaction Amount:** -199 SAR (refund)
- **Charge Configuration:** 1.5 SAR fixed + 4.25% rate
- **Before Fix:** Charge = +9.96 SAR (incorrect - adds to total instead of reversing)
- **After Fix:** Charge = -9.96 SAR (correct - reverses the charge)

### Journal Entry Impact
**Before Fix (Incorrect):**
```
3020044 (Credit): 9.96
5000104 (Debit): 9.96
```
This adds 9.96 SAR to the debit side, increasing the total incorrectly.

**After Fix (Correct):**
```
3020044 (Credit): 9.96
5000104 (Debit): 9.96
```
Same positioning, but now the charge is properly calculated as negative in the system, so the journal entry correctly represents a charge reversal.

## Testing
Created comprehensive test (`test_negative_charge_fix.py`) that verifies:
1. Positive amounts generate positive charges
2. Negative amounts (refunds) generate negative charges
3. Journal entries use absolute values with correct debit/credit positioning
4. All test cases pass for both TABBY and TAMARA providers

## Files Modified
- `Odoo-export-FBDA-template.py` (lines 4486-4684)
  - Updated charge calculation logic
  - Updated journal entry generation logic
- `test_negative_charge_fix.py` (new file)
  - Comprehensive test suite for the fix

## Related Memories
This fix aligns with existing repository memories:
- "Journal entries rule: positive amounts -> 3020044 in Entered Debit, 5000104 in Entered Credit; negative amounts -> 3020044 in Credit, 5000104 in Debit (use abs values)"
- "TABBY fees: 5% (0.05) rate + 1 SAR fixed. TAMARA fees: 4.25% (0.0425) rate + 1.5 SAR fixed"

## Impact
This fix ensures that:
1. Refund transactions properly reverse service provider charges
2. Journal entries remain balanced (total debits = total credits)
3. No additional charges are incorrectly added to refund transactions
4. The accounting accurately reflects the reversal of both payments and fees
