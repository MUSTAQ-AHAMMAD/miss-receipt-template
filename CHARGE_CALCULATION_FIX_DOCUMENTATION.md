# Charge Calculation Fix: Daily Aggregation

## Summary

Fixed the journal template generation to calculate service provider charges (TABBY/TAMARA) on **daily aggregated totals** instead of per individual transaction.

## Problem

Previously, the system was calculating charges for each individual transaction:
- **Formula per transaction**: Fixed fee + (transaction amount × rate)
- **Example**: 6 TABBY transactions on March 5th = 6 fixed fees (6 × 1.00 SAR = 6.00 SAR) + percentage charges
- **Result**: Higher total charges due to multiple fixed fees per day

## Solution

Changed the calculation to aggregate all transactions per day, then apply the charge formula once:
- **Formula per day**: Fixed fee + (sum of all daily transactions × rate)
- **Example**: 6 TABBY transactions on March 5th = 1 fixed fee (1.00 SAR) + percentage on total daily amount
- **Result**: Lower, more accurate charges aligned with service provider contracts

## Impact (MAKKAH Payment File Example)

### Before (Per-Transaction):
- TABBY: 1,695.20 SAR (101 transactions)
- TAMARA: 2,070.59 SAR (158 transactions)
- **Total: 3,765.79 SAR**

### After (Per-Day):
- TABBY: 1,597.30 SAR (23 daily aggregates)
- TAMARA: 1,858.19 SAR (25 daily aggregates)
- **Total: 3,455.49 SAR**

### Savings: 310.30 SAR (8.2% reduction)

## Technical Changes

Modified `Odoo-export-FBDA-template.py` at three locations:

### 1. Payment-file-only branch (lines 4312-4331)
- Added date normalization to remove time component
- Grouped by (Payment Method, Date, Warehouse Code) instead of including Transaction Number
- Aggregates multiple transactions on the same day into one charge calculation

### 2. AR Invoice enrichment branch (lines 4366-4385)
- Same grouping logic applied when AR Invoice data is available
- Ensures consistent behavior across both processing paths

### 3. AR Invoice-only branch (lines 4387-4398)
- Updated grouping to use Date without Transaction Number
- Maintains consistency across all code paths

## Key Code Changes

```python
# Normalize Transaction Date to date-only (remove time component)
temp_df["Transaction Date"] = pd.to_datetime(temp_df["Transaction Date"]).dt.date

# Group by Payment Method + Date ONLY (not by Transaction Number)
group_cols = ["Receipt Method Name", "Transaction Date"]
if "Warehouse Code" in temp_df.columns:
    group_cols.append("Warehouse Code")

grouped = temp_df.groupby(group_cols, dropna=False).agg({
    "Transaction Line Amount": "sum",
    "Transaction Number": "first"  # Keep first for reference
}).reset_index()
```

## Testing

Verified with MAKKAH payment file (March 5-31, 2026):
- ✅ Charges correctly aggregate by day
- ✅ Formula applied once per day per payment method
- ✅ Total matches expected value (~3,455 SAR)
- ✅ Savings of ~310 SAR compared to per-transaction method

## Formula Reference

- **TABBY**: Fixed fee = 1.00 SAR, Rate = 5.00%
- **TAMARA**: Fixed fee = 1.50 SAR, Rate = 4.25%

**Daily Charge Calculation**:
```
Total Charge = Fixed Fee + (Sum of Daily Transactions × Rate)
```

**Example** (March 5, 2026 - TABBY):
- 6 transactions totaling 2,159.00 SAR
- Charge = 1.00 + (2,159.00 × 0.05) = 1.00 + 107.95 = **108.95 SAR**
- Old method: 6 × 1.00 + (2,159.00 × 0.05) = 6.00 + 107.95 = **113.95 SAR**
- Savings: 5.00 SAR per day
