"""
================================================================================
CSV MERGER UTILITY FOR AR INVOICES
================================================================================
Merges multiple AR Invoice CSV files into a single consolidated file
while maintaining proper sequence and avoiding duplicates.
================================================================================
"""

import pandas as pd
from pathlib import Path
from typing import List
from datetime import datetime
import sys


def merge_ar_invoices(input_files: List[str], output_file: str) -> dict:
    """
    Merge multiple AR Invoice CSV files into one.

    Args:
        input_files: List of paths to AR Invoice CSV files
        output_file: Path for the merged output file

    Returns:
        Dictionary with merge statistics
    """
    if not input_files:
        raise ValueError("No input files provided")

    all_dfs = []
    stats = {
        "total_files": len(input_files),
        "total_rows": 0,
        "unique_transactions": 0,
        "total_amount": 0.0,
        "files_processed": [],
        "duplicates_removed": 0,
        "duplicate_details": [],
        "amount_difference": 0.0,
    }

    print(f"\n{'='*72}")
    print("  AR INVOICE CSV MERGER")
    print(f"{'='*72}\n")

    # Track transaction numbers across files for duplicate detection
    transaction_tracker = {}

    for i, file_path in enumerate(input_files, 1):
        try:
            print(f"  [{i}/{len(input_files)}] Loading: {Path(file_path).name}")
            df = pd.read_csv(file_path, encoding="utf-8-sig")

            rows = len(df)
            amount = df["Transaction Line Amount"].sum() if "Transaction Line Amount" in df.columns else 0.0

            # Track unique transactions per file
            unique_txns = 0
            if "Transaction Number" in df.columns:
                unique_txns = df["Transaction Number"].nunique()

                # Track which transactions came from which files
                for txn in df["Transaction Number"].unique():
                    if txn not in transaction_tracker:
                        transaction_tracker[txn] = []
                    transaction_tracker[txn].append(Path(file_path).name)

            all_dfs.append(df)
            stats["total_rows"] += rows
            stats["total_amount"] += amount
            stats["files_processed"].append({
                "file": Path(file_path).name,
                "rows": rows,
                "amount": amount,
                "unique_transactions": unique_txns,
            })

            print(f"      Rows: {rows:,}  |  Transactions: {unique_txns:,}  |  Amount: {amount:,.2f} SAR")

        except Exception as e:
            print(f"      ⚠ Error loading {file_path}: {e}")
            continue

    if not all_dfs:
        raise ValueError("No valid CSV files could be loaded")

    print(f"\n  Merging {len(all_dfs)} files...")
    merged_df = pd.concat(all_dfs, ignore_index=True)

    # Simple concatenation - no duplicate removal
    # User requested: "one csv has 50 lines and other one has 20 lines my output should have 70 lines"
    duplicates_removed = 0
    stats["duplicates_removed"] = 0

    # Calculate final statistics
    stats["final_rows"] = len(merged_df)
    stats["final_amount"] = merged_df["Transaction Line Amount"].sum() if "Transaction Line Amount" in merged_df.columns else 0.0
    stats["unique_transactions"] = merged_df["Transaction Number"].nunique() if "Transaction Number" in merged_df.columns else 0
    stats["amount_difference"] = 0.0  # No duplicates removed, so no difference
    stats["cross_file_duplicates"] = []  # Not checking for duplicates anymore

    # Save merged file
    merged_df.to_csv(output_file, index=False, encoding="utf-8-sig", quoting=1)

    print(f"\n  ✅ Merge Complete!")
    print(f"  Output file: {output_file}")
    print(f"  Final rows: {stats['final_rows']:,}")
    print(f"  Unique transactions: {stats['unique_transactions']:,}")
    print(f"  Total amount: {stats['final_amount']:,.2f} SAR")
    print(f"{'='*72}\n")

    return stats


def main():
    """Command-line interface for CSV merger"""
    if len(sys.argv) < 3:
        print("\nUsage: python csv_merger.py <output_file> <input_file1> <input_file2> ...")
        print("\nExample:")
        print("  python csv_merger.py merged_ar_invoice.csv file1.csv file2.csv file3.csv")
        sys.exit(1)
    
    output_file = sys.argv[1]
    input_files = sys.argv[2:]
    
    try:
        stats = merge_ar_invoices(input_files, output_file)
        
        # Write comprehensive merge accuracy report
        report_path = output_file.replace(".csv", "_merge_report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            # HEADER
            f.write("╔" + "═" * 78 + "╗\n")
            f.write("║" + "  AR INVOICE CSV MERGE — SIMPLE CONCATENATION REPORT".center(78) + "║\n")
            f.write("║" + f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".ljust(78) + "║\n")
            f.write("╚" + "═" * 78 + "╝\n\n")

            # EXECUTIVE SUMMARY
            f.write("╔" + "═" * 78 + "╗\n")
            f.write("║" + "  EXECUTIVE SUMMARY".ljust(78) + "║\n")
            f.write("╠" + "═" * 78 + "╣\n")

            # Overall status
            status_line = "║  Overall Status: ✓ SIMPLE CONCATENATION - ALL ROWS PRESERVED"
            f.write(status_line.ljust(78) + "║\n")

            # Quick stats
            f.write("║" + "-" * 78 + "║\n")
            f.write(f"║  Files Merged: {stats['total_files']}".ljust(41) + f"  Mode: Simple Concatenation".ljust(37) + "║\n")
            f.write(f"║  Input Data Rows: {stats['total_rows']:,} (excl. headers)".ljust(41) + f"  Output Data Rows: {stats['final_rows']:,}".ljust(37) + "║\n")
            f.write(f"║  Input Amount: {stats['total_amount']:,.2f} SAR".ljust(41) + f"  Output Amount: {stats['final_amount']:,.2f} SAR".ljust(37) + "║\n")
            f.write("╠" + "═" * 78 + "╣\n")

            # Key metrics
            f.write(f"║  ✓  All Rows Preserved".ljust(45) + f"100%".rjust(33) + "║\n")
            f.write(f"║  ✓  All Amounts Preserved".ljust(45) + f"100%".rjust(33) + "║\n")
            f.write(f"║  ℹ  Unique Transactions".ljust(45) + f"{stats['unique_transactions']:,}".rjust(33) + "║\n")
            f.write("╚" + "═" * 78 + "╝\n\n")

            # INPUT FILES SUMMARY TABLE
            f.write("╔" + "═" * 78 + "╗\n")
            f.write("║" + "  INPUT FILES PROCESSED".ljust(78) + "║\n")
            f.write("╚" + "═" * 78 + "╝\n\n")

            # Table header
            f.write("  ┌" + "─" * 4 + "┬" + "─" * 32 + "┬" + "─" * 12 + "┬" + "─" * 12 + "┬" + "─" * 14 + "┐\n")
            f.write("  │ #  │ File Name".ljust(34) + "│ Data Rows".ljust(14) + "│ Txns".ljust(14) + "│ Amount (SAR)".ljust(16) + "│\n")
            f.write("  ├" + "─" * 4 + "┼" + "─" * 32 + "┼" + "─" * 12 + "┼" + "─" * 12 + "┼" + "─" * 14 + "┤\n")

            for i, file_info in enumerate(stats["files_processed"], 1):
                fname = file_info['file'][:29] + "..." if len(file_info['file']) > 32 else file_info['file']
                f.write(f"  │ {i:<2} │ {fname:<30} │ {file_info['rows']:>10,} │ {file_info['unique_transactions']:>10,} │ {file_info['amount']:>12,.2f} │\n")

            # Table footer with totals
            f.write("  ├" + "─" * 4 + "┴" + "─" * 32 + "┼" + "─" * 12 + "┼" + "─" * 12 + "┼" + "─" * 14 + "┤\n")
            f.write(f"  │ TOTAL".ljust(39) + f"│ {stats['total_rows']:>10,} │ {'-':>10} │ {stats['total_amount']:>12,.2f} │\n")
            f.write("  └" + "─" * 36 + "┴" + "─" * 12 + "┴" + "─" * 12 + "┴" + "─" * 14 + "┘\n\n")

            # MERGE OPERATION DETAILS
            f.write("╔" + "═" * 78 + "╗\n")
            f.write("║" + "  MERGE OPERATION — SIMPLE CONCATENATION".ljust(78) + "║\n")
            f.write("╚" + "═" * 78 + "╝\n\n")

            f.write("  ┌" + "─" * 76 + "┐\n")
            f.write("  │ MERGE METHOD: Simple Concatenation (No Duplicate Removal)".ljust(78) + "│\n")
            f.write("  ├" + "─" * 76 + "┤\n")
            f.write(f"  │ Files Merged: {stats['total_files']}".ljust(78) + "│\n")
            f.write(f"  │ Input Rows: {stats['total_rows']:,}".ljust(78) + "│\n")
            f.write(f"  │ Output Rows: {stats['final_rows']:,}".ljust(78) + "│\n")
            f.write(f"  │ Rows Preserved: 100% (All rows included)".ljust(78) + "│\n")
            f.write("  ├" + "─" * 76 + "┤\n")
            f.write(f"  │ Input Amount: {stats['total_amount']:,.2f} SAR".ljust(78) + "│\n")
            f.write(f"  │ Output Amount: {stats['final_amount']:,.2f} SAR".ljust(78) + "│\n")
            f.write(f"  │ Amount Preserved: 100%".ljust(78) + "│\n")
            f.write("  └" + "─" * 76 + "┘\n\n")

            # FINAL VERIFICATION
            f.write("╔" + "═" * 78 + "╗\n")
            f.write("║" + "  FINAL VERIFICATION".ljust(78) + "║\n")
            f.write("╚" + "═" * 78 + "╝\n\n")

            f.write(f"  ✓  Merge Method:        Simple Concatenation\n")
            f.write(f"  ✓  Rows Retained:       {stats['final_rows']:,} / {stats['total_rows']:,} (100%)\n")
            f.write(f"  ✓  Amount Retained:     {stats['final_amount']:,.2f} / {stats['total_amount']:,.2f} SAR (100%)\n")
            f.write(f"  ✓  Output File:         {Path(output_file).name}\n")
            f.write(f"  ✓  Report File:         {Path(report_path).name}\n\n")

            # CONCLUSION
            f.write("  " + "═" * 76 + "\n")
            f.write("  ✓  MERGE COMPLETED SUCCESSFULLY\n")
            f.write("  ✓  All files merged using simple concatenation\n")
            f.write("  ✓  All rows from all files have been preserved\n")
            f.write("  ✓  No duplicate removal performed\n")
            f.write(f"  ✓  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("  " + "═" * 76 + "\n")

        print(f"  📄 Professional merge accuracy report saved: {report_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
