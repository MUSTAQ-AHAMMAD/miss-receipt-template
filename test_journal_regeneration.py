"""
Comprehensive test to regenerate journal and verify charges match the formula
This script will:
1. Generate a fresh journal template using the current code
2. Extract charge amounts from the generated journal
3. Compare them with expected charges based on the formula
4. Report any mismatches
"""

import subprocess
import pandas as pd
import csv
import sys
from pathlib import Path
from datetime import datetime

def calculate_expected_charge(amount, payment_method):
    """Calculate expected charge based on user's formula"""
    abs_amount = abs(amount)

    if payment_method.upper() == "TAMARA":
        fixed = 1.5
        rate = 0.0425  # 4.25%
    elif payment_method.upper() == "TABBY":
        fixed = 1.0
        rate = 0.05  # 5%
    else:
        return 0.0

    total_charge = fixed + (abs_amount * rate)
    return round(total_charge, 2)

def main():
    print("="*80)
    print("JOURNAL TEMPLATE REGENERATION AND VERIFICATION TEST")
    print("="*80)
    print(f"\nTest started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 1: Check required files
    print("\n" + "="*80)
    print("STEP 1: Checking required files")
    print("="*80)

    required_files = [
        "Odoo-export-FBDA-template.py",
        "MAKKAH payment line 5 to 31 March.xlsx",
        "SERVICE_PROVIDER_JOURNAL_META_Charges.csv",
        "SERVICE_PROVIDER_JOURNAL_META.csv"
    ]

    for file in required_files:
        if Path(file).exists():
            print(f"✓  Found: {file}")
        else:
            print(f"⚠️  Missing: {file}")
            return

    # Step 2: Load expected charges
    expected_file = "charge_calculation_expected.csv"
    if Path(expected_file).exists():
        expected_df = pd.read_csv(expected_file)
        print(f"\n✓  Loaded {len(expected_df)} expected charge calculations")

        # Calculate expected totals
        expected_totals = {}
        for method in ['TABBY', 'TAMARA']:
            method_data = expected_df[expected_df['Method'] == method]
            expected_totals[method] = {
                'count': len(method_data),
                'invoice_total': method_data['Amount'].sum(),
                'charge_total': method_data['Expected_Charge'].sum()
            }

        print("\nExpected charge totals:")
        for method, totals in expected_totals.items():
            print(f"  {method}: {totals['charge_total']:,.2f} SAR ({totals['count']} transactions)")
    else:
        print(f"\n⚠️  Expected charges file not found. Run test_charge_calculation_fix.py first")
        expected_df = None
        expected_totals = {}

    # Step 3: Generate new journal
    print("\n" + "="*80)
    print("STEP 2: Generating fresh journal template")
    print("="*80)

    print("\nRunning Odoo-export-FBDA-template.py...")
    print("(This may take a few moments...)\n")

    try:
        result = subprocess.run(
            ["python3", "Odoo-export-FBDA-template.py"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Print output (filtered for charge-related info)
        print("\n--- Generation Output (charge-related lines) ---")
        for line in result.stdout.split('\n'):
            if any(keyword in line for keyword in ['charge', 'Charge', 'CHARGE', 'TABBY', 'TAMARA', 'Total', '✓', '⚠️']):
                print(line)

        if result.returncode != 0:
            print(f"\n⚠️  Script returned error code: {result.returncode}")
            print("Error output:")
            print(result.stderr)
            return

        print("\n✓  Journal generation completed")

    except subprocess.TimeoutExpired:
        print("\n⚠️  Journal generation timed out after 5 minutes")
        return
    except Exception as e:
        print(f"\n⚠️  Error running journal generation: {e}")
        return

    # Step 4: Find and analyze the new journal file
    print("\n" + "="*80)
    print("STEP 3: Analyzing generated journal")
    print("="*80)

    # Find the most recent journal file
    journal_files = list(Path(".").glob("Journal_Import_Template_*.csv"))
    if not journal_files:
        print("\n⚠️  No journal template file found!")
        return

    # Get the most recent one
    journal_file = max(journal_files, key=lambda p: p.stat().st_mtime)
    print(f"\n✓  Found journal file: {journal_file}")

    # Load and analyze
    with open(journal_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        journal_rows = list(reader)

    print(f"✓  Loaded {len(journal_rows)} journal entries")

    # Extract charges by provider
    charges_by_provider = {'TABBY': [], 'TAMARA': []}
    from collections import defaultdict
    batches = defaultdict(list)

    for row in journal_rows:
        batch = row.get('REFERENCE1 (Batch Name)', '')
        seg2 = row.get('Segment2', '')
        debit_str = row.get('Entered Debit Amount', '').strip()
        credit_str = row.get('Entered Credit Amount', '').strip()

        debit = float(debit_str) if debit_str else 0.0
        credit = float(credit_str) if credit_str else 0.0
        amount = debit if debit > 0 else credit

        if amount > 0:
            batches[batch].append({
                'seg2': seg2,
                'amount': amount
            })

    # Collect charge amounts (should all be under 150 SAR for this dataset)
    for batch_name, entries in batches.items():
        provider = None
        if 'TABBY' in batch_name.upper():
            provider = 'TABBY'
        elif 'TAMARA' in batch_name.upper():
            provider = 'TAMARA'

        if provider:
            for entry in entries:
                # In charges-only mode, all amounts should be charges
                charges_by_provider[provider].append(entry['amount'])

    # Step 5: Compare with expected
    print("\n" + "="*80)
    print("STEP 4: Comparing with expected charges")
    print("="*80)

    all_match = True

    for provider in ['TABBY', 'TAMARA']:
        charges = charges_by_provider[provider]
        actual_total = sum(charges)
        actual_count = len(charges) // 2  # Each charge has 2 entries (debit/credit)

        print(f"\n{provider}:")
        print(f"  Entries in journal: {len(charges)} lines ({actual_count} charge transactions)")
        print(f"  Actual charge total: {actual_total:,.2f} SAR")

        if provider in expected_totals:
            expected = expected_totals[provider]
            print(f"  Expected charge total: {expected['charge_total']:,.2f} SAR ({expected['count']} transactions)")

            diff = abs(actual_total - expected['charge_total'])
            if diff < 1.0:  # Allow small rounding differences
                print(f"  ✅ MATCH! (difference: {diff:.2f} SAR)")
            else:
                print(f"  ❌ MISMATCH! (difference: {diff:.2f} SAR)")
                all_match = False

    # Final verdict
    print("\n" + "="*80)
    print("FINAL RESULT")
    print("="*80)

    if all_match and expected_df is not None:
        print("\n✅ SUCCESS! All charges match the expected formula:")
        print("   TAMARA = 1.5 + (amount × 4.25%)")
        print("   TABBY = 1.0 + (amount × 5%)")
        print(f"\n✓  Generated journal file: {journal_file}")
    elif expected_df is None:
        print("\n⚠️  Could not fully verify (expected charges file missing)")
        print(f"   Generated journal file: {journal_file}")
    else:
        print("\n❌ FAILURE! Charges do not match the expected formula")
        print("   Please review the output above for details")

    print("\n" + "="*80)

if __name__ == "__main__":
    main()
