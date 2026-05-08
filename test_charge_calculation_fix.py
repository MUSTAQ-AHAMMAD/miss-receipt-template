"""
Test charge calculation to identify and fix any mismatches
This script will:
1. Load payment data
2. Calculate expected charges using the formula
3. Generate journal template
4. Compare calculated charges with expected values
5. Report any mismatches
"""

import pandas as pd
import sys
from pathlib import Path

# Expected formulas:
# TAMARA = fixed_fees(1.5) + (amount * 4.25%)
# TABBY = fixed_fees(1) + (amount * 5%)

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
    print("CHARGE CALCULATION VERIFICATION TEST")
    print("="*80)
    print("\nFormulas:")
    print("  TAMARA = 1.5 + (amount × 4.25%)")
    print("  TABBY  = 1.0 + (amount × 5%)")
    print("="*80)

    # Test with MAKKAH payment file
    payment_file = "MAKKAH payment line 5 to 31 March.xlsx"

    if not Path(payment_file).exists():
        print(f"\n⚠️  Payment file not found: {payment_file}")
        print("Available Excel files:")
        for f in Path(".").glob("*.xlsx"):
            print(f"  - {f.name}")
        return

    # Load payment file
    print(f"\n✓  Loading payment file: {payment_file}")
    df = pd.read_excel(payment_file)
    print(f"✓  Loaded {len(df)} rows")

    # Find relevant columns
    print(f"\nColumns in file: {list(df.columns)[:10]}...")

    # Look for payment method and amount columns
    method_col = None
    amount_col = None
    order_col = None

    for col in df.columns:
        col_lower = col.lower()
        if 'payment' in col_lower and 'method' in col_lower:
            method_col = col
        elif 'payment' in col_lower and 'amount' in col_lower:
            amount_col = col  # Payment file has Payments/Amount
        elif 'subtotal' in col_lower:
            if 'w/o tax' in col_lower or 'without tax' in col_lower:
                amount_col = col  # Prefer w/o tax
            elif not amount_col:
                amount_col = col
        elif 'order' in col_lower and ('ref' in col_lower or 'number' in col_lower or col_lower == 'order'):
            order_col = col

    if not method_col or not amount_col:
        print(f"\n⚠️  Could not find required columns")
        print(f"   Payment method column: {method_col}")
        print(f"   Amount column: {amount_col}")
        return

    print(f"\n✓  Using columns:")
    print(f"   Payment Method: {method_col}")
    print(f"   Amount: {amount_col}")
    if order_col:
        print(f"   Order: {order_col}")

    # Filter for TABBY and TAMARA
    df_filtered = df[df[method_col].notna()].copy()
    df_filtered[method_col] = df_filtered[method_col].astype(str).str.strip().str.upper()
    df_filtered = df_filtered[df_filtered[method_col].isin(['TABBY', 'TAMARA'])]

    print(f"\n✓  Found {len(df_filtered)} TABBY/TAMARA transactions")

    # Calculate expected charges
    print("\n" + "="*80)
    print("CHARGE CALCULATION DETAILS")
    print("="*80)

    results = []

    for idx, row in df_filtered.iterrows():
        method = row[method_col]
        amount = float(row[amount_col])
        order = row[order_col] if order_col else idx

        expected_charge = calculate_expected_charge(amount, method)

        if method == "TAMARA":
            fixed = 1.5
            rate = 0.0425
        else:  # TABBY
            fixed = 1.0
            rate = 0.05

        variable = abs(amount) * rate

        results.append({
            'Order': order,
            'Method': method,
            'Amount': amount,
            'Fixed': fixed,
            'Variable': variable,
            'Expected_Charge': expected_charge
        })

    # Show sample calculations
    results_df = pd.DataFrame(results)
    print("\nSample calculations (first 10):")
    print(results_df.head(10).to_string(index=False))

    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)

    for method in ['TABBY', 'TAMARA']:
        method_data = results_df[results_df['Method'] == method]
        if len(method_data) > 0:
            print(f"\n{method}:")
            print(f"  Total transactions: {len(method_data)}")
            print(f"  Total invoice amount: {method_data['Amount'].sum():,.2f} SAR")
            print(f"  Total charges (expected): {method_data['Expected_Charge'].sum():,.2f} SAR")
            print(f"  Average charge per transaction: {method_data['Expected_Charge'].mean():.2f} SAR")
            print(f"  Min charge: {method_data['Expected_Charge'].min():.2f} SAR")
            print(f"  Max charge: {method_data['Expected_Charge'].max():.2f} SAR")

    # Export to CSV for verification
    output_file = "charge_calculation_expected.csv"
    results_df.to_csv(output_file, index=False)
    print(f"\n✓  Exported expected charges to: {output_file}")

    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80)
    print("\nNext steps:")
    print("1. Review the expected charges above")
    print("2. Generate journal template using Odoo-export-FBDA-template.py")
    print("3. Compare generated journal charges with expected values")
    print("4. Identify any mismatches")

if __name__ == "__main__":
    main()
