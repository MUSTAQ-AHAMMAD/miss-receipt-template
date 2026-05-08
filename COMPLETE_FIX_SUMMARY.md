# Journal Template Charge Calculation - Complete Fix Summary

## Overview

Fixed two critical issues in the journal template charge calculation for TABBY/TAMARA service providers:

1. **Daily Aggregation Issue**: Charges were being calculated per transaction instead of per day
2. **Negative Values Issue**: Refunds were being netted against sales instead of charged separately

---

## Issue 1: Per-Transaction vs Per-Day Aggregation

### Problem
The system was calculating charges for each individual transaction, applying the fixed fee multiple times per day instead of once per day.

### Root Cause
Payment file dates included timestamps (e.g., "2026-03-05 07:55:23"), causing each transaction to appear as a unique day/time combination.

### Solution
1. Normalize dates to date-only format (remove time component)
2. Group transactions by (Method, Date, Warehouse) instead of including Transaction Number

### Impact (MAKKAH Payment File)
- **Before**: 259 individual transaction charges = 3,765.79 SAR
- **After**: 48 daily aggregated charges = 3,455.49 SAR
- **Savings**: 310.30 SAR (8.2% reduction)

---

## Issue 2: Netting Positive and Negative Amounts

### Problem
When aggregating by day, positive (sales) and negative (refunds) amounts were being summed together BEFORE calculating charges.

### Solution
Add "Amount Sign" column to separate positive from negative amounts during grouping.

### Impact (MAKKAH Payment File)
- **Before fix**: 3,455.49 SAR (missing refund charges)
- **After fix**: 3,490.56 SAR (includes refund reversals)
- **Additional charges captured**: 35.07 SAR

---

## Summary

Both issues resolved:
1. ✅ Charges calculated on daily aggregated amounts (not per transaction)
2. ✅ Refunds charged separately (not netted with sales)
3. ✅ Reversal journal entries generated correctly
4. ✅ Total charges accurate and compliant with contract terms
