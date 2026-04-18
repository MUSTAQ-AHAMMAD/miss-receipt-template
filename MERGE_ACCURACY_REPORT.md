# CSV Merge Accuracy Report

## Overview

The CSV merger tool generates comprehensive, **professional** accuracy reports that make it easy to identify and track all differences between input and output files during merge operations.

## Professional Report Format

The report follows the same professional standards used throughout the application, featuring:

- **Executive Summary** with overall status at-a-glance
- **Visual Hierarchy** using box-drawing characters (╔══╗ ║ ╚══╝)
- **Status Indicators** (✓/✗/⚠/ℹ) for instant problem identification
- **Professional Tables** for structured data presentation
- **Prominent Issue Highlighting** with █ blocks when problems are detected

## Report Structure

### 1. Executive Summary

The report starts with a comprehensive executive summary that shows:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  EXECUTIVE SUMMARY                                                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Overall Status: ✓ CLEAN MERGE - NO ISSUES DETECTED                         ║
║------------------------------------------------------------------------------║
║  Files Merged: 2                         Duplicates: 0                      ║
║  Input Rows: 4                           Output Rows: 4                     ║
║  Input Amount: 1,000.00 SAR              Output Amount: 1,000.00 SAR        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ✓  Row Retention                                                     100.0%║
║  ✓  Amount Retention                                                  100.0%║
║  ✓  Cross-File Duplicates                                     0 transactions║
║  ℹ  Unique Transactions                                                    4║
╚══════════════════════════════════════════════════════════════════════════════╝
```

**Overall Status Indicators:**
- `✓ CLEAN MERGE - NO ISSUES DETECTED` - Perfect merge, no duplicates
- `ℹ DUPLICATES REMOVED` - Duplicates found and removed (normal operation)
- `⚠ ISSUES DETECTED` - Cross-file duplicates or other issues requiring attention

### 2. Problem Detection (When Issues Exist)

When problems are detected, a prominent highlighted box appears immediately after the executive summary:

```
  ████████████████████████████████████████████████████████████████████████████
  █                   ⚠ PROBLEMS DETECTED — ACTION REQUIRED                  █
  ████████████████████████████████████████████████████████████████████████████
  █  • DUPLICATE ROWS:                                                      █
  █      2 duplicate rows were removed from the merge                       █
  █      Amount removed: 700.00 SAR                                         █
  █                                                                          █
  █  • CROSS-FILE DUPLICATES:                                               █
  █      2 transactions appear in multiple input files                      █
  █      This may indicate overlapping date ranges or data export issues    █
  █                                                                          █
  █  RECOMMENDATION:                                                        █
  █    → Review the duplicate transaction details below                     █
  █    → Verify input files have correct date ranges                        █
  █    → Check for overlapping data exports                                 █
  ████████████████████████████████████████████████████████████████████████████
```

This makes problems **impossible to miss** and provides clear recommendations.

### 3. Input Files Summary Table

Professional table showing all input files with their statistics:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  INPUT FILES PROCESSED                                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

  ┌────┬────────────────────────────────┬────────────┬────────────┬──────────────┐
  │ #  │ File Name                │ Rows        │ Txns        │ Amount (SAR)  │
  ├────┼────────────────────────────────┼────────────┼────────────┼──────────────┤
  │ 1  │ store1.csv                     │          4 │          4 │     1,000.00 │
  │ 2  │ store2.csv                     │          3 │          3 │     1,200.00 │
  │ 3  │ store3.csv                     │          2 │          2 │     1,300.00 │
  ├────┴────────────────────────────────┼────────────┼────────────┼──────────────┤
  │ TOTAL                              │          9 │          - │     3,500.00 │
  └────────────────────────────────────┴────────────┴────────────┴──────────────┘
```

### 4. Merge Operation — Before & After

Side-by-side comparison showing what changed:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  MERGE OPERATION — BEFORE & AFTER                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

  ┌──────────────────────────────────────┬──────────────────────────────────────┐
  │ BEFORE MERGE                        │ AFTER MERGE                           │
  ├──────────────────────────────────────┼──────────────────────────────────────┤
  │ Files: 3                            │ Unique Transactions: 7                │
  │ Total Rows: 9                       │ Final Rows: 7                         │
  │ Total Amount: 3,500.00 SAR          │ Final Amount: 2,800.00 SAR            │
  ├──────────────────────────────────────┴──────────────────────────────────────┤
  │ DIFFERENCE                                                                 │
  ├─────────────────────────────────────────────────────────────────────────────┤
  │ Rows Removed: 2 (22.22%)                                                   │
  │ Amount Removed: 700.00 SAR (20.00%)                                        │
  └─────────────────────────────────────────────────────────────────────────────┘
```

### 5. Duplicate Transactions Analysis (If Present)

Detailed table of duplicate transactions:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  DUPLICATE TRANSACTIONS ANALYSIS                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

  Total duplicate transactions found: 2

  ┌────┬────────────────────┬────────────┬────────────────┬──────────────────────┐
  │ #  │ Transaction   │ Dup Lines   │ Dup Amount      │ Found in Files         │
  ├────┼────────────────────┼────────────┼────────────────┼──────────────────────┤
  │ 1  │ BLK-0000003        │          1 │         300.00 │ 2 files              │
  │ 2  │ BLK-0000004        │          1 │         400.00 │ 2 files              │
  └────┴────────────────────┴────────────┴────────────────┴──────────────────────┘
```

### 6. Cross-File Duplicates (If Present)

Lists transactions that appear in multiple input files:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  CROSS-FILE DUPLICATES — TRANSACTIONS IN MULTIPLE FILES                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

  ⚠ WARNING: 2 transactions appear in multiple files

  [1] BLK-0000003
      → Appears in 2 files: store2.csv, store1.csv

  [2] BLK-0000004
      → Appears in 2 files: store2.csv, store1.csv
```

### 7. Final Verification

Summary of verification checks:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  FINAL VERIFICATION                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

  ℹ  Data Integrity:    2 duplicates removed
  ⚠  File Overlap:      2 cross-file duplicates
  ✓  Output File:       merged.csv
  ✓  Report File:       merged_merge_report.txt
```

### 8. Conclusion

Final status with timestamp:

```
  ════════════════════════════════════════════════════════════════════════════
  ⚠  MERGE COMPLETED WITH WARNINGS
  ⚠  Review duplicate transactions and cross-file overlaps above
  ℹ  Consider checking input file date ranges
  ✓  Finished: 2026-04-18 19:25:22
  ════════════════════════════════════════════════════════════════════════════
```

## Status Indicators

The report uses clear status indicators throughout:

- **✓** - Check passed / No issues
- **✗** - Critical failure detected
- **⚠** - Warning / Attention required
- **ℹ** - Informational

## Benefits

### Easy Problem Identification

1. **Executive Summary** - See status at-a-glance before reading details
2. **Problem Detection Box** - Impossible to miss when issues exist
3. **Clear Indicators** - ✓/⚠/ℹ show exactly what needs attention
4. **Structured Tables** - Easy to scan and compare data

### Professional Presentation

1. **Visual Hierarchy** - Box-drawing characters create clear sections
2. **Aligned Columns** - Professional table formatting
3. **Consistent Style** - Matches other reports in the application
4. **Clean Layout** - Easy to read and understand

### Actionable Information

1. **Recommendations** - Clear next steps when issues are found
2. **Detailed Analysis** - Transaction-level duplicate information
3. **Cross-File Tracking** - Identifies which files contain duplicates
4. **Metrics** - Percentages and counts for verification

## Usage

### Command Line

```bash
python csv_merger.py merged_output.csv file1.csv file2.csv file3.csv
```

The professional accuracy report is automatically saved as `merged_output_merge_report.txt`

### Web UI

1. Navigate to "Merge AR Invoices" mode
2. Upload 2 or more CSV files
3. Click "Merge"
4. Download both the merged file and the professional accuracy report

## Use Cases

### 1. Quality Assurance
- Quickly verify merge accuracy with executive summary
- Confirm no unexpected data loss
- Check duplicate handling is correct

### 2. Debugging
- Identify which files contain duplicate data
- Find cross-file overlaps instantly
- Review detailed duplicate transaction lists

### 3. Auditing
- Professional format suitable for documentation
- Complete record of merge operations
- Clear status indicators for compliance

### 4. Reconciliation
- Before/After comparison shows all changes
- Amount tracking ensures financial accuracy
- Percentage metrics validate expectations

## Technical Details

### Duplicate Detection Strategy

The merger identifies duplicates based on:
- Transaction Number
- Transaction Line Description

This ensures that the same transaction line from different files is only included once.

### Report Display Limits

To keep reports readable:
- Duplicate transactions: Shows top 20 (configurable)
- Cross-file duplicates: Shows top 15 (configurable)
- Additional items noted with "... and N more" messages

### File Name Handling

Long file names are automatically truncated in tables:
- Maximum 32 characters shown
- Truncated names end with "..."
- Full names used in detailed sections

## Important Notes

1. **Executive Summary First** - Always check the executive summary before diving into details
2. **Status Indicators** - ✓/⚠/ℹ symbols show exactly what needs attention
3. **Problem Box** - When present, this should be your first focus
4. **Cross-File Duplicates** - May indicate overlapping date ranges in source files
5. **First Occurrence Kept** - When duplicates are found, the first occurrence is retained

## Troubleshooting

### Report shows ⚠ ISSUES DETECTED

Check the problem detection box immediately after the executive summary for:
- Duplicate rows and amounts removed
- Cross-file duplicate warnings
- Actionable recommendations

### Understanding Cross-File Duplicates

This means the same transaction appears in multiple input files, which may indicate:
- Files were exported with overlapping date ranges
- The same data was exported multiple times
- Files should be checked for proper filtering

### Report shows ℹ DUPLICATES REMOVED but no cross-file duplicates

This is normal - duplicates were found within the combined data and removed automatically. The output file contains unique transactions only.

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
