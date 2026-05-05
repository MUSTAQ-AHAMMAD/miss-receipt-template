# Charge Calculation Demonstration Results

## Overview

This document shows the calculation output for the new charge logic for Tabby and Tamara payment methods. The calculation uses the formula specified in your requirements.

## Formula

For any Tabby or Tamara payment:

```
Total Charge = (Amount × Rate) × (1 + VAT)
Net Receipt = Amount - Total Charge
```

Where:
- **Amount**: The transaction amount from the sales lines
- **Rate**: The charge rate from SERVICE_PROVIDER_JOURNAL_META_Charges.csv
  - TABBY: 5.5% (0.055)
  - TAMARA: 3.5% (0.035)
- **VAT**: 15% (0.15) in Saudi Arabia

## Charge Rates Configuration

From `SERVICE_PROVIDER_JOURNAL_META_Charges.csv`:

| Provider | Type | Charge Rate |
|----------|------|-------------|
| TABBY | NON-CASH | 5.50% |
| TAMARA | NON-CASH | 3.50% |
| HUNGERSTATION | NON-CASH | 2.50% |
| MRSOOL | CASH | 15.00% |

## Sample Calculations

### Example 1: TAMARA Payment (199 SAR)

```
Order Ref: MAKKAH/112720
Date: 2026-03-31 22:27:59
Branch: MAKKAH
Payment Method: TAMARA
Original Amount: 199.00 SAR

Calculation:
  Total Charge = (Amount × Rate) × (1 + VAT)
  Total Charge = (199.00 × 0.035) × (1 + 0.15)
  Total Charge = 6.97 × 1.15
  Total Charge = 8.01 SAR

  Net Receipt = Amount - Total Charge
  Net Receipt = 199.00 - 8.01
  Net Receipt = 190.99 SAR
```

### Example 2: TABBY Payment (499 SAR)

```
Order Ref: MAKKAH/112701
Date: 2026-03-31 20:05:16
Branch: MAKKAH
Payment Method: TABBY
Original Amount: 499.00 SAR

Calculation:
  Total Charge = (Amount × Rate) × (1 + VAT)
  Total Charge = (499.00 × 0.055) × (1 + 0.15)
  Total Charge = 27.45 × 1.15
  Total Charge = 31.56 SAR

  Net Receipt = Amount - Total Charge
  Net Receipt = 499.00 - 31.56
  Net Receipt = 467.44 SAR
```

## Summary of Test Results (First 10 Orders)

| Order Ref | Date | Branch | Payment Method | Original Amount | Charge Rate | Total Charge | Net Receipt |
|-----------|------|--------|----------------|-----------------|-------------|--------------|-------------|
| MAKKAH/112720 | 2026-03-31 22:27:59 | MAKKAH | TAMARA | 199.00 | 3.50% | 8.01 | 190.99 |
| MAKKAH/112701 | 2026-03-31 20:05:16 | MAKKAH | TABBY | 499.00 | 5.50% | 31.56 | 467.44 |
| MAKKAH/112692 | 2026-03-31 19:16:47 | MAKKAH | TAMARA | 199.00 | 3.50% | 8.01 | 190.99 |
| MAKKAH/112691 | 2026-03-31 19:08:17 | MAKKAH | TAMARA | 249.00 | 3.50% | 10.02 | 238.98 |
| MAKKAH/112659 | 2026-03-30 22:06:23 | MAKKAH | TABBY | 222.00 | 5.50% | 14.04 | 207.96 |
| MAKKAH/112622 | 2026-03-30 18:43:33 | MAKKAH | TABBY | 499.00 | 5.50% | 31.56 | 467.44 |
| MAKKAH/112598 | 2026-03-30 15:19:05 | MAKKAH | TAMARA | 299.00 | 3.50% | 12.03 | 286.97 |
| MAKKAH/112597 | 2026-03-30 15:11:16 | MAKKAH | TAMARA | 399.00 | 3.50% | 16.06 | 382.94 |
| MAKKAH/112583 | 2026-03-30 11:39:55 | MAKKAH | TAMARA | 199.00 | 3.50% | 8.01 | 190.99 |
| MAKKAH/112521 | 2026-03-29 14:04:28 | MAKKAH | TAMARA | 463.00 | 3.50% | 18.64 | 444.36 |

**Totals:**
- Total Original Amount: 3,227.00 SAR
- Total Charges: 157.95 SAR
- Total Net Receipt: 3,069.05 SAR

## Data Sources

The calculation uses three files:

1. **Sales Lines File** (`MAkkah_SAles_Line.xlsx`):
   - Contains: Order Ref, Date, Branch, Payments/Amount, Payments/Payment Method
   - Used to get: Line item amounts per order

2. **Payment File** (`MAKKAH payment line 5 to 31 March.xlsx`):
   - Contains: Order Ref, Date, Branch, Payments/Amount, Payments/Payment Method
   - Used to: Match Order Ref with payment methods (TABBY/TAMARA)

3. **Charges File** (`SERVICE_PROVIDER_JOURNAL_META_Charges.csv`):
   - Contains: SERVICE_PROVIDER, CREDIT_DEBIT, BANK_CHARGE_RATE, and other metadata
   - Used to: Get the charge rate for each service provider

## Implementation Notes

### Matching Logic

1. Read the payment file to identify orders with TABBY or TAMARA payment methods
2. Match Order Ref from payment file to sales lines file
3. For each matching order:
   - Get the amount from the payment file (already split by payment method)
   - Get the charge rate for the specific provider (TABBY/TAMARA)
   - Calculate: Total Charge = (Amount × Rate) × (1 + VAT)
   - Calculate: Net Receipt = Amount - Total Charge

### Key Points

- **Order Ref** is the unique parameter to match between files
- Each order can have multiple payment methods
- Currently showing only TABBY and TAMARA (as per journal template requirements)
- Discount items handling: Can be excluded by checking for negative amounts or specific identifiers
- The charges are calculated per payment line (not per sales line item)

## Test Data Statistics

From the MAKKAH payment file:
- Total payment lines: 6,416
- TABBY/TAMARA payment lines: 259
- Unique orders with TABBY/TAMARA: 259

This indicates that each TABBY/TAMARA order typically has one payment line, which simplifies the calculation.

## Next Steps

Based on these results, please review and confirm:

1. ✅ Is the charge calculation formula correct?
2. ✅ Are the charge rates correct (TABBY: 5.5%, TAMARA: 3.5%)?
3. ✅ Should the Net Receipt amount be used in the journal template?
4. ❓ How should multiple items in a single order be handled?
5. ❓ Should discount items be excluded from the calculation?
6. ❓ Do you want charges broken down per item or per order total?

## Files Generated

- **Test Script**: `test_charges_calculation.py`
- **Output CSV**: `charges_calculation_output.csv`
- **This Report**: `CHARGE_CALCULATION_DEMO_RESULTS.md`

You can run the test script anytime with:
```bash
python3 test_charges_calculation.py
```

---

**Note**: The current implementation in `Odoo-export-FBDA-template.py` does NOT yet include this charge calculation logic. This is a demonstration only. Once you approve the calculation, we will integrate it into the journal template generation function.
