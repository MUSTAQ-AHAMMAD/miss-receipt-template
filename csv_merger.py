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

    # Remove duplicates based on Transaction Number and Line Description
    duplicates_removed = 0
    if "Transaction Number" in merged_df.columns:
        before_dedup = len(merged_df)

        # Identify duplicates before removing them
        duplicate_mask = merged_df.duplicated(
            subset=["Transaction Number", "Transaction Line Description"],
            keep="first"
        )
        duplicate_rows = merged_df[duplicate_mask]

        # Track which transactions and amounts were duplicated
        if len(duplicate_rows) > 0:
            for txn_num in duplicate_rows["Transaction Number"].unique():
                dup_txn_rows = duplicate_rows[duplicate_rows["Transaction Number"] == txn_num]
                dup_amount = dup_txn_rows["Transaction Line Amount"].sum() if "Transaction Line Amount" in dup_txn_rows.columns else 0.0

                stats["duplicate_details"].append({
                    "transaction": txn_num,
                    "duplicate_lines": len(dup_txn_rows),
                    "duplicate_amount": dup_amount,
                    "found_in_files": transaction_tracker.get(txn_num, []),
                })

        # Remove duplicates
        merged_df = merged_df.drop_duplicates(
            subset=["Transaction Number", "Transaction Line Description"],
            keep="first"
        )
        after_dedup = len(merged_df)
        duplicates_removed = before_dedup - after_dedup
        stats["duplicates_removed"] = duplicates_removed

        if duplicates_removed > 0:
            print(f"  Removed {duplicates_removed:,} duplicate rows")

    # Calculate final statistics
    stats["final_rows"] = len(merged_df)
    stats["final_amount"] = merged_df["Transaction Line Amount"].sum() if "Transaction Line Amount" in merged_df.columns else 0.0
    stats["unique_transactions"] = merged_df["Transaction Number"].nunique() if "Transaction Number" in merged_df.columns else 0
    stats["amount_difference"] = stats["total_amount"] - stats["final_amount"]

    # Detect cross-file duplicates
    cross_file_duplicates = []
    for txn, files in transaction_tracker.items():
        if len(files) > 1:
            cross_file_duplicates.append({
                "transaction": txn,
                "appears_in": list(set(files)),
                "count": len(files),
            })
    stats["cross_file_duplicates"] = cross_file_duplicates

    # Save merged file
    merged_df.to_csv(output_file, index=False, encoding="utf-8-sig", quoting=1)

    print(f"\n  ✅ Merge Complete!")
    print(f"  Output file: {output_file}")
    print(f"  Final rows: {stats['final_rows']:,}")
    print(f"  Unique transactions: {stats['unique_transactions']:,}")
    print(f"  Total amount: {stats['final_amount']:,.2f} SAR")

    if stats["amount_difference"] != 0:
        print(f"  Amount removed (duplicates): {stats['amount_difference']:,.2f} SAR")

    if cross_file_duplicates:
        print(f"  Cross-file duplicates detected: {len(cross_file_duplicates):,} transactions")

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
            # Determine overall status
            has_duplicates = stats['duplicates_removed'] > 0
            has_cross_file_dups = len(stats.get('cross_file_duplicates', [])) > 0
            has_issues = has_duplicates or has_cross_file_dups

            # Calculate metrics
            row_retention = (stats['final_rows'] / stats['total_rows'] * 100) if stats['total_rows'] > 0 else 0
            amount_retention = (stats['final_amount'] / stats['total_amount'] * 100) if stats['total_amount'] > 0 else 0

            # HEADER
            f.write("╔" + "═" * 78 + "╗\n")
            f.write("║" + "  AR INVOICE CSV MERGE — ACCURACY REPORT".center(78) + "║\n")
            f.write("║" + f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".ljust(78) + "║\n")
            f.write("╚" + "═" * 78 + "╝\n\n")

            # EXECUTIVE SUMMARY
            f.write("╔" + "═" * 78 + "╗\n")
            f.write("║" + "  EXECUTIVE SUMMARY".ljust(78) + "║\n")
            f.write("╠" + "═" * 78 + "╣\n")

            # Overall status
            if not has_issues:
                status_line = "║  Overall Status: ✓ CLEAN MERGE - NO ISSUES DETECTED"
            elif has_duplicates and not has_cross_file_dups:
                status_line = "║  Overall Status: ℹ DUPLICATES REMOVED"
            else:
                status_line = "║  Overall Status: ⚠ ISSUES DETECTED"
            f.write(status_line.ljust(78) + "║\n")

            # Quick stats
            f.write("║" + "-" * 78 + "║\n")
            f.write(f"║  Files Merged: {stats['total_files']}".ljust(41) + f"  Duplicates: {stats['duplicates_removed']:,}".ljust(37) + "║\n")
            f.write(f"║  Input Rows: {stats['total_rows']:,}".ljust(41) + f"  Output Rows: {stats['final_rows']:,}".ljust(37) + "║\n")
            f.write(f"║  Input Amount: {stats['total_amount']:,.2f} SAR".ljust(41) + f"  Output Amount: {stats['final_amount']:,.2f} SAR".ljust(37) + "║\n")
            f.write("╠" + "═" * 78 + "╣\n")

            # Key metrics
            f.write(f"║  {'✓' if not has_duplicates else 'ℹ'}  Row Retention".ljust(45) + f"{row_retention:.1f}%".rjust(33) + "║\n")
            f.write(f"║  {'✓' if not has_duplicates else 'ℹ'}  Amount Retention".ljust(45) + f"{amount_retention:.1f}%".rjust(33) + "║\n")
            f.write(f"║  {'✓' if not has_cross_file_dups else '⚠'}  Cross-File Duplicates".ljust(45) + f"{len(stats.get('cross_file_duplicates', [])):,} transactions".rjust(33) + "║\n")
            f.write(f"║  ℹ  Unique Transactions".ljust(45) + f"{stats['unique_transactions']:,}".rjust(33) + "║\n")
            f.write("╚" + "═" * 78 + "╝\n\n")

            # PROBLEMS DETECTED (if any)
            if has_issues:
                f.write("  " + "█" * 76 + "\n")
                f.write("  █" + "  ⚠ PROBLEMS DETECTED — ACTION REQUIRED".center(74) + "█\n")
                f.write("  " + "█" * 76 + "\n")

                if has_duplicates:
                    f.write("  █  • DUPLICATE ROWS:".ljust(76) + "█\n")
                    f.write(f"  █      {stats['duplicates_removed']:,} duplicate rows were removed from the merge".ljust(76) + "█\n")
                    f.write(f"  █      Amount removed: {stats['amount_difference']:,.2f} SAR".ljust(76) + "█\n")
                    f.write("  █" + " " * 74 + "█\n")

                if has_cross_file_dups:
                    f.write("  █  • CROSS-FILE DUPLICATES:".ljust(76) + "█\n")
                    f.write(f"  █      {len(stats['cross_file_duplicates']):,} transactions appear in multiple input files".ljust(76) + "█\n")
                    f.write("  █      This may indicate overlapping date ranges or data export issues".ljust(76) + "█\n")
                    f.write("  █" + " " * 74 + "█\n")

                f.write("  █  RECOMMENDATION:".ljust(76) + "█\n")
                f.write("  █    → Review the duplicate transaction details below".ljust(76) + "█\n")
                f.write("  █    → Verify input files have correct date ranges".ljust(76) + "█\n")
                f.write("  █    → Check for overlapping data exports".ljust(76) + "█\n")
                f.write("  " + "█" * 76 + "\n\n")

            # INPUT FILES SUMMARY TABLE
            f.write("╔" + "═" * 78 + "╗\n")
            f.write("║" + "  INPUT FILES PROCESSED".ljust(78) + "║\n")
            f.write("╚" + "═" * 78 + "╝\n\n")

            # Table header
            f.write("  ┌" + "─" * 4 + "┬" + "─" * 32 + "┬" + "─" * 12 + "┬" + "─" * 12 + "┬" + "─" * 14 + "┐\n")
            f.write("  │ #  │ File Name".ljust(34) + "│ Rows".ljust(14) + "│ Txns".ljust(14) + "│ Amount (SAR)".ljust(16) + "│\n")
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
            f.write("║" + "  MERGE OPERATION — BEFORE & AFTER".ljust(78) + "║\n")
            f.write("╚" + "═" * 78 + "╝\n\n")

            f.write("  ┌" + "─" * 38 + "┬" + "─" * 38 + "┐\n")
            f.write("  │ BEFORE MERGE".ljust(40) + "│ AFTER MERGE".ljust(40) + "│\n")
            f.write("  ├" + "─" * 38 + "┼" + "─" * 38 + "┤\n")
            f.write(f"  │ Files: {stats['total_files']}".ljust(40) + f"│ Unique Transactions: {stats['unique_transactions']:,}".ljust(40) + "│\n")
            f.write(f"  │ Total Rows: {stats['total_rows']:,}".ljust(40) + f"│ Final Rows: {stats['final_rows']:,}".ljust(40) + "│\n")
            f.write(f"  │ Total Amount: {stats['total_amount']:,.2f} SAR".ljust(40) + f"│ Final Amount: {stats['final_amount']:,.2f} SAR".ljust(40) + "│\n")
            f.write("  ├" + "─" * 38 + "┴" + "─" * 38 + "┤\n")
            f.write(f"  │ DIFFERENCE".ljust(79) + "│\n")
            f.write("  ├" + "─" * 77 + "┤\n")
            f.write(f"  │ Rows Removed: {stats['duplicates_removed']:,} ({100 - row_retention:.2f}%)".ljust(79) + "│\n")
            f.write(f"  │ Amount Removed: {stats['amount_difference']:,.2f} SAR ({100 - amount_retention:.2f}%)".ljust(79) + "│\n")
            f.write("  └" + "─" * 77 + "┘\n\n")

            # DUPLICATE ANALYSIS (if any)
            if stats.get('duplicate_details'):
                f.write("╔" + "═" * 78 + "╗\n")
                f.write("║" + "  DUPLICATE TRANSACTIONS ANALYSIS".ljust(78) + "║\n")
                f.write("╚" + "═" * 78 + "╝\n\n")
                f.write(f"  Total duplicate transactions found: {len(stats['duplicate_details'])}\n\n")

                # Show top duplicates
                display_count = min(20, len(stats['duplicate_details']))
                f.write("  ┌" + "─" * 4 + "┬" + "─" * 20 + "┬" + "─" * 12 + "┬" + "─" * 16 + "┬" + "─" * 22 + "┐\n")
                f.write("  │ #  │ Transaction".ljust(23) + "│ Dup Lines".ljust(14) + "│ Dup Amount".ljust(18) + "│ Found in Files".ljust(25) + "│\n")
                f.write("  ├" + "─" * 4 + "┼" + "─" * 20 + "┼" + "─" * 12 + "┼" + "─" * 16 + "┼" + "─" * 22 + "┤\n")

                for i, dup in enumerate(stats['duplicate_details'][:display_count], 1):
                    txn = dup['transaction'][:17] + "..." if len(str(dup['transaction'])) > 20 else str(dup['transaction'])
                    files_str = f"{len(dup['found_in_files'])} files"
                    f.write(f"  │ {i:<2} │ {txn:<18} │ {dup['duplicate_lines']:>10} │ {dup['duplicate_amount']:>14,.2f} │ {files_str:<20} │\n")

                f.write("  └" + "─" * 4 + "┴" + "─" * 20 + "┴" + "─" * 12 + "┴" + "─" * 16 + "┴" + "─" * 22 + "┘\n")

                if len(stats['duplicate_details']) > display_count:
                    f.write(f"\n  ... and {len(stats['duplicate_details']) - display_count} more duplicate transactions\n")
                f.write("\n")

            # CROSS-FILE DUPLICATES (if any)
            if stats.get('cross_file_duplicates'):
                f.write("╔" + "═" * 78 + "╗\n")
                f.write("║" + "  CROSS-FILE DUPLICATES — TRANSACTIONS IN MULTIPLE FILES".ljust(78) + "║\n")
                f.write("╚" + "═" * 78 + "╝\n\n")
                f.write(f"  ⚠ WARNING: {len(stats['cross_file_duplicates'])} transactions appear in multiple files\n\n")

                display_count = min(15, len(stats['cross_file_duplicates']))
                for i, dup in enumerate(stats['cross_file_duplicates'][:display_count], 1):
                    f.write(f"  [{i}] {dup['transaction']}\n")
                    f.write(f"      → Appears in {dup['count']} files: {', '.join(dup['appears_in'][:3])}")
                    if len(dup['appears_in']) > 3:
                        f.write(f" + {len(dup['appears_in']) - 3} more")
                    f.write("\n\n")

                if len(stats['cross_file_duplicates']) > display_count:
                    f.write(f"  ... and {len(stats['cross_file_duplicates']) - display_count} more cross-file duplicates\n\n")

            # FINAL VERIFICATION
            f.write("╔" + "═" * 78 + "╗\n")
            f.write("║" + "  FINAL VERIFICATION".ljust(78) + "║\n")
            f.write("╚" + "═" * 78 + "╝\n\n")

            integrity_status = 'CLEAN' if not has_duplicates else f'{stats["duplicates_removed"]:,} duplicates removed'
            f.write(f"  {'✓' if not has_duplicates else 'ℹ'}  Data Integrity:    {integrity_status}\n")

            overlap_count = len(stats.get('cross_file_duplicates', []))
            overlap_status = 'NONE DETECTED' if not has_cross_file_dups else f'{overlap_count} cross-file duplicates'
            f.write(f"  {'✓' if not has_cross_file_dups else '⚠'}  File Overlap:      {overlap_status}\n")
            f.write(f"  ✓  Output File:       {Path(output_file).name}\n")
            f.write(f"  ✓  Report File:       {Path(report_path).name}\n\n")

            # CONCLUSION
            f.write("  " + "═" * 76 + "\n")
            if not has_issues:
                f.write("  ✓  MERGE COMPLETED SUCCESSFULLY\n")
                f.write("  ✓  All files merged cleanly with no duplicates detected\n")
            elif has_duplicates and not has_cross_file_dups:
                f.write("  ℹ  MERGE COMPLETED WITH DUPLICATES REMOVED\n")
                f.write(f"  ℹ  {stats['duplicates_removed']:,} duplicate rows were automatically removed\n")
                f.write("  ✓  Output file contains unique transactions only\n")
            else:
                f.write("  ⚠  MERGE COMPLETED WITH WARNINGS\n")
                f.write("  ⚠  Review duplicate transactions and cross-file overlaps above\n")
                f.write("  ℹ  Consider checking input file date ranges\n")
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
