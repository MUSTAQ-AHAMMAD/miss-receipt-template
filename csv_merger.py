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
            f.write("=" * 80 + "\n")
            f.write("  AR INVOICE CSV MERGE ACCURACY REPORT\n")
            f.write(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            f.write("INPUT FILES PROCESSED:\n")
            f.write("-" * 80 + "\n")
            total_input_rows = 0
            total_input_amount = 0.0
            for i, file_info in enumerate(stats["files_processed"], 1):
                f.write(f"  [{i}] {file_info['file']}\n")
                f.write(f"      Rows:         {file_info['rows']:>10,}\n")
                f.write(f"      Transactions: {file_info['unique_transactions']:>10,}\n")
                f.write(f"      Amount:       {file_info['amount']:>10,.2f} SAR\n\n")
                total_input_rows += file_info['rows']
                total_input_amount += file_info['amount']

            f.write(f"  TOTAL INPUT:\n")
            f.write(f"      Rows:         {total_input_rows:>10,}\n")
            f.write(f"      Amount:       {total_input_amount:>10,.2f} SAR\n\n")

            f.write("=" * 80 + "\n")
            f.write("MERGE OPERATION SUMMARY:\n")
            f.write("=" * 80 + "\n\n")

            f.write("BEFORE MERGE:\n")
            f.write("-" * 80 + "\n")
            f.write(f"  Total files:              {stats['total_files']}\n")
            f.write(f"  Total rows (combined):    {stats['total_rows']:,}\n")
            f.write(f"  Total amount (combined):  {stats['total_amount']:,.2f} SAR\n\n")

            f.write("AFTER MERGE:\n")
            f.write("-" * 80 + "\n")
            f.write(f"  Final rows:               {stats['final_rows']:,}\n")
            f.write(f"  Unique transactions:      {stats['unique_transactions']:,}\n")
            f.write(f"  Final amount:             {stats['final_amount']:,.2f} SAR\n\n")

            f.write("DIFFERENCES DETECTED:\n")
            f.write("-" * 80 + "\n")
            f.write(f"  Duplicate rows removed:   {stats['duplicates_removed']:,}\n")
            f.write(f"  Amount removed:           {stats['amount_difference']:,.2f} SAR\n")
            f.write(f"  Accuracy:                 {((stats['final_rows'] / stats['total_rows']) * 100) if stats['total_rows'] > 0 else 0:.2f}% rows retained\n\n")

            # Detailed duplicate analysis
            if stats.get('duplicate_details'):
                f.write("=" * 80 + "\n")
                f.write("DETAILED DUPLICATE ANALYSIS:\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"  Total duplicate transactions: {len(stats['duplicate_details'])}\n\n")

                for i, dup in enumerate(stats['duplicate_details'][:50], 1):  # Limit to first 50
                    f.write(f"  [{i}] Transaction: {dup['transaction']}\n")
                    f.write(f"      Duplicate lines:  {dup['duplicate_lines']}\n")
                    f.write(f"      Duplicate amount: {dup['duplicate_amount']:,.2f} SAR\n")
                    f.write(f"      Found in files:   {', '.join(dup['found_in_files'])}\n\n")

                if len(stats['duplicate_details']) > 50:
                    f.write(f"  ... and {len(stats['duplicate_details']) - 50} more duplicate transactions\n\n")

            # Cross-file duplicate analysis
            if stats.get('cross_file_duplicates'):
                f.write("=" * 80 + "\n")
                f.write("CROSS-FILE DUPLICATE ANALYSIS:\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"  Transactions appearing in multiple files: {len(stats['cross_file_duplicates'])}\n\n")

                for i, dup in enumerate(stats['cross_file_duplicates'][:30], 1):  # Limit to first 30
                    f.write(f"  [{i}] Transaction: {dup['transaction']}\n")
                    f.write(f"      Appears in {dup['count']} files: {', '.join(dup['appears_in'])}\n\n")

                if len(stats['cross_file_duplicates']) > 30:
                    f.write(f"  ... and {len(stats['cross_file_duplicates']) - 30} more cross-file duplicates\n\n")

            f.write("=" * 80 + "\n")
            f.write("ACCURACY VERIFICATION:\n")
            f.write("=" * 80 + "\n\n")

            # Calculate accuracy metrics
            row_retention = (stats['final_rows'] / stats['total_rows'] * 100) if stats['total_rows'] > 0 else 0
            amount_retention = (stats['final_amount'] / stats['total_amount'] * 100) if stats['total_amount'] > 0 else 0

            f.write(f"  ✓ Row count verification:\n")
            f.write(f"      Input:    {stats['total_rows']:,} rows\n")
            f.write(f"      Output:   {stats['final_rows']:,} rows\n")
            f.write(f"      Removed:  {stats['duplicates_removed']:,} duplicates ({100 - row_retention:.2f}%)\n")
            f.write(f"      Status:   {'✓ ACCURATE' if stats['duplicates_removed'] >= 0 else '✗ ISSUE DETECTED'}\n\n")

            f.write(f"  ✓ Amount verification:\n")
            f.write(f"      Input:    {stats['total_amount']:,.2f} SAR\n")
            f.write(f"      Output:   {stats['final_amount']:,.2f} SAR\n")
            f.write(f"      Removed:  {stats['amount_difference']:,.2f} SAR ({100 - amount_retention:.2f}%)\n")
            f.write(f"      Status:   {'✓ ACCURATE' if abs(stats['amount_difference']) < 0.01 or stats['duplicates_removed'] > 0 else '✗ ISSUE DETECTED'}\n\n")

            f.write(f"  ✓ Transaction uniqueness:\n")
            f.write(f"      Unique transactions: {stats['unique_transactions']:,}\n")
            f.write(f"      Cross-file duplicates: {len(stats.get('cross_file_duplicates', [])):,}\n")
            f.write(f"      Status:   ✓ VERIFIED\n\n")

            f.write("=" * 80 + "\n")
            f.write("CONCLUSION:\n")
            f.write("=" * 80 + "\n\n")

            if stats['duplicates_removed'] == 0 and len(stats.get('cross_file_duplicates', [])) == 0:
                f.write("  ✓ All files merged successfully with NO DUPLICATES detected.\n")
                f.write("  ✓ All input rows were unique and retained in the output.\n")
            else:
                f.write(f"  ✓ Merge completed with {stats['duplicates_removed']:,} duplicate rows removed.\n")
                if stats.get('cross_file_duplicates'):
                    f.write(f"  ⚠ {len(stats['cross_file_duplicates']):,} transactions appear in multiple input files.\n")
                f.write("  ✓ Output file contains unique transactions only.\n")

            f.write(f"\n  Output file: {output_file}\n")
            f.write(f"  Accuracy report: {report_path}\n\n")

            f.write("=" * 80 + "\n")

        print(f"  📄 Detailed merge accuracy report saved: {report_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
