# Alphanumeric Transaction and Receipt Numbers - Update Summary

## Overview
Updated the transaction number and receipt number generation to use **alphanumeric format** instead of purely numeric format.

## Changes Made

### 1. Transaction Number Format
**Before:**
- Format: `BLKU-0000001`, `BLKU-0000002`, ... `BLKU-9999999`
- Only numeric digits (0-9)

**After:**
- Format: `BLKU-0000001`, `BLKU-000000A`, `BLKU-0000010`, `BLKU-000002S`
- Alphanumeric using base-36 encoding (0-9, A-Z)
- More compact and supports larger sequence ranges

### 2. Receipt Number Format
Since receipt numbers are derived from transaction numbers, they automatically become alphanumeric:

**Standard Receipts:**
- Format: `{method}-{transaction_number}`
- Examples:
  - `CASH-BLKU-0000001`
  - `CASH-BLKU-000000A`
  - `BANK-BLKU-0000010`

**Miscellaneous Receipts:**
- Format: `MISC-{method}-{transaction_number}`
- Examples:
  - `MISC-CASH-BLKU-0000001`
  - `MISC-BANK-BLKU-000000A`

## Implementation Details

### Base-36 Encoding
The system now uses base-36 encoding where:
- Digits 0-9 represent values 0-9
- Letters A-Z represent values 10-35
- Example conversions:
  - 1 → `0000001`
  - 10 → `000000A`
  - 36 → `0000010`
  - 100 → `000002S`
  - 1000 → `00000RS`

### New Methods Added

#### `TxnNumberGenerator._to_alphanumeric(num: int, length: int = 7) -> str`
Converts a decimal number to alphanumeric format with padding.

#### `TxnNumberGenerator._from_alphanumeric(alphanumeric: str) -> int`
Converts an alphanumeric string back to decimal for internal tracking.

### Files Modified
1. `Odoo-export-FBDA-template.py` - Main integration script
2. `100%-Working-code-Odoo-to-Oracle-FBDA.py` - Backup/working version

## Benefits

1. **Alphanumeric Format**: As requested, both transaction and receipt numbers now contain letters and numbers
2. **Backward Compatible Tracking**: Internal sequence tracking still uses numeric values
3. **Larger Capacity**: Base-36 encoding provides much larger sequence range:
   - 7 characters can represent up to 78,364,164,096 values (vs 9,999,999 in pure numeric)
4. **Consistent Length**: Numbers are zero-padded to maintain consistent field width

## Testing Results

✓ All conversion tests passed
✓ Transaction number generation verified
✓ Receipt number format verified
✓ Round-trip conversion (number → alphanumeric → number) works correctly

## Examples

### Progressive Sequence Examples:
```
Sequence 1:  BLKU-0000001
Sequence 2:  BLKU-0000002
Sequence 9:  BLKU-0000009
Sequence 10: BLKU-000000A  ← First letter appears
Sequence 11: BLKU-000000B
Sequence 36: BLKU-0000010
Sequence 100: BLKU-000002S
```

### Receipt Examples:
```
Standard: CASH-BLKU-000000A
Standard: VISA-BLKU-0000010
Misc: MISC-BANK-BLKU-000002S
```

## Migration Notes

- The system automatically handles both old numeric and new alphanumeric formats
- Internal sequence tracking continues to use numeric values
- All display and output formats now show alphanumeric values
- No data migration required - system will generate new numbers in alphanumeric format going forward
