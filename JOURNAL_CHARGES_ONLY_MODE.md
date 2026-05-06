# Journal Template - Charges Only Mode

## Overview

The journal template generation has been updated to generate **CHARGES ONLY** - not payment amounts. This mode is designed for scenarios where payment amounts are already recorded in the system, and only the service provider fees (TABBY/TAMARA charges) need to be journaled separately.

## What Changed

### Before (Previous Behavior)
Each order generated **4 journal entry lines**:
- 2 lines for the payment amount (debit/credit pair)
- 2 lines for the service charge (debit/credit pair)

### After (Current Behavior - Charges Only)
Each order generates **2 journal entry lines**:
- 2 lines for the service charge ONLY (debit/credit pair)
- Payment amount lines are **EXCLUDED**

## Why This Change?

This change addresses the following scenario:
- Payment amounts (the actual transaction values) are already recorded in another system or module
- Only the service provider charges (fees charged by TABBY/TAMARA) need to be journaled
- Including both would create duplicate entries for payment amounts

## How It Works

### Charge Calculation

Charges are calculated based on the charges configuration file (`SERVICE_PROVIDER_JOURNAL_META_Charges.csv`):

```
Formula: Total Charge = Fixed Charge + (Amount × Rate)
```

For example:
- TABBY: Fixed = 1.00 SAR, Rate = 2.5%
- TAMARA: Fixed = 1.00 SAR, Rate = 3.0%

### Journal Entry Structure

For each qualifying order (TABBY/TAMARA payment), the system generates:

**Charge Entry (2 lines):**
1. **Credit Account** (3-series, e.g., 3020044)
   - Entered Credit Amount: [charge amount]
2. **Debit Account** (5-series, e.g., 5000104)
   - Entered Debit Amount: [charge amount]

**Example:**
```
Order: SO-12345
Payment Amount: 500.00 SAR
Charge Calculation: 1.00 + (500.00 × 2.5%) = 13.50 SAR

Journal Entries Generated:
Line 1: Account 3020044, Credit: 13.50 SAR
Line 2: Account 5000104, Debit: 13.50 SAR
```

## Output Example

When generating a journal template, you'll see output like:

```
════════════════════════════════════════════════════════════════════════════════
JOURNAL TEMPLATE MODE: CHARGES ONLY
════════════════════════════════════════════════════════════════════════════════
ℹ️  This journal template will generate entries for SERVICE CHARGES ONLY
ℹ️  Payment amounts will NOT be included in the journal entries
ℹ️  Each qualifying order will have one debit/credit pair for charges
════════════════════════════════════════════════════════════════════════════════

  ℹ️  Charge for TABBY: Fixed=1.00, Rate=2.50%, Total Charge=13.50
  ℹ️  Added charge entries for TABBY: 13.50 SAR
  ℹ️  Charge for TAMARA: Fixed=1.00, Rate=3.00%, Total Charge=16.00
  ℹ️  Added charge entries for TAMARA: 16.00 SAR

════════════════════════════════════════════════════════════════════════════════
JOURNAL TEMPLATE GENERATION COMPLETE - CHARGES ONLY MODE
════════════════════════════════════════════════════════════════════════════════
✓  Generated 4 journal entry lines
   - Charge entries: 4 lines (2 charge transactions)
   - Payment entries: 0 lines (EXCLUDED in charges-only mode)
   - Total charges amount: 29.50 SAR
════════════════════════════════════════════════════════════════════════════════
```

## What If No Charges Are Found?

If the system cannot calculate charges for a transaction, you'll see:

```
⚠️  No charges calculated for TABBY (Amount: 500.00 SAR) - skipping entry
```

This means:
- No charges file was provided, OR
- The charges lookup returned 0 for this provider, OR
- The transaction doesn't match the charges configuration

To resolve:
1. Ensure `SERVICE_PROVIDER_JOURNAL_META_Charges.csv` exists
2. Verify it contains entries for TABBY and TAMARA
3. Check that the IS_CASH flag matches (typically "0" for non-cash)

## Restoring Payment Entries (If Needed)

If you need to restore the original behavior (payment amounts + charges), locate line ~4582 in `Odoo-export-FBDA-template.py` and uncomment these lines:

```python
# NOTE: If you need to restore payment entries, uncomment the lines below:
# journal_entries.append(credit_account_entry)
# journal_entries.append(debit_account_entry)
```

After uncommenting, each order will generate 4 lines again (2 for payment + 2 for charges).

## Sample Test Data

To test the charges-only mode, use:

1. **Payment File**: Contains TABBY/TAMARA transactions with Sales Order references
2. **Sales Lines File**: Contains line items with amounts per order
3. **Charges File**: `SERVICE_PROVIDER_JOURNAL_META_Charges.csv` with charge rates

### Sample Charges File Format:

```csv
SERVICE_PROVIDER,IS_CASH,FIXED_CHARGE,RATE,VAT
TABBY,0,1.00,0.025,0.15
TAMARA,0,1.00,0.030,0.15
```

## Benefits of Charges-Only Mode

1. **No Duplication**: Payment amounts aren't duplicated if already recorded elsewhere
2. **Clear Separation**: Service charges are isolated in their own journal entries
3. **Easier Reconciliation**: Only charge amounts need to be reconciled with provider statements
4. **Flexible Accounting**: Payment and charge entries can be posted to different periods if needed

## Verification Checklist

After generating a journal template in charges-only mode:

- [ ] Total number of lines = 2 × number of qualifying orders
- [ ] Each order has exactly 2 lines (one debit, one credit)
- [ ] Total debits = Total credits (balanced entries)
- [ ] Amounts match expected charge calculations
- [ ] No payment amount entries are present
- [ ] Only TABBY and TAMARA transactions are included

## Troubleshooting

### "No journal entries generated"

**Possible Causes:**
1. No charges file provided
2. No TABBY/TAMARA transactions in payment file
3. Charges lookup returning 0 for all transactions

**Solutions:**
1. Verify `SERVICE_PROVIDER_JOURNAL_META_Charges.csv` exists and is properly formatted
2. Check payment file contains TABBY/TAMARA payment methods
3. Review charges file rates and fixed charges (ensure they're > 0)

### "Charges calculated but seem incorrect"

**Check:**
1. Fixed charge amount in charges file
2. Rate percentage (e.g., 0.025 = 2.5%)
3. VAT is included in the rate
4. Formula: Fixed + (Amount × Rate)

### "Want both payment and charge entries"

Uncomment the payment entry lines at line ~4582 in the code (see "Restoring Payment Entries" section above).

## Related Files

- `Odoo-export-FBDA-template.py` - Main implementation (lines 4403-4732)
- `SERVICE_PROVIDER_JOURNAL_META_Charges.csv` - Charge rates configuration
- `JOURNAL_SALES_LINES_FIX.md` - Documentation on sales lines amount integration
- `JOURNAL_TEMPLATE_GENERATION_GUIDE.md` - General journal template guide

## Version History

- **2026-05-06**: Implemented charges-only mode
  - Removed payment amount entries from journal template
  - Added comprehensive logging and warnings
  - Updated summary output for charges-only mode
