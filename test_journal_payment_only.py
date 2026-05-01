#!/usr/bin/env python3
"""
Test script to verify journal template generation works with payment file only
(no AR Invoice required).
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

def test_journal_generation_payment_only():
    """Test journal template generation with payment file only"""

    print("=" * 80)
    print("TEST: Journal Template Generation with Payment File Only")
    print("=" * 80)

    # Setup test output directory
    output_dir = Path("/tmp/test_journal_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize integration without AR Invoice
    integration = mod.OracleFusionIntegration(
        output_dir=str(output_dir),
        use_sequence_manager=False,
    )

    # Test file path
    payment_file = "ZAHRAN payment line 5 to 31 March.xlsx"

    if not Path(payment_file).exists():
        print(f"❌ ERROR: Payment file not found: {payment_file}")
        return False

    print(f"\n✓ Found payment file: {payment_file}")

    # First, let's check what's in the payment file
    df = pd.read_excel(payment_file)
    print(f"\n📊 Payment file statistics:")
    print(f"   Total rows: {len(df)}")

    if 'Payments/Payment Method' in df.columns:
        payment_methods = df['Payments/Payment Method'].value_counts()
        print(f"\n   Payment methods breakdown:")
        for method, count in payment_methods.items():
            print(f"     - {method}: {count} transactions")

        # Check for service providers
        service_providers = ['TAMARA', 'TABBY', 'HUNGERSTATION', 'MRSOOL']
        qualifying_methods = [m for m in payment_methods.index if m.upper() in service_providers]
        if qualifying_methods:
            print(f"\n   ✓ Found qualifying service provider transactions:")
            for method in qualifying_methods:
                count = payment_methods[method]
                print(f"     - {method}: {count} transactions")
        else:
            print(f"\n   ⚠ No qualifying service provider transactions found")
            print(f"     Expected: {service_providers}")

    # Test 1: Generate journal template with payment file only
    print(f"\n" + "=" * 80)
    print("TEST 1: Generate Journal Template (Payment File Only)")
    print("=" * 80)

    try:
        journal_df = integration.generate_journal_template(
            journal_config_path="",  # Will use defaults
            account_mapping_path="",  # Will use defaults
            period_name="Mar-26",
            interface_group_id=114,
            service_provider_meta_path="SERVICE_PROVIDER_JOURNAL_META.csv",
            cost_center_meta_path="FUSION_SALES_METADATA_Cost_Center.csv",
            payment_file_path=payment_file,
        )

        if journal_df.empty:
            print("\n❌ FAILED: Journal template is empty")
            print("   This could mean no qualifying transactions were found")
            return False

        print(f"\n✓ SUCCESS: Generated journal template")
        print(f"   Total journal lines: {len(journal_df)}")
        print(f"   Transactions (debit+credit pairs): {len(journal_df) // 2}")

        # Show some statistics
        if 'Segment1' in journal_df.columns:
            print(f"\n   Journal entry details:")
            print(f"     Unique Segment1 values: {journal_df['Segment1'].nunique()}")
            print(f"     Unique Segment2 values: {journal_df['Segment2'].nunique()}")

        # Show debit/credit breakdown
        try:
            debit_sum = pd.to_numeric(journal_df['Entered Debit Amount'], errors='coerce').fillna(0).sum()
            credit_sum = pd.to_numeric(journal_df['Entered Credit Amount'], errors='coerce').fillna(0).sum()
            print(f"\n   Financial totals:")
            print(f"     Total Debit:  {debit_sum:,.2f} SAR")
            print(f"     Total Credit: {credit_sum:,.2f} SAR")
            print(f"     Balanced: {'✓ Yes' if abs(debit_sum - credit_sum) < 0.01 else '✗ No'}")
        except Exception as e:
            print(f"\n   ⚠ Could not calculate financial totals: {e}")

        # Save the journal template
        output_file = output_dir / f"Journal_Import_Test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        journal_df.to_csv(output_file, index=False)
        print(f"\n✓ Saved journal template to: {output_file}")

        # Display first few rows
        print(f"\n   First 2 journal entries (4 lines - 2 debit/credit pairs):")
        print(journal_df.head(4)[['Status Code', 'Segment1', 'Segment2', 'Entered Debit Amount', 'Entered Credit Amount']].to_string(index=False))

        return True

    except Exception as e:
        print(f"\n❌ FAILED: Exception occurred")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("JOURNAL TEMPLATE GENERATION TEST SUITE")
    print("Testing the revised functionality: Payment Lines Only")
    print("=" * 80)

    # Run the test
    success = test_journal_generation_payment_only()

    print("\n" + "=" * 80)
    if success:
        print("✓ ALL TESTS PASSED")
        print("=" * 80)
        return 0
    else:
        print("✗ TESTS FAILED")
        print("=" * 80)
        return 1

if __name__ == "__main__":
    exit(main())
