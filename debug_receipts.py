#!/usr/bin/env python3
"""
Diagnostic script to debug receipt generation issues.
Analyzes AR Invoice, Payment files, and Receipt Methods to identify problems.
"""

import pandas as pd
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def safe_str(val):
    if pd.isna(val):
        return ""
    return str(val).strip()

def safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def analyze_ar_invoice(ar_path):
    """Analyze AR Invoice file for date-wise totals."""
    print("\n" + "="*80)
    print("ANALYZING AR INVOICE FILE")
    print("="*80)

    df = pd.read_csv(ar_path, encoding='utf-8-sig', dtype=str)
    print(f"Total rows: {len(df):,}")

    # Normalize column names
    df.columns = [c.strip() for c in df.columns]

    # Group by Transaction Date
    df['Transaction Line Amount'] = df['Transaction Line Amount'].apply(safe_float)
    df['Transaction Date'] = pd.to_datetime(df['Transaction Date'], errors='coerce')

    date_totals = df.groupby(df['Transaction Date'].dt.strftime('%Y-%m-%d'))['Transaction Line Amount'].sum()

    print("\nDATE-WISE AR TOTALS:")
    print(f"{'Date':<15} {'Total Amount':>18}")
    print("-"*40)
    for date, total in sorted(date_totals.items()):
        print(f"{date:<15} {total:>18,.2f} SAR")
    print("-"*40)
    print(f"{'GRAND TOTAL':<15} {date_totals.sum():>18,.2f} SAR")

    return df, date_totals

def analyze_payment_file(payment_path):
    """Analyze payment file for date-wise totals."""
    print("\n" + "="*80)
    print("ANALYZING PAYMENT FILE")
    print("="*80)

    df = pd.read_csv(payment_path, encoding='utf-8-sig', dtype=str)
    print(f"Total payment rows: {len(df):,}")

    # Normalize columns
    df.columns = [c.strip() for c in df.columns]

    # Find date and amount columns
    date_col = None
    amount_col = None

    for col in df.columns:
        if 'date' in col.lower() and date_col is None:
            date_col = col
        if 'amount' in col.lower() and amount_col is None:
            amount_col = col

    if not date_col or not amount_col:
        print(f"⚠ Could not find date/amount columns")
        print(f"Available columns: {list(df.columns)}")
        return None, None

    print(f"Using date column: {date_col}")
    print(f"Using amount column: {amount_col}")

    df[amount_col] = df[amount_col].apply(safe_float)
    df['parsed_date'] = pd.to_datetime(df[date_col], errors='coerce')

    date_totals = df.groupby(df['parsed_date'].dt.strftime('%Y-%m-%d'))[amount_col].sum()

    print("\nDATE-WISE PAYMENT TOTALS:")
    print(f"{'Date':<15} {'Total Amount':>18}")
    print("-"*40)
    for date, total in sorted(date_totals.items()):
        print(f"{date:<15} {total:>18,.2f} SAR")
    print("-"*40)
    print(f"{'GRAND TOTAL':<15} {date_totals.sum():>18,.2f} SAR")

    return df, date_totals

def compare_date_totals(ar_totals, payment_totals):
    """Compare AR and Payment date-wise totals."""
    print("\n" + "="*80)
    print("DATE-WISE COMPARISON")
    print("="*80)

    print(f"{'Date':<15} {'AR Total':>18} {'Payment Total':>18} {'Difference':>18} {'Status':>10}")
    print("-"*90)

    all_dates = sorted(set(list(ar_totals.keys()) + list(payment_totals.keys())))

    total_diff = 0.0
    for date in all_dates:
        ar_amt = ar_totals.get(date, 0.0)
        pay_amt = payment_totals.get(date, 0.0)
        diff = ar_amt - pay_amt
        total_diff += abs(diff)
        status = "✓ MATCH" if abs(diff) < 0.01 else "⚠ DIFF"
        print(f"{date:<15} {ar_amt:>18,.2f} {pay_amt:>18,.2f} {diff:>18,.2f} {status:>10}")

    print("-"*90)
    print(f"Total absolute difference: {total_diff:,.2f} SAR")

    if total_diff < 1.0:
        print("✓ Date-wise totals MATCH (within rounding)")
    else:
        print("⚠ Date-wise totals DO NOT MATCH - investigate data")

def analyze_receipt_methods(receipt_methods_path):
    """Analyze receipt methods bank account mapping."""
    print("\n" + "="*80)
    print("ANALYZING RECEIPT METHODS")
    print("="*80)

    df = pd.read_csv(receipt_methods_path, encoding='utf-8-sig', dtype=str)
    df.columns = [c.strip() for c in df.columns]

    print(f"Total receipt method entries: {len(df):,}")

    # Group by payment method
    method_col = 'RECEIPT_METHOD_NAME'
    if method_col in df.columns:
        methods = df[method_col].value_counts()
        print("\nPayment Methods:")
        for method, count in methods.items():
            print(f"  {method}: {count} bank accounts")

    # Check for common stores
    acct_name_col = 'BANK_ACCOUNT_NAME'
    if acct_name_col in df.columns:
        print("\nSample bank account mappings:")
        for idx, row in df.head(10).iterrows():
            method = safe_str(row.get(method_col, ''))
            acct_name = safe_str(row.get(acct_name_col, ''))
            acct_num = safe_str(row.get('BANK_ACCOUNT_NUMBER', ''))
            print(f"  {method:12} -> {acct_name[:40]:40} -> {acct_num}")

    return df

def analyze_receipts_directory(receipts_dir):
    """Analyze generated receipt files."""
    print("\n" + "="*80)
    print("ANALYZING GENERATED RECEIPTS")
    print("="*80)

    receipts_path = Path(receipts_dir)
    if not receipts_path.exists():
        print(f"⚠ Receipt directory not found: {receipts_dir}")
        return

    # Find all CSV files
    receipt_files = list(receipts_path.rglob("*.csv"))
    print(f"Total receipt files found: {len(receipt_files)}")

    method_totals = defaultdict(float)
    method_counts = defaultdict(int)
    date_totals = defaultdict(float)

    for file_path in receipt_files:
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig', dtype=str)
            df.columns = [c.strip() for c in df.columns]

            if 'Amount' in df.columns:
                amount = safe_float(df['Amount'].iloc[0])

                # Extract method from filename or column
                method = None
                if 'ReceiptMethod' in df.columns:
                    method = safe_str(df['ReceiptMethod'].iloc[0])
                else:
                    # Try to extract from filename
                    name_parts = file_path.stem.split('_')
                    if len(name_parts) > 1:
                        method = name_parts[1]

                # Extract date
                date = None
                if 'ReceiptDate' in df.columns:
                    date = safe_str(df['ReceiptDate'].iloc[0])

                if method:
                    method_totals[method] += amount
                    method_counts[method] += 1

                if date:
                    date_totals[date] += amount

        except Exception as e:
            print(f"⚠ Error reading {file_path.name}: {e}")

    print("\nRECEIPT TOTALS BY METHOD:")
    print(f"{'Method':<15} {'Files':>8} {'Total Amount':>18}")
    print("-"*50)
    grand_total = 0.0
    for method in sorted(method_totals.keys()):
        amount = method_totals[method]
        count = method_counts[method]
        print(f"{method:<15} {count:>8} {amount:>18,.2f} SAR")
        grand_total += amount
    print("-"*50)
    print(f"{'GRAND TOTAL':<15} {sum(method_counts.values()):>8} {grand_total:>18,.2f} SAR")

    print("\nRECEIPT TOTALS BY DATE:")
    print(f"{'Date':<15} {'Total Amount':>18}")
    print("-"*40)
    for date in sorted(date_totals.keys()):
        print(f"{date:<15} {date_totals[date]:>18,.2f} SAR")

def main():
    print("="*80)
    print("RECEIPT GENERATION DIAGNOSTIC TOOL")
    print("="*80)

    # Find files in current directory
    base_dir = Path('.')

    # Look for AR Invoice file
    ar_files = list(base_dir.glob("AR_Invoice*.csv"))
    if ar_files:
        ar_path = ar_files[0]
        print(f"\nFound AR Invoice: {ar_path.name}")
        ar_df, ar_date_totals = analyze_ar_invoice(str(ar_path))
    else:
        print("\n⚠ No AR Invoice file found")
        ar_date_totals = None

    # Look for payment files
    payment_files = [f for f in base_dir.glob("*.xlsx") if 'payment' in f.name.lower()]
    if not payment_files:
        payment_files = [f for f in base_dir.glob("*.csv") if 'payment' in f.name.lower()]

    payment_date_totals = None
    if payment_files:
        payment_path = payment_files[0]
        print(f"\nFound Payment file: {payment_path.name}")
        try:
            if payment_path.suffix == '.xlsx':
                payment_df = pd.read_excel(payment_path, dtype=str)
                # Save as temp CSV for easier processing
                temp_csv = base_dir / "temp_payment.csv"
                payment_df.to_csv(temp_csv, index=False)
                payment_df, payment_date_totals = analyze_payment_file(str(temp_csv))
                temp_csv.unlink()  # Clean up
            else:
                payment_df, payment_date_totals = analyze_payment_file(str(payment_path))
        except Exception as e:
            print(f"⚠ Error analyzing payment file: {e}")

    # Compare if both available
    if ar_date_totals is not None and payment_date_totals is not None:
        compare_date_totals(ar_date_totals, payment_date_totals)

    # Analyze receipt methods
    receipt_methods_path = base_dir / "Receipt_Methods.csv"
    if receipt_methods_path.exists():
        analyze_receipt_methods(str(receipt_methods_path))
    else:
        print("\n⚠ Receipt_Methods.csv not found")

    # Analyze generated receipts
    receipts_dir = base_dir / "ORACLE_FUSION_OUTPUT" / "Receipts"
    if not receipts_dir.exists():
        # Try finding in upload directories
        upload_dirs = list(base_dir.glob("*/ORACLE_FUSION_OUTPUT/Receipts"))
        if upload_dirs:
            receipts_dir = upload_dirs[0]

    if receipts_dir.exists():
        analyze_receipts_directory(str(receipts_dir))
    else:
        print("\n⚠ No receipt output directory found")

if __name__ == "__main__":
    main()
