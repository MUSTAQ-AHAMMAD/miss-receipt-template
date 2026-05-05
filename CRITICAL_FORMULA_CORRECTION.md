# 🚨 CRITICAL CORRECTION: Charge Calculation Formula

## Summary

The charge calculation formula has been **corrected** based on the Oracle SQL formula reference provided by the user.

## Previous Implementation (INCORRECT) ❌

### Formula
```
Total Charge = (Amount × Rate) × (1 + VAT)
```

### Rates
- **TABBY**: 0.5% (0.005)
- **TAMARA**: 0.3% (0.003)
- **VAT**: 15% (0.15)

### Why This Was Wrong
This formula was based on initial user requirements that were **incorrect**. It included VAT in the charge calculation and used very low rates.

## Current Implementation (CORRECT) ✅

### Formula
```
Total Charge = FIXED_FREIGHT_CHARGE + (Amount × BANK_CHARGE_RATE)
```

This matches the Oracle SQL formula:
```sql
j.FIXED_FREIGHT_CHARGE + (I.AMT * J.BANK_CHARGE_RATE)
```

### Configuration
- **TABBY**:
  - Fixed Charge: 1 SAR
  - Rate: 5.5% (0.055)
- **TAMARA**:
  - Fixed Charge: 1.5 SAR
  - Rate: 5.99% (0.0599)

### Key Differences
1. **NO VAT** in charge calculation
2. **Fixed charge component** added
3. **Higher rates** (5.5% and 5.99% instead of 0.5% and 0.3%)

## Verification Examples

### Example 1: TABBY (160 SAR)
```
Amount: 160 SAR
Fixed Charge: 1 SAR
Rate: 5.5% (0.055)

Calculation:
  Variable Charge = 160 × 0.055 = 8.8 SAR
  Total Charge = 1 + 8.8 = 9.8 SAR

✓ Matches user example: (160 × 0.055) + 1 = 9.8
```

### Example 2: TAMARA (75 SAR)
```
Amount: 75 SAR
Fixed Charge: 1.5 SAR
Rate: 5.99% (0.0599)

Calculation:
  Variable Charge = 75 × 0.0599 = 4.4925 SAR
  Total Charge = 1.5 + 4.4925 = 5.9925 SAR

✓ Matches user example: (75 × 0.0599) + 1.5 = 5.9925
```

## What Changed

### 1. SERVICE_PROVIDER_JOURNAL_META_Charges.csv

**Before:**
```csv
TABBY,  CREDIT, ..., 1,   0.005
TABBY,  DEBIT,  ..., 1,   0.005
TAMARA, CREDIT, ..., 1,   0.003
TAMARA, DEBIT,  ..., 1,   0.003
```

**After:**
```csv
TABBY,  CREDIT, ..., 1,   0.055
TABBY,  DEBIT,  ..., 1,   0.055
TAMARA, CREDIT, ..., 1.5, 0.0599
TAMARA, DEBIT,  ..., 1.5, 0.0599
```

### 2. Odoo-export-FBDA-template.py

#### Charge Loading
Now loads **both** FIXED_FREIGHT_CHARGE and BANK_CHARGE_RATE:
```python
charges_lookup[key] = (fixed_charge, rate)  # Tuple of (fixed, rate)
```

#### Calculation Function
```python
def _calculate_charge(amount: float, payment_method: str) -> float:
    fixed_charge, rate = charges_lookup[charge_key]
    # NEW: Total Charge = FIXED_FREIGHT_CHARGE + (Amount × BANK_CHARGE_RATE)
    total_charge = fixed_charge + (amount * rate)
    return total_charge
```

**Previously:**
```python
def _calculate_charge(amount: float, payment_method: str, vat_rate: float) -> float:
    rate = charges_lookup[charge_key]
    # OLD: Total Charge = (Amount × Rate) × (1 + VAT)
    total_charge = (amount * rate) * (1 + vat_rate)
    return total_charge
```

#### Logging
Now shows all components:
```python
print(f"  ℹ️  Charge calculation for {payment_method}: "
      f"Amount={amount:.2f}, Fixed={fixed_charge:.2f}, Rate={rate*100:.2f}%, "
      f"Variable Charge={amount*rate:.2f}, "
      f"Total Charge={total_charge:.2f}")
```

## Comparison: Old vs New

### For 199 SAR TAMARA Transaction

**OLD (INCORRECT):**
```
Formula: (Amount × Rate) × (1 + VAT)
Calculation: (199 × 0.003) × 1.15 = 0.687 SAR
```

**NEW (CORRECT):**
```
Formula: FIXED_FREIGHT_CHARGE + (Amount × BANK_CHARGE_RATE)
Calculation: 1.5 + (199 × 0.0599) = 1.5 + 11.92 = 13.42 SAR
```

**Difference:** The correct formula produces **significantly higher** and more accurate charges!

### For 499 SAR TABBY Transaction

**OLD (INCORRECT):**
```
Formula: (Amount × Rate) × (1 + VAT)
Calculation: (499 × 0.005) × 1.15 = 2.87 SAR
```

**NEW (CORRECT):**
```
Formula: FIXED_FREIGHT_CHARGE + (Amount × BANK_CHARGE_RATE)
Calculation: 1 + (499 × 0.055) = 1 + 27.445 = 28.445 SAR
```

**Difference:** ~**10x higher** with correct formula!

## Oracle SQL Reference

The correct formula comes from this Oracle SQL calculation:
```sql
SUM(ROUND(UNIT_SELLING_PRICE*QUANTITY,2)+nvl(TAX_AMT,0))  AMT
j.FIXED_FREIGHT_CHARGE+(I.AMT*J.BANK_CHARGE_RATE)
```

Where:
- `I.AMT` = Transaction amount
- `J.FIXED_FREIGHT_CHARGE` = Fixed charge from charges table
- `J.BANK_CHARGE_RATE` = Variable rate from charges table

## Additional Requirements from User

1. **Amount Calculation**:
   ```sql
   SUM(ROUND(UNIT_SELLING_PRICE*QUANTITY,2)+nvl(TAX_AMT,0))
   ```
   - Calculate per invoice number and branch
   - Exclude discount items

2. **Per-Item Calculation**:
   - Calculate charges per individual line item
   - Sum total charges for each order

3. **Order Ref Matching**:
   - Match Order Ref between payment file and sales lines file
   - Use this to get accurate amounts per transaction

## Files Modified

1. ✅ `SERVICE_PROVIDER_JOURNAL_META_Charges.csv` - Updated rates and fixed charges
2. ✅ `Odoo-export-FBDA-template.py` - Corrected formula implementation
3. ✅ `verify_correct_formula.py` - Verification script created

## Testing

Run the verification script:
```bash
python3 verify_correct_formula.py
```

Expected output:
```
TABBY: (160 × 0.055) + 1 = 9.8 ✓
TAMARA: (75 × 0.0599) + 1.5 = 5.9925 ✓
```

## Next Steps

The formula is now **correct** and matches the Oracle SQL reference. The system will:

1. ✅ Load both FIXED_FREIGHT_CHARGE and BANK_CHARGE_RATE from CSV
2. ✅ Calculate using formula: `Fixed + (Amount × Rate)`
3. ✅ Log all charge components during processing
4. 🔄 Ready for per-item calculation when sales lines file is provided

## Important Notes

⚠️ **Previous calculations were incorrect** - any journal templates generated before this fix used the wrong formula and wrong rates.

✅ **Current implementation is correct** - matches Oracle formula exactly.

---

**Date**: May 5, 2026
**Status**: ✅ CORRECTED
**Formula**: `Total Charge = FIXED_FREIGHT_CHARGE + (Amount × BANK_CHARGE_RATE)`
