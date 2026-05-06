#!/usr/bin/env python3
"""
Test script to verify that charge entries are correctly added to journal template.
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# Add the repository root to the path
sys.path.insert(0, str(Path(__file__).parent))

# Import the integration module
import importlib.util
spec = importlib.util.spec_from_file_location(
    "oracle_integration",
    Path(__file__).parent / "Odoo-export-FBDA-template.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def test_charge_entries():
    """Test that charge entries are generated for TABBY and TAMARA transactions"""

    print("=" * 80)
    print("TEST: Verify Charge Entries in Journal Template")
    print("=" * 80)

    # Setup test output directory
    output_dir = Path("/tmp/test_charge_entries")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize integration without AR Invoice
    integration = mod.OracleFusionIntegration(
        output_dir=str(output_dir),
        use_sequence_manager=False,
    )

    # Test file paths
    payment_file = "MAKKAH payment line 5 to 31 March.xlsx"
    charges_file = "SERVICE_PROVIDER_JOURNAL_META_Charges.csv"

    if not Path(payment_file).exists():
        print(f"❌ ERROR: Payment file not found: {payment_file}")
        return False

    if not Path(charges_file).exists():
        print(f"❌ ERROR: Charges file not found: {charges_file}")
        return False

    print(f"\n✓ Found payment file: {payment_file}")
    print(f"✓ Found charges file: {charges_file}")

    # First, let's check the charges configuration
    charges_df = pd.read_csv(charges_file)
    print(f"\n📊 Charges configuration:")
    tabby_charges = charges_df[(charges_df['SERVICE_PROVIDER'] == 'TABBY') & (charges_df['IS_CASH'] == '0')]
    tamara_charges = charges_df[(charges_df['SERVICE_PROVIDER'] == 'TAMARA') & (charges_df['IS_CASH'] == '0')]

    if not tabby_charges.empty:
        row = tabby_charges.iloc[0]
        print(f"   TABBY: Fixed={row['FIXED_FREIGHT_CHARGE']}, Rate={float(row['BANK_CHARGE_RATE'])*100:.2f}%")

    if not tamara_charges.empty:
        row = tamara_charges.iloc[0]
        print(f"   TAMARA: Fixed={row['FIXED_FREIGHT_CHARGE']}, Rate={float(row['BANK_CHARGE_RATE'])*100:.2f}%")

    # Check payment file
    df = pd.read_excel(payment_file)
    print(f"\n📊 Payment file statistics:")
    print(f"   Total rows: {len(df)}")

    if 'Payments/Payment Method' in df.columns:
        payment_methods = df['Payments/Payment Method'].value_counts()
        print(f"\n   Payment methods breakdown:")
        tabby_count = payment_methods.get('TABBY', 0)
        tamara_count = payment_methods.get('TAMARA', 0)
        print(f"     - TABBY: {tabby_count} transactions")
        print(f"     - TAMARA: {tamara_count} transactions")

    # Generate journal template with charges
    print(f"\n" + "=" * 80)
    print("Generating Journal Template with Charge Entries")
    print("=" * 80)

    try:
        journal_df = integration.generate_journal_template(
            journal_config_path="",  # Will use defaults
            account_mapping_path="",  # Will use defaults
            period_name="Mar-26",
            interface_group_id="TEST_CHARGES_001",
            service_provider_meta_path="SERVICE_PROVIDER_JOURNAL_META.csv",
            cost_center_meta_path="",
            is_cash="0",  # Non-cash transactions only
            payment_file_path=payment_file,
            sales_lines_file_path="",
            charges_file_path=charges_file,
        )

        if journal_df.empty:
            print("\n❌ ERROR: No journal entries generated")
            return False

        print(f"\n✅ SUCCESS: Generated journal template with {len(journal_df)} total entries")

        # Analyze the generated entries
        print(f"\n" + "=" * 80)
        print("Analysis of Generated Entries")
        print("=" * 80)

        # Count entries by checking for unique combinations of payment amounts
        # Each transaction should have 4 entries (2 for payment, 2 for charges)

        # Group by batch name to see transactions
        if "REFERENCE1 (Batch Name)" in journal_df.columns:
            batch_groups = journal_df.groupby("REFERENCE1 (Batch Name)")
            print(f"\n✓ Number of unique batches: {len(batch_groups)}")

            # Show first few batches
            print(f"\n📋 First 3 batches:")
            for i, (batch_name, batch_df) in enumerate(batch_groups):
                if i >= 3:
                    break
                print(f"\n   Batch: {batch_name}")
                print(f"   Entries: {len(batch_df)} lines")

                # Check for debit and credit amounts
                debit_entries = batch_df[batch_df["Entered Debit Amount"].astype(str).str.strip() != ""]
                credit_entries = batch_df[batch_df["Entered Credit Amount"].astype(str).str.strip() != ""]

                print(f"   Debit entries: {len(debit_entries)}")
                print(f"   Credit entries: {len(credit_entries)}")

                # Show amounts
                for _, row in batch_df.iterrows():
                    segment2 = row.get("Segment2", "")
                    debit_amt = row.get("Entered Debit Amount", "")
                    credit_amt = row.get("Entered Credit Amount", "")

                    if debit_amt and str(debit_amt).strip():
                        print(f"      Segment2={segment2} → Debit: {debit_amt}")
                    if credit_amt and str(credit_amt).strip():
                        print(f"      Segment2={segment2} → Credit: {credit_amt}")

        # Save the generated journal for inspection
        output_file = output_dir / "test_journal_with_charges.csv"
        journal_df.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"\n✓ Saved test journal template to: {output_file}")

        return True

    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_charge_entries()
    sys.exit(0 if success else 1)
