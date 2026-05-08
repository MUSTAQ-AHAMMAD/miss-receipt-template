"""
Diagnose journal template charge calculation
Generate journal and compare with expected charges
"""

import pandas as pd
import sys
import csv
from pathlib import Path

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
    print("JOURNAL TEMPLATE CHARGE DIAGNOSIS")
    print("="*80)

    # Step 1: Load expected charges
    expected_file = "charge_calculation_expected.csv"
    if not Path(expected_file).exists():
        print(f"\n⚠️  Expected charges file not found: {expected_file}")
        print("Run test_charge_calculation_fix.py first")
        return

    expected_df = pd.read_csv(expected_file)
    print(f"\n✓  Loaded {len(expected_df)} expected charge calculations")

    # Step 2: Check for generated journal file
    journal_file = "Makkah_JRNL (1).csv"
    if not Path(journal_file).exists():
        # Try to find any journal file
        journal_files = list(Path(".").glob("*JRNL*.csv")) + list(Path(".").glob("*journal*.csv"))
        if journal_files:
            journal_file = str(journal_files[0])
            print(f"\n✓  Found journal file: {journal_file}")
        else:
            print(f"\n⚠️  No journal file found. Please generate one first using:")
            print("     python3 Odoo-export-FBDA-template.py")
            return
    else:
        print(f"\n✓  Found journal file: {journal_file}")

    # Step 3: Analyze journal file
    print(f"\n✓  Analyzing journal file...")

    with open(journal_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        journal_rows = list(reader)

    print(f"✓  Loaded {len(journal_rows)} journal entries")

    # Extract charge amounts from journal
    # Charges are typically smaller amounts (under 100 SAR)
    # Group by batch to understand the structure
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

    # Step 4: Identify charges vs payments in journal
    print("\n" + "="*80)
    print("JOURNAL STRUCTURE ANALYSIS")
    print("="*80)

    charge_entries = []
    payment_entries = []

    for batch_name, entries in batches.items():
        provider = None
        if 'TABBY' in batch_name.upper():
            provider = 'TABBY'
        elif 'TAMARA' in batch_name.upper():
            provider = 'TAMARA'

        if not provider:
            continue

        # Get unique amounts in this batch
        amounts = sorted(set([e['amount'] for e in entries]))

        # If we have multiple different amounts, identify which are charges
        # Charges should be small (typically < 100 SAR for most transactions)
        for amt in amounts:
            # Check if this looks like a charge amount by comparing to expected
            expected_charge = calculate_expected_charge(amt, provider)

            # If the amount itself could be a valid charge, store it
            if amt < 100 or abs(amt - expected_charge) < 0.1:
                charge_entries.append({
                    'batch': batch_name,
                    'provider': provider,
                    'amount': amt
                })
            else:
                # This is likely a payment amount
                # Calculate what the charge should be
                expected_charge_for_payment = calculate_expected_charge(amt, provider)
                payment_entries.append({
                    'batch': batch_name,
                    'provider': provider,
                    'payment_amount': amt,
                    'expected_charge': expected_charge_for_payment
                })

    print(f"\nFound {len(payment_entries)} payment entries")
    print(f"Found {len(charge_entries)} charge entries")

    # Step 5: Compare with expected
    print("\n" + "="*80)
    print("CHARGE VERIFICATION")
    print("="*80)

    if len(charge_entries) == 0:
        print("\n⚠️  WARNING: NO CHARGE ENTRIES FOUND IN JOURNAL!")
        print("   The journal appears to contain only payment amounts.")
        print("   This indicates the journal was generated in CHARGES-ONLY mode")
        print("   but the charges weren't actually calculated correctly,")
        print("   OR payment entries were uncommented in the code.")

        if len(payment_entries) > 0:
            print(f"\n   The journal contains {len(payment_entries)} PAYMENT entries instead.")
            print("\n   Sample payment entries found:")
            for entry in payment_entries[:5]:
                print(f"     {entry['provider']:6} Payment: {entry['payment_amount']:>8.2f} SAR")
                print(f"              Expected charge: {entry['expected_charge']:>8.2f} SAR")
    else:
        print(f"\n✓  Found {len(charge_entries)} charge entries in journal")
        print("\nSample charges from journal:")
        for entry in charge_entries[:10]:
            print(f"  {entry['provider']:6}: {entry['amount']:>8.2f} SAR")

        # Compare totals
        journal_charge_total = sum(e['amount'] for e in charge_entries)
        expected_charge_total = expected_df['Expected_Charge'].sum()

        print(f"\n📊 Charge Totals:")
        print(f"   Expected (from formula): {expected_charge_total:,.2f} SAR")
        print(f"   Found in journal:        {journal_charge_total:,.2f} SAR")
        print(f"   Difference:              {abs(expected_charge_total - journal_charge_total):,.2f} SAR")

        if abs(expected_charge_total - journal_charge_total) > 1.0:
            print(f"\n⚠️  MISMATCH DETECTED!")
            print(f"   The charges in the journal don't match the expected formula.")
        else:
            print(f"\n✅  CHARGES MATCH! Calculation is correct.")

    print("\n" + "="*80)
    print("DIAGNOSIS COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
