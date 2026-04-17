"""
================================================================================
COMPREHENSIVE REPORT GENERATOR
================================================================================
Generates detailed reports for generated AR Invoice and Receipt files including:
- Sub-inventory breakdown by invoice
- Total summaries
- SKU analysis
- Discount item tracking
- Data accuracy validation
================================================================================
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict
import json


class ComprehensiveReportGenerator:
    """Generate detailed reports for generated files"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_ar_invoice_report(
        self,
        ar_invoice_path: str,
        metadata_path: Optional[str] = None
    ) -> dict:
        """
        Generate comprehensive report for AR Invoice file
        
        Args:
            ar_invoice_path: Path to AR Invoice CSV
            metadata_path: Optional path to metadata CSV for enrichment
            
        Returns:
            Dictionary with report data
        """
        print(f"\n{'='*72}")
        print("  GENERATING COMPREHENSIVE AR INVOICE REPORT")
        print(f"{'='*72}\n")
        
        # Load AR Invoice
        ar_df = pd.read_csv(ar_invoice_path, encoding="utf-8-sig")
        
        report = {
            "file": Path(ar_invoice_path).name,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_rows": len(ar_df),
            "total_amount": float(ar_df["Transaction Line Amount"].sum()),
            "unique_transactions": ar_df["Transaction Number"].nunique(),
            "unique_invoices": ar_df["Sales Order Number"].nunique(),
        }
        
        # Transaction breakdown
        print("  Analyzing transactions...")
        txn_summary = ar_df.groupby("Transaction Number").agg({
            "Transaction Line Amount": "sum",
            "Sales Order Number": "first",
            "Transaction Date": "first",
        }).reset_index()
        txn_summary.columns = ["Transaction Number", "Amount", "Invoice", "Date"]
        
        # Store breakdown (from Bill-to Account)
        print("  Analyzing by store...")
        store_summary = ar_df.groupby("Bill-to Customer Account Number").agg({
            "Transaction Line Amount": "sum",
            "Transaction Number": "nunique",
            "Sales Order Number": "nunique",
        }).reset_index()
        store_summary.columns = ["Store", "Total Amount", "Transactions", "Invoices"]
        store_summary = store_summary.sort_values("Total Amount", ascending=False)
        
        # Discount items analysis
        print("  Analyzing discount items...")
        discount_items = ar_df[
            (ar_df["Memo Line Name"] == "Discount Item") |
            (ar_df["Inventory Item Number"] == "")
        ]
        regular_items = ar_df[
            (ar_df["Memo Line Name"] != "Discount Item") &
            (ar_df["Inventory Item Number"] != "")
        ]
        
        report["discount_analysis"] = {
            "discount_lines": len(discount_items),
            "discount_amount": float(discount_items["Transaction Line Amount"].sum()),
            "regular_lines": len(regular_items),
            "regular_amount": float(regular_items["Transaction Line Amount"].sum()),
            "discount_percentage": (len(discount_items) / len(ar_df) * 100) if len(ar_df) > 0 else 0,
        }
        
        # SKU analysis
        print("  Analyzing SKUs...")
        sku_summary = ar_df[ar_df["Inventory Item Number"] != ""].groupby("Inventory Item Number").agg({
            "Transaction Line Amount": "sum",
            "Transaction Line Quantity": "sum",
        }).reset_index()
        sku_summary.columns = ["SKU", "Total Amount", "Total Quantity"]
        sku_summary = sku_summary.sort_values("Total Amount", ascending=False)
        
        report["sku_analysis"] = {
            "unique_skus": len(sku_summary),
            "missing_skus": len(discount_items),
            "top_10_skus": sku_summary.head(10).to_dict("records") if len(sku_summary) > 0 else [],
        }
        
        # Invoice-level details
        print("  Generating invoice-level breakdown...")
        invoice_details = []
        for invoice_num in ar_df["Sales Order Number"].unique():
            inv_data = ar_df[ar_df["Sales Order Number"] == invoice_num]
            
            invoice_info = {
                "invoice_number": invoice_num,
                "transaction_number": inv_data["Transaction Number"].iloc[0],
                "date": inv_data["Transaction Date"].iloc[0],
                "store": inv_data["Bill-to Customer Account Number"].iloc[0],
                "total_lines": len(inv_data),
                "discount_lines": len(inv_data[inv_data["Memo Line Name"] == "Discount Item"]),
                "regular_lines": len(inv_data[inv_data["Memo Line Name"] != "Discount Item"]),
                "total_amount": float(inv_data["Transaction Line Amount"].sum()),
                "line_items": [],
            }
            
            # Add line item details
            for _, row in inv_data.iterrows():
                invoice_info["line_items"].append({
                    "description": row["Transaction Line Description"],
                    "sku": row["Inventory Item Number"],
                    "quantity": row["Transaction Line Quantity"],
                    "unit_price": row["Unit Selling Price"],
                    "amount": row["Transaction Line Amount"],
                    "is_discount": row["Memo Line Name"] == "Discount Item",
                })
            
            invoice_details.append(invoice_info)
        
        report["invoice_details"] = invoice_details
        report["store_summary"] = store_summary.to_dict("records")
        report["transaction_summary"] = txn_summary.to_dict("records")
        
        # Save report
        self._save_report(report, "AR_Invoice_Comprehensive_Report")
        
        return report
    
    def generate_receipts_report(self, receipts_dir: str) -> dict:
        """
        Generate comprehensive report for all receipt files
        
        Args:
            receipts_dir: Directory containing receipt CSV files
            
        Returns:
            Dictionary with report data
        """
        print(f"\n{'='*72}")
        print("  GENERATING COMPREHENSIVE RECEIPTS REPORT")
        print(f"{'='*72}\n")
        
        receipts_path = Path(receipts_dir)
        if not receipts_path.exists():
            raise ValueError(f"Receipts directory not found: {receipts_dir}")
        
        report = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "receipts_by_method": {},
            "total_receipts": 0,
            "total_amount": 0.0,
        }
        
        # Process each payment method folder
        for method_folder in receipts_path.glob("*"):
            if not method_folder.is_dir():
                continue
            
            method_name = method_folder.name
            print(f"  Processing {method_name} receipts...")
            
            method_stats = {
                "files": 0,
                "total_amount": 0.0,
                "receipts": [],
            }
            
            for csv_file in method_folder.glob("*.csv"):
                try:
                    df = pd.read_csv(csv_file, encoding="utf-8-sig")
                    
                    file_info = {
                        "filename": csv_file.name,
                        "rows": len(df),
                        "amount": float(df["Amount"].sum()) if "Amount" in df.columns else 0.0,
                    }
                    
                    # Extract store and date from filename
                    parts = csv_file.stem.split("_")
                    if len(parts) >= 3:
                        file_info["store"] = parts[2]
                        file_info["date"] = parts[3] if len(parts) > 3 else ""
                    
                    method_stats["files"] += 1
                    method_stats["total_amount"] += file_info["amount"]
                    method_stats["receipts"].append(file_info)
                    
                except Exception as e:
                    print(f"    ⚠ Error processing {csv_file.name}: {e}")
            
            report["receipts_by_method"][method_name] = method_stats
            report["total_receipts"] += method_stats["files"]
            report["total_amount"] += method_stats["total_amount"]
        
        # Save report
        self._save_report(report, "Receipts_Comprehensive_Report")
        
        return report
    
    def generate_sub_inventory_report(
        self,
        ar_invoice_path: str,
        metadata_path: str
    ) -> dict:
        """
        Generate sub-inventory report with invoice-wise and total breakdown
        
        Args:
            ar_invoice_path: Path to AR Invoice CSV
            metadata_path: Path to metadata CSV with sub-inventory mapping
            
        Returns:
            Dictionary with sub-inventory analysis
        """
        print(f"\n{'='*72}")
        print("  GENERATING SUB-INVENTORY REPORT")
        print(f"{'='*72}\n")
        
        # Load files
        ar_df = pd.read_csv(ar_invoice_path, encoding="utf-8-sig")
        metadata_df = pd.read_csv(metadata_path, encoding="utf-8-sig")
        
        # Normalize column names
        metadata_df.columns = [c.strip().upper() for c in metadata_df.columns]
        
        # Create mapping from Bill-to Account to Subinventory
        subinv_map = {}
        for _, row in metadata_df.iterrows():
            account = str(row.get("BILL_TO_ACCOUNT", "")).strip()
            subinv = str(row.get("SUBINVENTORY", "")).strip()
            if account and subinv:
                subinv_map[account] = subinv
        
        print(f"  Loaded {len(subinv_map)} sub-inventory mappings")
        
        # Add sub-inventory column to AR data
        ar_df["SubInventory"] = ar_df["Bill-to Customer Account Number"].map(subinv_map)
        
        report = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_invoices": ar_df["Sales Order Number"].nunique(),
            "total_amount": float(ar_df["Transaction Line Amount"].sum()),
        }
        
        # Invoice-wise breakdown
        print("  Generating invoice-wise sub-inventory breakdown...")
        invoice_subinv = []
        
        for invoice_num in ar_df["Sales Order Number"].unique():
            inv_data = ar_df[ar_df["Sales Order Number"] == invoice_num]
            subinv = inv_data["SubInventory"].iloc[0] if len(inv_data) > 0 else "UNKNOWN"
            
            invoice_subinv.append({
                "invoice": invoice_num,
                "sub_inventory": subinv,
                "store": inv_data["Bill-to Customer Account Number"].iloc[0],
                "date": inv_data["Transaction Date"].iloc[0],
                "lines": len(inv_data),
                "amount": float(inv_data["Transaction Line Amount"].sum()),
            })
        
        # Total by sub-inventory
        print("  Generating total sub-inventory summary...")
        subinv_totals = ar_df.groupby("SubInventory").agg({
            "Transaction Line Amount": "sum",
            "Sales Order Number": "nunique",
            "Transaction Number": "nunique",
        }).reset_index()
        subinv_totals.columns = ["SubInventory", "Total Amount", "Invoices", "Transactions"]
        subinv_totals = subinv_totals.sort_values("Total Amount", ascending=False)
        
        report["invoice_wise"] = invoice_subinv
        report["subinventory_totals"] = subinv_totals.to_dict("records")
        
        # Save report
        self._save_report(report, "SubInventory_Report")
        
        return report
    
    def _save_report(self, report_data: dict, report_name: str):
        """Save report as both JSON and formatted text"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON
        json_path = self.output_dir / f"{report_name}_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)
        print(f"\n  ✅ JSON report saved: {json_path}")
        
        # Save formatted text
        txt_path = self.output_dir / f"{report_name}_{timestamp}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            self._write_formatted_report(f, report_data, report_name)
        print(f"  ✅ Text report saved: {txt_path}")
    
    def _write_formatted_report(self, f, data: dict, title: str):
        """Write formatted text report"""
        f.write("=" * 72 + "\n")
        f.write(f"  {title.upper().replace('_', ' ')}\n")
        f.write(f"  Generated: {data.get('generated_at', '')}\n")
        f.write("=" * 72 + "\n\n")
        
        # Write summary statistics
        if "total_rows" in data:
            f.write("SUMMARY:\n")
            f.write("-" * 72 + "\n")
            f.write(f"  Total rows: {data['total_rows']:,}\n")
            f.write(f"  Total amount: {data['total_amount']:,.2f} SAR\n")
            f.write(f"  Unique transactions: {data.get('unique_transactions', 0):,}\n")
            f.write(f"  Unique invoices: {data.get('unique_invoices', 0):,}\n\n")
        
        # Write discount analysis
        if "discount_analysis" in data:
            disc = data["discount_analysis"]
            f.write("DISCOUNT ITEMS ANALYSIS:\n")
            f.write("-" * 72 + "\n")
            f.write(f"  Discount lines: {disc['discount_lines']:,}\n")
            f.write(f"  Discount amount: {disc['discount_amount']:,.2f} SAR\n")
            f.write(f"  Regular lines: {disc['regular_lines']:,}\n")
            f.write(f"  Regular amount: {disc['regular_amount']:,.2f} SAR\n")
            f.write(f"  Discount percentage: {disc['discount_percentage']:.2f}%\n\n")
        
        # Write SKU analysis
        if "sku_analysis" in data:
            sku = data["sku_analysis"]
            f.write("SKU ANALYSIS:\n")
            f.write("-" * 72 + "\n")
            f.write(f"  Unique SKUs: {sku['unique_skus']:,}\n")
            f.write(f"  Missing SKUs (discount items): {sku['missing_skus']:,}\n\n")
            
            if sku.get("top_10_skus"):
                f.write("  Top 10 SKUs by Amount:\n")
                for i, item in enumerate(sku["top_10_skus"], 1):
                    f.write(f"    {i:2d}. {item['SKU']:<20} "
                           f"Qty: {item['Total Quantity']:8.0f}  "
                           f"Amount: {item['Total Amount']:12,.2f} SAR\n")
                f.write("\n")
        
        # Write sub-inventory totals
        if "subinventory_totals" in data:
            f.write("SUB-INVENTORY TOTALS:\n")
            f.write("-" * 72 + "\n")
            for item in data["subinventory_totals"]:
                f.write(f"  {item['SubInventory']:<30} "
                       f"Invoices: {item['Invoices']:5,}  "
                       f"Amount: {item['Total Amount']:12,.2f} SAR\n")
            f.write("\n")
        
        # Write receipts by method
        if "receipts_by_method" in data:
            f.write("RECEIPTS BY PAYMENT METHOD:\n")
            f.write("-" * 72 + "\n")
            for method, stats in data["receipts_by_method"].items():
                f.write(f"  {method}:\n")
                f.write(f"    Files: {stats['files']:,}\n")
                f.write(f"    Total Amount: {stats['total_amount']:,.2f} SAR\n\n")


def main():
    """Command-line interface for report generator"""
    import sys
    
    if len(sys.argv) < 3:
        print("\nUsage:")
        print("  python report_generator.py ar <ar_invoice.csv> [metadata.csv]")
        print("  python report_generator.py receipts <receipts_directory>")
        print("  python report_generator.py subinv <ar_invoice.csv> <metadata.csv>")
        sys.exit(1)
    
    report_type = sys.argv[1]
    generator = ComprehensiveReportGenerator("REPORTS")
    
    try:
        if report_type == "ar":
            ar_path = sys.argv[2]
            metadata_path = sys.argv[3] if len(sys.argv) > 3 else None
            generator.generate_ar_invoice_report(ar_path, metadata_path)
            
        elif report_type == "receipts":
            receipts_dir = sys.argv[2]
            generator.generate_receipts_report(receipts_dir)
            
        elif report_type == "subinv":
            if len(sys.argv) < 4:
                print("Error: subinv requires both AR invoice and metadata files")
                sys.exit(1)
            ar_path = sys.argv[2]
            metadata_path = sys.argv[3]
            generator.generate_sub_inventory_report(ar_path, metadata_path)
            
        else:
            print(f"Unknown report type: {report_type}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
