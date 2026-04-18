# CSV Merge Accuracy Report

## Overview

The CSV merger tool has been enhanced with comprehensive accuracy reporting to help identify and track all differences between input and output files during merge operations.

## What's New

### Enhanced Merge Function

The `merge_ar_invoices()` function now tracks:

1. **Per-file statistics**: Rows, transactions, and amounts for each input file
2. **Transaction tracking**: Which files contain which transactions
3. **Duplicate detection**: Detailed information about duplicate rows and their amounts
4. **Cross-file duplicates**: Transactions that appear in multiple input files
5. **Amount differences**: Exact amount removed due to deduplication

### Comprehensive Accuracy Report

After merging, a detailed accuracy report is automatically generated with the following sections:

#### 1. Input Files Processed
- Individual file statistics (rows, transactions, amounts)
- Total input summary

#### 2. Merge Operation Summary
- **Before Merge**: Total files, rows, and amounts
- **After Merge**: Final rows, unique transactions, and final amount
- **Differences Detected**: Duplicates removed, amount difference, accuracy percentage

#### 3. Detailed Duplicate Analysis
- List of duplicate transactions with:
  - Transaction number
  - Number of duplicate lines
  - Duplicate amount
  - Source files containing the duplicate

#### 4. Cross-File Duplicate Analysis
- Transactions appearing in multiple files
- Shows which files contain each duplicate transaction

#### 5. Accuracy Verification
- **Row Count Verification**: Input vs output with removal percentage
- **Amount Verification**: Input vs output amounts with difference
- **Transaction Uniqueness**: Final unique transaction count

#### 6. Conclusion
- Summary of merge results
- Warnings about cross-file duplicates
- Output file locations

## Example Report

```
================================================================================
  AR INVOICE CSV MERGE ACCURACY REPORT
  Generated: 2026-04-18 19:06:22
================================================================================

INPUT FILES PROCESSED:
--------------------------------------------------------------------------------
  [1] AR_Invoice_Store1.csv
      Rows:              1,234
      Transactions:        456
      Amount:       125,430.00 SAR

  [2] AR_Invoice_Store2.csv
      Rows:                987
      Transactions:        321
      Amount:        98,765.00 SAR

  TOTAL INPUT:
      Rows:              2,221
      Amount:       224,195.00 SAR

================================================================================
MERGE OPERATION SUMMARY:
================================================================================

BEFORE MERGE:
--------------------------------------------------------------------------------
  Total files:              2
  Total rows (combined):    2,221
  Total amount (combined):  224,195.00 SAR

AFTER MERGE:
--------------------------------------------------------------------------------
  Final rows:               2,150
  Unique transactions:      750
  Final amount:             218,500.00 SAR

DIFFERENCES DETECTED:
--------------------------------------------------------------------------------
  Duplicate rows removed:   71
  Amount removed:           5,695.00 SAR
  Accuracy:                 96.80% rows retained

================================================================================
DETAILED DUPLICATE ANALYSIS:
================================================================================

  Total duplicate transactions: 12

  [1] Transaction: BLK-0001234
      Duplicate lines:  3
      Duplicate amount: 450.00 SAR
      Found in files:   AR_Invoice_Store1.csv, AR_Invoice_Store2.csv
  ...

================================================================================
CROSS-FILE DUPLICATE ANALYSIS:
================================================================================

  Transactions appearing in multiple files: 12

  [1] Transaction: BLK-0001234
      Appears in 2 files: AR_Invoice_Store1.csv, AR_Invoice_Store2.csv
  ...

================================================================================
ACCURACY VERIFICATION:
================================================================================

  ✓ Row count verification:
      Input:    2,221 rows
      Output:   2,150 rows
      Removed:  71 duplicates (3.20%)
      Status:   ✓ ACCURATE

  ✓ Amount verification:
      Input:    224,195.00 SAR
      Output:   218,500.00 SAR
      Removed:  5,695.00 SAR (2.54%)
      Status:   ✓ ACCURATE

  ✓ Transaction uniqueness:
      Unique transactions: 750
      Cross-file duplicates: 12
      Status:   ✓ VERIFIED

================================================================================
CONCLUSION:
================================================================================

  ✓ Merge completed with 71 duplicate rows removed.
  ⚠ 12 transactions appear in multiple input files.
  ✓ Output file contains unique transactions only.

  Output file: merged_ar_invoice.csv
  Accuracy report: merged_ar_invoice_merge_report.txt

================================================================================
```

## Benefits

### Easy Identification of Issues

The report makes it easy to:

1. **Spot differences**: Immediately see how many rows and what amount was removed
2. **Track duplicates**: Know exactly which transactions were duplicated
3. **Verify accuracy**: Check that the merge operation was correct
4. **Audit trail**: Have a complete record of what changed during merge

### Use Cases

1. **Quality Assurance**: Verify that no data was incorrectly removed
2. **Debugging**: Identify which files contain duplicate data
3. **Auditing**: Maintain a record of merge operations
4. **Reconciliation**: Ensure amounts match expectations

## Usage

### Command Line

```bash
python csv_merger.py merged_output.csv file1.csv file2.csv file3.csv
```

The accuracy report will be automatically saved as `merged_output_merge_report.txt`

### Web UI

1. Navigate to "Merge AR Invoices" mode
2. Upload 2 or more CSV files
3. Click "Merge"
4. Download the merged file and the accuracy report

## Technical Details

### Duplicate Detection Strategy

The merger identifies duplicates based on:
- Transaction Number
- Transaction Line Description

This ensures that the same transaction line from different files is only included once.

### Tracking Implementation

- **transaction_tracker**: Dictionary mapping transaction numbers to source files
- **duplicate_details**: List of dictionaries containing duplicate information
- **cross_file_duplicates**: List of transactions appearing in multiple files

### Accuracy Metrics

- **Row Retention**: `(final_rows / total_rows) * 100`
- **Amount Retention**: `(final_amount / total_amount) * 100`
- **Duplicate Percentage**: `(duplicates_removed / total_rows) * 100`

## Important Notes

1. The first occurrence of a duplicate is kept (`keep="first"`)
2. Cross-file duplicates indicate the same transaction appears in multiple input files
3. Amount differences are expected when duplicates are removed
4. The report limits detailed duplicate listings to 50 items to keep file size manageable

## Troubleshooting

### No duplicates detected but amounts differ

Check if the input files have different transaction line amounts for the same transaction number.

### Too many cross-file duplicates

This may indicate:
- Files were exported from overlapping date ranges
- The same data was exported multiple times
- Files should be checked for proper date filtering

### Report shows issues detected

Review the detailed duplicate analysis section to see which specific transactions are duplicated and in which files they appear.
