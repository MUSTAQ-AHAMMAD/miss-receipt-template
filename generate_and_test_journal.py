"""
Generate journal template for MAKKAH payment file and verify charges
"""

import pandas as pd
import sys
import csv
from pathlib import Path
from datetime import datetime

# Add path to import the module
sys.path.insert(0, '/home/runner/work/miss-receipt-template/miss-receipt-template')

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
    print("JOURNAL TEMPLATE GENERATION FOR MAKKAH PAYMENT FILE")
    print("="*80)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Import the processor class
    import importlib.util
    spec = importlib.util.spec_from_file_location("odoo_export", "Odoo-export-FBDA-template.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    OracleFusionIntegration = module.OracleFusionIntegration

    # Create integration instance
    integration = OracleFusionIntegration(
        output_dir="ORACLE_FUSION_OUTPUT",
        start_seq=500,
        start_legacy_seq_1=1,
        start_legacy_seq_2=1
    )

    # Generate journal template
    payment_file = "MAKKAH payment line 5 to 31 March.xlsx"
    print(f"Generating journal template for: {payment_file}")
    print("="*80)
    print()

    journal_df = integration.generate_journal_template(
        service_provider_meta_path="SERVICE_PROVIDER_JOURNAL_META.csv",
        cost_center_meta_path="FUSION_SALES_METADATA_Cost_Center.csv",
        charges_file_path="SERVICE_PROVIDER_JOURNAL_META_Charges.csv",
        payment_file_path=payment_file,
        sales_lines_file_path=""  # No sales lines
    )

    print("\n" + "="*80)
    print("JOURNAL GENERATION COMPLETE")
    print("="*80)

    if journal_df.empty:
        print("\n⚠️ No journal entries generated!")
        return

    # Save the journal
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"MAKKAH_JRNL_CHARGES_{ts}.csv"
    journal_df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"\n✓ Saved journal to: {output_file}")
    print(f"✓ Total entries: {len(journal_df)}")

    # Analyze the generated journal
    print("\n" + "="*80)
    print("ANALYZING GENERATED CHARGES")
    print("="*80)

    # Extract charge amounts by provider
    charges_by_provider = {'TABBY': [], 'TAMARA': []}

    for _, row in journal_df.iterrows():
        batch = row.get('REFERENCE1 (Batch Name)', '')
        debit = float(row.get('Entered Debit Amount', 0) or 0)
        credit = float(row.get('Entered Credit Amount', 0) or 0)
        amount = debit if debit > 0 else credit

        if amount > 0:
            if 'TABBY' in str(batch).upper():
                charges_by_provider['TABBY'].append(amount)
            elif 'TAMARA' in str(batch).upper():
                charges_by_provider['TAMARA'].append(amount)

    # Load expected charges
    expected_file = "charge_calculation_expected.csv"
    if Path(expected_file).exists():
        expected_df = pd.read_csv(expected_file)
        expected_totals = {}
        for method in ['TABBY', 'TAMARA']:
            method_data = expected_df[expected_df['Method'] == method]
            expected_totals[method] = {
                'count': len(method_data),
                'total': method_data['Expected_Charge'].sum()
            }
    else:
        expected_totals = {}

    # Compare
    print()
    all_match = True
    for provider in ['TABBY', 'TAMARA']:
        charges = charges_by_provider[provider]
        actual_total = sum(charges)
        actual_count = len(charges) // 2  # Each charge has 2 entries

        print(f"{provider}:")
        print(f"  Actual charges in journal: {actual_total:,.2f} SAR ({actual_count} transactions)")

        if provider in expected_totals:
            expected = expected_totals[provider]
            print(f"  Expected from formula:     {expected['total']:,.2f} SAR ({expected['count']} transactions)")

            diff = abs(actual_total - expected['total'])
            if diff < 1.0:
                print(f"  ✅ MATCH! (difference: {diff:.2f} SAR)")
            else:
                print(f"  ❌ MISMATCH! (difference: {diff:.2f} SAR)")
                all_match = False
        print()

    # Final result
    print("="*80)
    if all_match and expected_totals:
        print("✅ SUCCESS! All charges match the expected formula")
    elif not expected_totals:
        print("⚠️  Could not verify (run test_charge_calculation_fix.py first)")
    else:
        print("❌ FAILURE! Charges do not match")
    print("="*80)

if __name__ == "__main__":
    main()
