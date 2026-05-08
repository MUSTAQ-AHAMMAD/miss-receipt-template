#!/usr/bin/env python3
"""
Test script to investigate TAMARA charge calculation issues
with 49_stores_payment_lines.xlsx and 49_stores_sales_lines.xlsx
"""

import sys
import pandas as pd
from pathlib import Path

# Import from the main module properly
sys.path.insert(0, str(Path(__file__).parent))

# Read and execute the main file, handling BOM
with open("Odoo-export-FBDA-template.py", 'r', encoding='utf-8-sig') as f:
    exec(f.read())

from datetime import datetime

def test_49_stores():
    print("=" * 100)
    print("TESTING TAMARA CHARGES WITH 49_STORES DATA")
    print("=" * 100)

    # File paths
    payment_file = "49_stores_payment_lines.xlsx"
    sales_file = "49_stores_sales_lines.xlsx"

    print(f"\nPayment file: {payment_file}")
    print(f"Sales file: {sales_file}")

    # Check if files exist
    if not Path(payment_file).exists():
        print(f"ERROR: {payment_file} not found!")
        return
    if not Path(sales_file).exists():
        print(f"ERROR: {sales_file} not found!")
        return

    print("\n" + "=" * 100)
    print("STEP 1: Reading payment file to examine TAMARA transactions")
    print("=" * 100)

    # Read payment file
    payment_df = pd.read_excel(payment_file)
    print(f"\nPayment file columns: {payment_df.columns.tolist()[:10]}...")  # First 10 columns
    print(f"Total rows: {len(payment_df)}")

    # Find TAMARA transactions
    payment_method_col = None
    for col in payment_df.columns:
        if 'payment method' in str(col).lower():
            payment_method_col = col
            break

    if payment_method_col:
        print(f"Payment method column: {payment_method_col}")
        tamara_mask = payment_df[payment_method_col].astype(str).str.upper().str.contains('TAMARA', na=False)
        tamara_df = payment_df[tamara_mask].copy()

        print(f"\nTAMARA transactions found: {len(tamara_df)}")

        if len(tamara_df) > 0:
            # Find amount column
            amount_col = None
            for col in payment_df.columns:
                if 'amount' in str(col).lower() and 'payment' in str(col).lower():
                    amount_col = col
                    break

            if amount_col:
                print(f"Amount column: {amount_col}")
                print("\nSample TAMARA transactions (first 10):")
                print("-" * 100)
                relevant_cols = [c for c in ['Sales Order', payment_method_col, amount_col] if c in tamara_df.columns]
                print(tamara_df[relevant_cols].head(10).to_string(index=False))

                print(f"\nTAMARA transaction statistics:")
                amounts = pd.to_numeric(tamara_df[amount_col], errors='coerce').dropna()
                print(f"  Min amount: {amounts.min():.2f} SAR")
                print(f"  Max amount: {amounts.max():.2f} SAR")
                print(f"  Mean amount: {amounts.mean():.2f} SAR")
                print(f"  Total amount: {amounts.sum():.2f} SAR")

    print("\n" + "=" * 100)
    print("STEP 2: Reading sales lines file")
    print("=" * 100)

    # Read sales lines file
    sales_df = pd.read_excel(sales_file)
    print(f"\nSales file columns: {sales_df.columns.tolist()[:10]}...")  # First 10 columns
    print(f"Total rows: {len(sales_df)}")

    # Check if we have the preferred column
    if 'Order Lines/Subtotal w/o Tax' in sales_df.columns:
        print("\n✓ Found 'Order Lines/Subtotal w/o Tax' column (preferred)")
    elif 'Order Lines/Subtotal' in sales_df.columns:
        print("\n✓ Found 'Order Lines/Subtotal' column")

    print("\n" + "=" * 100)
    print("STEP 3: Generating Journal Template")
    print("=" * 100)

    # Create integration instance
    integration = OracleFusionIntegration(
        output_dir="ORACLE_FUSION_OUTPUT_49_STORES",
        start_seq=1,
        start_legacy_seq_1=1,
        start_legacy_seq_2=1,
    )

    try:
        # Generate journal template with charges
        journal_df = integration.generate_journal_template(
            journal_config_path="JOURNAL_CONFIG.csv",
            account_mapping_path="JOURNAL_ACCOUNT_MAPPING.csv",
            period_name="Mar-26",
            interface_group_id=114,
            service_provider_meta_path="SERVICE_PROVIDER_JOURNAL_META.csv",
            cost_center_meta_path="FUSION_SALES_METADATA_Cost_Center.csv",
            is_cash="0",
            payment_file_path=payment_file,
            sales_lines_file_path=sales_file,
            charges_file_path="SERVICE_PROVIDER_JOURNAL_META_Charges.csv",
        )

        if journal_df.empty:
            print("\n⚠️  No journal entries generated!")
            return

        print(f"\n✓ Generated {len(journal_df)} journal entries")

        # Save the journal
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"49_STORES_JRNL_CHARGES_{ts}.csv"
        journal_df.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"✓ Saved to: {output_file}")

        print("\n" + "=" * 100)
        print("STEP 4: Analyzing TAMARA charges in journal output")
        print("=" * 100)

        # Filter for TAMARA entries
        tamara_journal = journal_df[journal_df['REFERENCE1 (Batch Name)'].str.contains('TAMARA', na=False)]

        print(f"\nTAMARA entries in journal: {len(tamara_journal)}")

        if len(tamara_journal) > 0:
            # Get debit amounts (charges)
            debit_col = 'Entered Debit Amount'
            if debit_col in tamara_journal.columns:
                charges = tamara_journal[debit_col].astype(str).str.strip()
                charges = pd.to_numeric(charges, errors='coerce').dropna()

                if len(charges) > 0:
                    print(f"\nTAMARA Charge Statistics:")
                    print(f"  Number of charges: {len(charges)}")
                    print(f"  Min charge: {charges.min():.2f} SAR")
                    print(f"  Max charge: {charges.max():.2f} SAR")
                    print(f"  Mean charge: {charges.mean():.2f} SAR")
                    print(f"  Total charges: {charges.sum():.2f} SAR")

                    print(f"\nSample TAMARA charges (first 10 unique values):")
                    unique_charges = sorted(charges.unique())[:10]
                    print("-" * 100)
                    print(f"{'Charge':<15} {'Reverse-Calc Amount':<25} {'Verification':<30}")
                    print("-" * 100)

                    # Reverse calculate original amounts
                    tamara_fixed = 1.5
                    tamara_rate = 0.0425

                    for charge in unique_charges:
                        orig_amount = (charge - tamara_fixed) / tamara_rate
                        verify_charge = round(tamara_fixed + (orig_amount * tamara_rate), 2)
                        match = "✓ MATCH" if abs(verify_charge - charge) < 0.01 else "✗ MISMATCH"
                        print(f"{charge:<15.2f} {orig_amount:<25.2f} {match:<30}")

        print("\n" + "=" * 100)
        print("STEP 5: Manual Verification of Sample Charges")
        print("=" * 100)

        # Let's manually verify a few transactions
        if payment_method_col and amount_col and len(tamara_df) > 0:
            print("\nManually calculating expected charges for first 5 TAMARA payments:")
            print("-" * 100)
            print(f"{'Amount':<15} {'Fixed':<10} {'Variable':<15} {'Total Charge':<15}")
            print("-" * 100)

            tamara_fixed = 1.5
            tamara_rate = 0.0425

            for idx, row in tamara_df.head(5).iterrows():
                amount = pd.to_numeric(row[amount_col], errors='coerce')
                if pd.notna(amount):
                    variable = amount * tamara_rate
                    total = tamara_fixed + variable
                    print(f"{amount:<15.2f} {tamara_fixed:<10.2f} {variable:<15.2f} {total:<15.2f}")

        print("\n" + "=" * 100)
        print("ANALYSIS COMPLETE")
        print("=" * 100)

    except Exception as e:
        import traceback
        print(f"\n❌ Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_49_stores()
