# Receipt Consolidation Update

## Summary

Updated the receipt generation system to consolidate receipts by payment method instead of creating separate files for each date and store combination.

## Changes Made

### Before
- **Standard Receipts**: One file per payment method per store per date
  - Example: `Receipt_Cash_Store1_20260401.csv`, `Receipt_Cash_Store1_20260402.csv`, etc.
- **Misc Receipts**: One file per payment method per store per date
  - Example: `MiscReceipt_Visa_Store1_20260401.csv`, `MiscReceipt_Visa_Store1_20260402.csv`, etc.

### After
- **Standard Receipts**: One file per payment method containing all dates and stores
  - Example: `Receipt_Cash.csv` (contains all dates and stores)
- **Misc Receipts**: One file per payment method containing all dates and stores
  - Example: `MiscReceipt_Visa.csv` (contains all dates and stores)

## Technical Changes

### 1. `generate_standard_receipts()` method
- Changed from creating one DataFrame per (method, store, date) combination
- Now creates one DataFrame per payment method with multiple rows
- Uses `method_rows` dictionary to collect all rows for each payment method
- Filename format changed from `Receipt_{method}_{store}_{date}.csv` to `Receipt_{method}.csv`

### 2. `generate_misc_receipts()` method
- Applied same consolidation logic as standard receipts
- Uses `method_rows` dictionary to collect all rows for each payment method
- Filename format changed from `MiscReceipt_{method}_{store}_{date}.csv` to `MiscReceipt_{method}.csv`

### 3. `save_standard_receipts()` and `save_misc_receipts()` methods
- Updated output formatting to show row counts
- Format: `✓ Receipt_Cash.csv  15 rows  12,345.67 SAR`
- This helps users see how many date/store combinations are in each file

## Benefits

1. **Fewer Files**: Instead of 100+ files (one per date per method), you get one file per payment method
2. **Easier Management**: All data for a payment method is in one place
3. **Better Organization**: Simpler folder structure with fewer files
4. **Same Data**: All the same information is preserved, just organized differently

## Example Output

### Standard Receipts
```
✓ Receipt_Cash.csv      45 rows    125,432.50 SAR
✓ Receipt_Mada.csv      32 rows     89,234.75 SAR
✓ Receipt_Visa.csv      28 rows     67,890.25 SAR
✓ Receipt_MasterCard.csv 15 rows    34,567.80 SAR
```

### Misc Receipts
```
✓ MiscReceipt_Visa.csv       28 rows    1,234.5678 SAR
✓ MiscReceipt_MasterCard.csv 15 rows      789.0123 SAR
```

## Testing

A test script (`test_consolidated_receipts.py`) has been added to verify:
- Consolidation logic is correctly implemented
- Filenames follow the new format
- Row counts are displayed in output
- Both standard and misc receipts are consolidated

Run the test with:
```bash
python3 test_consolidated_receipts.py
```

## Backward Compatibility

This change modifies the file structure. If you have existing integrations that expect the old file naming format, you may need to update them to work with the new consolidated format.

## Files Modified

1. `Odoo-export-FBDA-template.py`:
   - `generate_standard_receipts()` method (lines ~2409-2465)
   - `generate_misc_receipts()` method (lines ~2568-2631)
   - `save_standard_receipts()` method (lines ~2715-2738)
   - `save_misc_receipts()` method (lines ~2740-2755)

2. `test_consolidated_receipts.py` (new file):
   - Verification test for the consolidation logic
