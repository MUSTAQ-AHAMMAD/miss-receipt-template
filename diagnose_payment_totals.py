#!/usr/bin/env python3
"""
Diagnostic script to analyze payment method totals day-wise
and identify any mismatches or issues with order processing.
"""

import sys
import pandas as pd
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

def clean_order_ref(val) -> str:
    """Clean order reference like the main code does"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    s = s.replace("\ufeff", "").replace("\u200b", "").replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if s.endswith(".0") and s[:-2].replace("/", "").replace("-", "").isalnum():
        s = s[:-2]
    return s

def safe_str(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip()

def safe_float(val) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def normalise_payment(raw: str) -> str:
    """Normalize payment method names"""
    raw_upper = raw.upper().strip()

    payment_map = {
        "CASH": "Cash",
        "MADA": "Mada",
        "VISA": "Visa",
        "MASTERCARD": "MasterCard",
        "MASTER CARD": "MasterCard",
        "MASTER": "MasterCard",
        "MC": "MasterCard",
        "TAMARA": "TAMARA",
        "TABBY": "TABBY",
        "AMEX": "Amex",
        "APPLE PAY": "Apple Pay",
        "APPLEPAY": "Apple Pay",
        "STC PAY": "STC Pay",
        "STCPAY": "STC Pay",
        "GCCNET": "GCCNET",
    }

    return payment_map.get(raw_upper, raw)

def read_file(path: str) -> pd.DataFrame:
    """Read CSV or Excel file"""
    p = path.lower()
    if p.endswith(".xlsx") or p.endswith(".xls"):
        df = pd.read_excel(path, dtype=None)
    else:
        df = pd.read_csv(path, encoding="utf-8-sig", dtype=None)

    # Normalize column names
    df.columns = [col.replace("\ufeff", "").replace("\u200b", "").replace("\u00a0", " ").strip()
                  for col in df.columns]
    return df

def find_col(df: pd.DataFrame, candidates: list) -> str:
    """Find first matching column from candidates"""
    for cand in candidates:
        for col in df.columns:
            if col.strip().upper() == cand.strip().upper():
                return col
    return None

def analyze_files(sales_file: str, payment_file: str):
    """Analyze sales and payment files to identify discrepancies"""

    print("=" * 80)
    print("PAYMENT METHOD TOTALS DIAGNOSTIC")
    print("=" * 80)
    print()

    # Read files
    print("1. LOADING FILES")
    print("-" * 80)
    sales_df = read_file(sales_file)
    payment_df = read_file(payment_file)

    print(f"  Sales file:    {Path(sales_file).name}")
    print(f"  Sales rows:    {len(sales_df):,}")
    print(f"  Payment file:  {Path(payment_file).name}")
    print(f"  Payment rows:  {len(payment_df):,}")
    print()

    # Find columns
    sales_order_col = find_col(sales_df, ["Order Lines/Order Ref", "Order Ref"])
    sales_date_col = find_col(sales_df, ["Order Lines/Order Ref/Date", "Order Lines/Date", "Date", "Sale Date", "Order Date"])
    sales_amount_col = find_col(sales_df, ["Order Lines/Subtotal w/o Tax", "Subtotal w/o Tax", "Subtotal excl tax"])
    sales_qty_col = find_col(sales_df, ["Order Lines/Base Quantity", "Order Lines/Quantity", "Quantity"])

    payment_order_col = find_col(payment_df, ["Order Ref", "Payments/Order Ref"])
    payment_method_col = find_col(payment_df, ["Payments/Payment Method", "Payment Method"])
    payment_amount_col = find_col(payment_df, ["Payments/Amount", "Amount"])

    print("2. COLUMN MAPPING")
    print("-" * 80)
    print(f"  Sales order ref:  {sales_order_col}")
    print(f"  Sales date:       {sales_date_col}")
    print(f"  Sales amount:     {sales_amount_col}")
    print(f"  Payment order:    {payment_order_col}")
    print(f"  Payment method:   {payment_method_col}")
    print(f"  Payment amount:   {payment_amount_col}")
    print()

    if not all([sales_order_col, sales_date_col, payment_order_col, payment_method_col, payment_amount_col]):
        print("  ⚠ ERROR: Some required columns not found!")
        return

    # Process sales lines - sum by order
    print("3. PROCESSING SALES LINES")
    print("-" * 80)
    sales_df["Order Ref"] = sales_df[sales_order_col].apply(clean_order_ref)
    sales_df["Sale Date"] = pd.to_datetime(sales_df[sales_date_col], errors="coerce")
    sales_df["Amount"] = sales_df[sales_amount_col].apply(safe_float)

    # Group sales by order
    sales_by_order = sales_df.groupby("Order Ref").agg({
        "Amount": "sum",
        "Sale Date": "first"
    }).to_dict()

    sales_totals = sales_df["Amount"].sum()
    unique_orders_sales = len(sales_df["Order Ref"].unique())

    print(f"  Total sales amount:     {sales_totals:>18,.2f} SAR")
    print(f"  Unique orders in sales: {unique_orders_sales:>18,}")
    print(f"  Average per order:      {sales_totals/unique_orders_sales if unique_orders_sales > 0 else 0:>18,.2f} SAR")
    print()

    # Process payments
    print("4. PROCESSING PAYMENT LINES")
    print("-" * 80)
    payment_df["Order Ref"] = payment_df[payment_order_col].apply(clean_order_ref)
    payment_df["Payment Method"] = payment_df[payment_method_col].apply(lambda x: normalise_payment(safe_str(x)))
    payment_df["Amount"] = payment_df[payment_amount_col].apply(safe_float)

    # Remove zero/empty amounts
    payment_df = payment_df[payment_df["Amount"] > 0]
    payment_df = payment_df[payment_df["Order Ref"] != ""]

    payment_totals = payment_df["Amount"].sum()
    unique_orders_payment = len(payment_df["Order Ref"].unique())

    print(f"  Total payment amount:     {payment_totals:>18,.2f} SAR")
    print(f"  Unique orders in payment: {unique_orders_payment:>18,}")
    print(f"  Average per order:        {payment_totals/unique_orders_payment if unique_orders_payment > 0 else 0:>18,.2f} SAR")
    print()

    # Analyze by payment method
    print("5. PAYMENT METHOD BREAKDOWN")
    print("-" * 80)
    method_totals = payment_df.groupby("Payment Method")["Amount"].sum().sort_values(ascending=False)
    method_counts = payment_df.groupby("Payment Method").size()

    print(f"  {'Payment Method':<20} {'Count':<12} {'Total (SAR)':<20}")
    print(f"  {'-'*20} {'-'*12} {'-'*20}")
    for method in method_totals.index:
        count = method_counts[method]
        total = method_totals[method]
        print(f"  {method:<20} {count:<12,} {total:>18,.2f}")
    print(f"  {'-'*20} {'-'*12} {'-'*20}")
    print(f"  {'TOTAL':<20} {method_counts.sum():<12,} {method_totals.sum():>18,.2f}")
    print()

    # Analyze day-wise by payment method
    print("6. DAY-WISE PAYMENT METHOD TOTALS")
    print("-" * 80)

    # Add date from sales to payment records
    payment_with_date = []
    orders_without_date = []

    for _, row in payment_df.iterrows():
        order_ref = row["Order Ref"]
        if order_ref in sales_by_order["Sale Date"]:
            sale_date = sales_by_order["Sale Date"][order_ref]
            if pd.notna(sale_date):
                payment_with_date.append({
                    "Order Ref": order_ref,
                    "Date": sale_date.strftime("%Y-%m-%d"),
                    "Payment Method": row["Payment Method"],
                    "Amount": row["Amount"]
                })
            else:
                orders_without_date.append(order_ref)
        else:
            orders_without_date.append(order_ref)

    if orders_without_date:
        print(f"  ⚠ WARNING: {len(orders_without_date)} payment records have no matching sales date")
        print(f"     Example orders: {orders_without_date[:5]}")
        print()

    if payment_with_date:
        payment_dated_df = pd.DataFrame(payment_with_date)

        # Day-wise totals
        day_wise = payment_dated_df.groupby(["Date", "Payment Method"])["Amount"].sum().reset_index()
        day_wise_pivot = day_wise.pivot(index="Date", columns="Payment Method", values="Amount").fillna(0)

        print(f"  Day-wise payment method totals:")
        print()

        # Print header
        methods = sorted(day_wise_pivot.columns)
        header = f"  {'Date':<12}"
        for method in methods:
            header += f" {method:>12}"
        header += f" {'TOTAL':>12}"
        print(header)
        print(f"  {'-'*12}", end="")
        for _ in methods:
            print(f" {'-'*12}", end="")
        print(f" {'-'*12}")

        # Print rows
        for date in sorted(day_wise_pivot.index):
            row = day_wise_pivot.loc[date]
            line = f"  {date:<12}"
            row_total = 0
            for method in methods:
                amount = row.get(method, 0)
                row_total += amount
                line += f" {amount:>12,.0f}"
            line += f" {row_total:>12,.0f}"
            print(line)

        # Print totals
        print(f"  {'-'*12}", end="")
        for _ in methods:
            print(f" {'-'*12}", end="")
        print(f" {'-'*12}")

        line = f"  {'TOTAL':<12}"
        grand_total = 0
        for method in methods:
            method_total = day_wise_pivot[method].sum()
            grand_total += method_total
            line += f" {method_total:>12,.0f}"
        line += f" {grand_total:>12,.0f}"
        print(line)
        print()

    # Check for mismatches
    print("7. VALIDATION CHECKS")
    print("-" * 80)

    # Check if sales total matches payment total
    diff = abs(sales_totals - payment_totals)
    diff_pct = (diff / payment_totals * 100) if payment_totals > 0 else 0

    print(f"  Sales total:      {sales_totals:>18,.2f} SAR")
    print(f"  Payment total:    {payment_totals:>18,.2f} SAR")
    print(f"  Difference:       {diff:>18,.2f} SAR ({diff_pct:.2f}%)")

    if diff < 10:
        print(f"  Status:           ✓ MATCH (within tolerance)")
    elif diff_pct < 1:
        print(f"  Status:           ⚠ MINOR DIFFERENCE (<1%)")
    else:
        print(f"  Status:           ✗ MISMATCH (>{diff_pct:.1f}%)")
    print()

    # Check for orders in payment but not in sales
    sales_orders = set(sales_df["Order Ref"].unique())
    payment_orders = set(payment_df["Order Ref"].unique())

    only_in_sales = sales_orders - payment_orders
    only_in_payment = payment_orders - sales_orders

    if only_in_sales:
        print(f"  ⚠ {len(only_in_sales)} orders in SALES but NOT in PAYMENT")
        print(f"     Examples: {list(only_in_sales)[:5]}")
        print()

    if only_in_payment:
        print(f"  ⚠ {len(only_in_payment)} orders in PAYMENT but NOT in SALES")
        print(f"     Examples: {list(only_in_payment)[:5]}")
        print()

    if not only_in_sales and not only_in_payment:
        print(f"  ✓ All orders exist in both files")
        print()

    print("=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python diagnose_payment_totals.py <sales_file> <payment_file>")
        print()
        print("Examples:")
        print('  python diagnose_payment_totals.py "ZAHRAN sale line 5 to 31 March.xlsx" "ZAHRAN payment line 5 to 31 March.xlsx"')
        sys.exit(1)

    sales_file = sys.argv[1]
    payment_file = sys.argv[2]

    analyze_files(sales_file, payment_file)
