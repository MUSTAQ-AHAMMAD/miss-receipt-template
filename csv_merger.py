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
    }
    
    print(f"\n{'='*72}")
    print("  AR INVOICE CSV MERGER")
    print(f"{'='*72}\n")
    
    for i, file_path in enumerate(input_files, 1):
        try:
            print(f"  [{i}/{len(input_files)}] Loading: {Path(file_path).name}")
            df = pd.read_csv(file_path, encoding="utf-8-sig")
            
            rows = len(df)
            amount = df["Transaction Line Amount"].sum() if "Transaction Line Amount" in df.columns else 0.0
            
            all_dfs.append(df)
            stats["total_rows"] += rows
            stats["total_amount"] += amount
            stats["files_processed"].append({
                "file": Path(file_path).name,
                "rows": rows,
                "amount": amount,
            })
            
            print(f"      Rows: {rows:,}  |  Amount: {amount:,.2f} SAR")
            
        except Exception as e:
            print(f"      ⚠ Error loading {file_path}: {e}")
            continue
    
    if not all_dfs:
        raise ValueError("No valid CSV files could be loaded")
    
    print(f"\n  Merging {len(all_dfs)} files...")
    merged_df = pd.concat(all_dfs, ignore_index=True)
    
    # Remove duplicates based on Transaction Number and Line Description
    if "Transaction Number" in merged_df.columns:
        before_dedup = len(merged_df)
        merged_df = merged_df.drop_duplicates(
            subset=["Transaction Number", "Transaction Line Description"],
            keep="first"
        )
        after_dedup = len(merged_df)
        duplicates_removed = before_dedup - after_dedup
        if duplicates_removed > 0:
            print(f"  Removed {duplicates_removed:,} duplicate rows")
    
    # Calculate final statistics
    stats["final_rows"] = len(merged_df)
    stats["final_amount"] = merged_df["Transaction Line Amount"].sum() if "Transaction Line Amount" in merged_df.columns else 0.0
    stats["unique_transactions"] = merged_df["Transaction Number"].nunique() if "Transaction Number" in merged_df.columns else 0
    
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
        
        # Write merge report
        report_path = output_file.replace(".csv", "_merge_report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("=" * 72 + "\n")
            f.write("  AR INVOICE CSV MERGE REPORT\n")
            f.write(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 72 + "\n\n")
            
            f.write("FILES PROCESSED:\n")
            f.write("-" * 72 + "\n")
            for file_info in stats["files_processed"]:
                f.write(f"  {file_info['file']}\n")
                f.write(f"    Rows: {file_info['rows']:,}\n")
                f.write(f"    Amount: {file_info['amount']:,.2f} SAR\n\n")
            
            f.write("MERGE SUMMARY:\n")
            f.write("-" * 72 + "\n")
            f.write(f"  Total files processed: {stats['total_files']}\n")
            f.write(f"  Total rows (before merge): {stats['total_rows']:,}\n")
            f.write(f"  Final rows (after dedup): {stats['final_rows']:,}\n")
            f.write(f"  Unique transactions: {stats['unique_transactions']:,}\n")
            f.write(f"  Total amount: {stats['final_amount']:,.2f} SAR\n")
        
        print(f"  📄 Merge report saved: {report_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
