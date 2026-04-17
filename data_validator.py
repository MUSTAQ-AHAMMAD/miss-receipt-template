"""
================================================================================
DATA VALIDATION AND ACCURACY CHECKER
================================================================================
Validates generated AR Invoice and Receipt files for accuracy and consistency.
Checks for:
- Total amount matching
- SKU consistency
- Discount item proper handling
- Invoice number sequences
- Data integrity
================================================================================
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class DataValidator:
    """Comprehensive data validation for generated files"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.validations = []
    
    def validate_ar_invoice(
        self,
        ar_invoice_path: str,
        source_file_path: str = None
    ) -> dict:
        """
        Validate AR Invoice file for accuracy
        
        Args:
            ar_invoice_path: Path to generated AR Invoice CSV
            source_file_path: Optional path to source sales data for comparison
            
        Returns:
            Dictionary with validation results
        """
        print(f"\n{'='*72}")
        print("  AR INVOICE VALIDATION")
        print(f"{'='*72}\n")
        
        # Load AR Invoice
        ar_df = pd.read_csv(ar_invoice_path, encoding="utf-8-sig")
        
        results = {
            "file": Path(ar_invoice_path).name,
            "validated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_rows": len(ar_df),
            "issues": [],
            "warnings": [],
            "validations": [],
        }
        
        # Validation 1: Check for empty critical fields
        print("  [1/8] Checking critical fields...")
        critical_fields = {
            "Transaction Number": "Transaction numbers",
            "Bill-to Customer Account Number": "Bill-to accounts",
            "Transaction Line Amount": "Line amounts",
        }
        
        for field, desc in critical_fields.items():
            if field in ar_df.columns:
                empty_count = ar_df[field].isna().sum() + (ar_df[field] == "").sum()
                if empty_count > 0:
                    results["issues"].append(f"{empty_count} rows with empty {desc}")
                else:
                    results["validations"].append(f"✓ All {desc} populated")
        
        # Validation 2: Check SKU/Discount item consistency
        print("  [2/8] Validating SKU and discount items...")
        discount_items = ar_df[
            (ar_df["Memo Line Name"] == "Discount Item") |
            (ar_df["Inventory Item Number"] == "")
        ]
        
        # Check that discount items have empty SKU
        discount_with_sku = discount_items[discount_items["Inventory Item Number"] != ""]
        if len(discount_with_sku) > 0:
            results["issues"].append(
                f"{len(discount_with_sku)} discount items incorrectly have SKU values"
            )
        else:
            results["validations"].append(f"✓ All discount items have empty SKU")
        
        # Check that regular items have SKU
        regular_items = ar_df[ar_df["Memo Line Name"] != "Discount Item"]
        regular_without_sku = regular_items[regular_items["Inventory Item Number"] == ""]
        if len(regular_without_sku) > 0:
            results["warnings"].append(
                f"{len(regular_without_sku)} regular items missing SKU/barcode"
            )
        
        results["validations"].append(
            f"✓ {len(discount_items)} discount items, "
            f"{len(regular_items) - len(regular_without_sku)} regular items with SKU"
        )
        
        # Validation 3: Check amount/quantity sign consistency
        print("  [3/8] Checking amount and quantity sign consistency...")
        inconsistent_signs = 0
        for _, row in ar_df.iterrows():
            qty = row["Transaction Line Quantity"]
            amt = row["Transaction Line Amount"]
            if (qty > 0 and amt < 0) or (qty < 0 and amt > 0):
                inconsistent_signs += 1
        
        if inconsistent_signs > 0:
            results["issues"].append(
                f"{inconsistent_signs} rows with inconsistent amount/quantity signs"
            )
        else:
            results["validations"].append("✓ Amount and quantity signs are consistent")
        
        # Validation 4: Check transaction number sequence
        print("  [4/8] Validating transaction number sequence...")
        txn_nums = ar_df["Transaction Number"].unique()
        blk_nums = []
        for txn in txn_nums:
            if txn.startswith("BLK-"):
                try:
                    num = int(txn.replace("BLK-", ""))
                    blk_nums.append(num)
                except:
                    pass
        
        if blk_nums:
            blk_nums_sorted = sorted(blk_nums)
            gaps = []
            for i in range(len(blk_nums_sorted) - 1):
                if blk_nums_sorted[i+1] - blk_nums_sorted[i] > 1:
                    gaps.append((blk_nums_sorted[i], blk_nums_sorted[i+1]))
            
            if gaps:
                results["warnings"].append(
                    f"{len(gaps)} gaps in transaction number sequence"
                )
            else:
                results["validations"].append("✓ Transaction numbers are sequential")
            
            results["validations"].append(
                f"✓ Transaction range: BLK-{min(blk_nums):07d} to BLK-{max(blk_nums):07d}"
            )
        
        # Validation 5: Check for duplicate transaction numbers
        print("  [5/8] Checking for duplicates...")
        dup_txns = ar_df[ar_df.duplicated(subset=["Transaction Number", "Transaction Line Description"], keep=False)]
        if len(dup_txns) > 0:
            results["issues"].append(f"{len(dup_txns)} potential duplicate lines found")
        else:
            results["validations"].append("✓ No duplicate transaction lines")
        
        # Validation 6: Validate amounts
        print("  [6/8] Validating amounts...")
        total_amount = ar_df["Transaction Line Amount"].sum()
        results["validations"].append(f"✓ Total amount: {total_amount:,.2f} SAR")
        
        # Check for zero amounts
        zero_amt_lines = len(ar_df[ar_df["Transaction Line Amount"] == 0])
        if zero_amt_lines > 0:
            results["warnings"].append(f"{zero_amt_lines} lines with zero amount")
        
        # Validation 7: Check segment uniqueness
        print("  [7/8] Checking flexfield segments...")
        if "Line Transactions Flexfield Segment 1" in ar_df.columns:
            seg1_unique = ar_df["Line Transactions Flexfield Segment 1"].nunique()
            seg2_unique = ar_df["Line Transactions Flexfield Segment 2"].nunique()
            
            if seg1_unique == len(ar_df):
                results["validations"].append("✓ Segment 1 values are unique")
            else:
                results["issues"].append(
                    f"Segment 1 has {len(ar_df) - seg1_unique} duplicate values"
                )
            
            if seg2_unique == len(ar_df):
                results["validations"].append("✓ Segment 2 values are unique")
            else:
                results["issues"].append(
                    f"Segment 2 has {len(ar_df) - seg2_unique} duplicate values"
                )
        
        # Validation 8: Cross-check with source file if provided
        print("  [8/8] Source file comparison...")
        if source_file_path and Path(source_file_path).exists():
            try:
                if source_file_path.endswith('.csv'):
                    source_df = pd.read_csv(source_file_path, encoding="utf-8-sig")
                else:
                    source_df = pd.read_excel(source_file_path)
                
                source_rows = len(source_df)
                ar_rows = len(ar_df)
                
                if source_rows == ar_rows:
                    results["validations"].append(
                        f"✓ Row count matches source: {source_rows:,}"
                    )
                else:
                    results["issues"].append(
                        f"Row count mismatch: Source={source_rows:,}, AR={ar_rows:,}"
                    )
                
                # Try to match amounts if possible
                amount_cols = [c for c in source_df.columns 
                              if 'subtotal' in c.lower() or 'amount' in c.lower()]
                if amount_cols:
                    source_total = source_df[amount_cols[0]].sum()
                    diff = abs(total_amount - source_total)
                    if diff < 0.01:
                        results["validations"].append(
                            f"✓ Amount matches source: {source_total:,.2f} SAR"
                        )
                    else:
                        results["warnings"].append(
                            f"Amount difference: {diff:,.2f} SAR from source"
                        )
            except Exception as e:
                results["warnings"].append(f"Could not validate against source: {e}")
        else:
            results["validations"].append("ℹ No source file provided for comparison")
        
        # Summary
        print(f"\n  {'='*70}")
        print(f"  VALIDATION SUMMARY")
        print(f"  {'='*70}")
        print(f"  ✓ Validations passed: {len(results['validations'])}")
        print(f"  ⚠ Warnings:          {len(results['warnings'])}")
        print(f"  ✗ Issues found:      {len(results['issues'])}")
        print(f"  {'='*70}\n")
        
        return results
    
    def validate_receipts(
        self,
        receipts_dir: str,
        ar_invoice_path: str = None
    ) -> dict:
        """
        Validate receipt files for accuracy
        
        Args:
            receipts_dir: Directory containing receipt CSV files
            ar_invoice_path: Optional AR Invoice path for cross-validation
            
        Returns:
            Dictionary with validation results
        """
        print(f"\n{'='*72}")
        print("  RECEIPTS VALIDATION")
        print(f"{'='*72}\n")
        
        results = {
            "validated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": 0,
            "total_amount": 0.0,
            "issues": [],
            "warnings": [],
            "validations": [],
        }
        
        receipts_path = Path(receipts_dir)
        if not receipts_path.exists():
            results["issues"].append(f"Receipts directory not found: {receipts_dir}")
            return results
        
        # Process receipt files
        receipt_files = list(receipts_path.rglob("*.csv"))
        results["total_files"] = len(receipt_files)
        
        print(f"  Found {len(receipt_files)} receipt files")
        
        for csv_file in receipt_files:
            try:
                df = pd.read_csv(csv_file, encoding="utf-8-sig")
                
                # Check required columns
                if "Amount" not in df.columns:
                    results["issues"].append(f"{csv_file.name}: Missing Amount column")
                    continue
                
                file_amount = df["Amount"].sum()
                results["total_amount"] += file_amount
                
                # Check for empty amounts
                empty_amounts = df["Amount"].isna().sum()
                if empty_amounts > 0:
                    results["warnings"].append(
                        f"{csv_file.name}: {empty_amounts} rows with empty amounts"
                    )
                
            except Exception as e:
                results["issues"].append(f"{csv_file.name}: Error reading file - {e}")
        
        results["validations"].append(
            f"✓ Processed {results['total_files']} receipt files"
        )
        results["validations"].append(
            f"✓ Total receipt amount: {results['total_amount']:,.2f} SAR"
        )
        
        # Cross-check with AR Invoice if provided
        if ar_invoice_path and Path(ar_invoice_path).exists():
            try:
                ar_df = pd.read_csv(ar_invoice_path, encoding="utf-8-sig")
                ar_total = ar_df["Transaction Line Amount"].sum()
                
                # Receipts should be <= AR total (BNPL excluded)
                if results["total_amount"] <= ar_total:
                    results["validations"].append(
                        "✓ Receipt total is within AR Invoice total"
                    )
                else:
                    results["warnings"].append(
                        f"Receipt total ({results['total_amount']:,.2f}) "
                        f"exceeds AR total ({ar_total:,.2f})"
                    )
            except Exception as e:
                results["warnings"].append(f"Could not validate against AR Invoice: {e}")
        
        print(f"\n  {'='*70}")
        print(f"  VALIDATION SUMMARY")
        print(f"  {'='*70}")
        print(f"  ✓ Validations passed: {len(results['validations'])}")
        print(f"  ⚠ Warnings:          {len(results['warnings'])}")
        print(f"  ✗ Issues found:      {len(results['issues'])}")
        print(f"  {'='*70}\n")
        
        return results


def main():
    """Command-line interface"""
    import sys
    
    if len(sys.argv) < 3:
        print("\nUsage:")
        print("  python data_validator.py ar <ar_invoice.csv> [source_file]")
        print("  python data_validator.py receipts <receipts_directory> [ar_invoice.csv]")
        sys.exit(1)
    
    validator = DataValidator()
    validation_type = sys.argv[1]
    
    try:
        if validation_type == "ar":
            ar_path = sys.argv[2]
            source_path = sys.argv[3] if len(sys.argv) > 3 else None
            results = validator.validate_ar_invoice(ar_path, source_path)
            
        elif validation_type == "receipts":
            receipts_dir = sys.argv[2]
            ar_path = sys.argv[3] if len(sys.argv) > 3 else None
            results = validator.validate_receipts(receipts_dir, ar_path)
            
        else:
            print(f"Unknown validation type: {validation_type}")
            sys.exit(1)
        
        # Print detailed results
        if results.get("validations"):
            print("\nVALIDATIONS:")
            for v in results["validations"]:
                print(f"  {v}")
        
        if results.get("warnings"):
            print("\nWARNINGS:")
            for w in results["warnings"]:
                print(f"  ⚠ {w}")
        
        if results.get("issues"):
            print("\nISSUES:")
            for i in results["issues"]:
                print(f"  ✗ {i}")
        
        # Exit with error code if issues found
        if results.get("issues"):
            sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Validation error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
