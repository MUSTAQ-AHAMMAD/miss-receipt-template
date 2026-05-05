"""
Test script to demonstrate the new charge calculation logic for Tabby and Tamara.

This script:
1. Reads the sales lines file (Order line items)
2. Reads the payment file (Order Ref and payment methods)
3. Reads the charges file (SERVICE_PROVIDER_JOURNAL_META_Charges.csv)
4. Calculates charges using the formula:
   - Total Charge = (Amount × Rate) × (1 + VAT)
   - Net Receipt = Amount - Total Charge

The calculation is done per order line matching Order Ref between files.
"""

import pandas as pd
from pathlib import Path

# VAT rate (15% in Saudi Arabia)
VAT_RATE = 0.15

def load_charges_data(charges_file):
    """Load charges configuration from CSV."""
    df = pd.read_csv(charges_file)
    # Create a lookup dict: (SERVICE_PROVIDER, IS_CASH) -> BANK_CHARGE_RATE
    charges_lookup = {}
    for _, row in df.iterrows():
        provider = str(row['SERVICE_PROVIDER']).strip().upper()
        is_cash = str(row['IS_CASH']).strip()
        rate = row['BANK_CHARGE_RATE']

        # Only store non-null rates
        if pd.notna(rate):
            key = (provider, is_cash)
            charges_lookup[key] = float(rate)

    return charges_lookup

def calculate_charges(amount, rate, vat_rate=VAT_RATE):
    """
    Calculate total charge and net receipt.

    Formula:
    - Total Charge = (Amount × Rate) × (1 + VAT)
    - Net Receipt = Amount - Total Charge

    Args:
        amount: The transaction amount
        rate: The charge rate (e.g., 0.055 for 5.5%)
        vat_rate: VAT rate (default 0.15 for 15%)

    Returns:
        tuple: (total_charge, net_receipt)
    """
    total_charge = (amount * rate) * (1 + vat_rate)
    net_receipt = amount - total_charge
    return total_charge, net_receipt

def process_orders(sales_file, payment_file, charges_file):
    """Process orders and calculate charges."""

    # Load data
    print("=" * 80)
    print("LOADING DATA FILES")
    print("=" * 80)

    sales_df = pd.read_excel(sales_file)
    print(f"✓ Loaded sales lines: {len(sales_df)} rows")
    print(f"  Columns: {sales_df.columns.tolist()}")

    payment_df = pd.read_excel(payment_file)
    print(f"✓ Loaded payment file: {len(payment_df)} rows")
    print(f"  Columns: {payment_df.columns.tolist()}")

    charges_lookup = load_charges_data(charges_file)
    print(f"✓ Loaded charges data: {len(charges_lookup)} provider configurations")

    # Show available charge rates
    print("\nCharge Rates Configuration (from CSV):")
    for (provider, is_cash), rate in sorted(charges_lookup.items()):
        cash_label = "CASH" if is_cash == "1" else "NON-CASH"
        print(f"  {provider:15s} ({cash_label:8s}): {rate*100:.2f}%")

    # Override with user-specified rates for TABBY and TAMARA
    print("\n⚠️  NOTE: Using USER-SPECIFIED rates (overriding CSV):")
    print("  TABBY:  0.5% (0.005)")
    print("  TAMARA: 0.3% (0.003)")
    charges_lookup[('TABBY', '0')] = 0.005
    charges_lookup[('TAMARA', '0')] = 0.003

    # Filter payment file to only TABBY and TAMARA
    valid_providers = {'TABBY', 'TAMARA'}
    payment_df['Payment Method Upper'] = payment_df['Payments/Payment Method'].str.upper()
    filtered_payments = payment_df[payment_df['Payment Method Upper'].isin(valid_providers)].copy()

    print(f"\n✓ Filtered to TABBY/TAMARA payments: {len(filtered_payments)} payment lines")

    # Get unique Order Refs from filtered payments
    unique_orders = filtered_payments['Order Ref'].dropna().unique()
    print(f"✓ Unique orders with TABBY/TAMARA: {len(unique_orders)}")

    # Process each order
    print("\n" + "=" * 80)
    print("CALCULATING CHARGES FOR EACH ORDER")
    print("=" * 80)

    results = []

    # Group payments by Order Ref
    payment_groups = filtered_payments.groupby('Order Ref')

    for order_ref in unique_orders[:10]:  # Process first 10 for demonstration
        print(f"\n{'─' * 80}")
        print(f"Order: {order_ref}")
        print(f"{'─' * 80}")

        # Get payment methods for this order
        order_payments = payment_groups.get_group(order_ref)

        # Get sales lines for this order (match by Order Ref)
        order_sales = sales_df[sales_df['Order Ref'] == order_ref]

        if order_sales.empty:
            print(f"⚠️  No sales lines found for order {order_ref}")
            continue

        # Get date and branch from first payment line
        order_date = order_payments.iloc[0]['Date']
        order_branch = order_payments.iloc[0]['Branch']

        print(f"Date: {order_date}")
        print(f"Branch: {order_branch}")
        print(f"Sales Lines: {len(order_sales)} items")

        # Calculate total amount from sales lines (excluding discount items)
        # Assuming discount items might have negative amounts or specific identifiers
        total_sales_amount = order_sales['Payments/Amount'].sum()
        print(f"Total Sales Amount: {total_sales_amount:.2f} SAR")

        # Process each payment method for this order
        for _, payment in order_payments.iterrows():
            payment_method = payment['Payment Method Upper']
            payment_amount = payment['Payments/Amount']

            print(f"\n  Payment Method: {payment_method}")
            print(f"  Payment Amount: {payment_amount:.2f} SAR")

            # Get charge rate for this provider (assuming non-cash)
            is_cash = "0"  # TABBY/TAMARA are non-cash
            charge_key = (payment_method, is_cash)

            if charge_key not in charges_lookup:
                print(f"  ⚠️  No charge rate found for {payment_method}")
                continue

            rate = charges_lookup[charge_key]
            print(f"  Charge Rate: {rate*100:.2f}%")
            print(f"  VAT Rate: {VAT_RATE*100:.0f}%")

            # Calculate charges
            total_charge, net_receipt = calculate_charges(payment_amount, rate, VAT_RATE)

            print(f"\n  Calculation:")
            print(f"    Total Charge = (Amount × Rate) × (1 + VAT)")
            print(f"    Total Charge = ({payment_amount:.2f} × {rate}) × (1 + {VAT_RATE})")
            print(f"    Total Charge = ({payment_amount:.2f} × {rate}) × {1 + VAT_RATE}")
            print(f"    Total Charge = {payment_amount * rate:.2f} × {1 + VAT_RATE}")
            print(f"    Total Charge = {total_charge:.2f} SAR")
            print(f"\n    Net Receipt = Amount - Total Charge")
            print(f"    Net Receipt = {payment_amount:.2f} - {total_charge:.2f}")
            print(f"    Net Receipt = {net_receipt:.2f} SAR")

            results.append({
                'Order Ref': order_ref,
                'Date': order_date,
                'Branch': order_branch,
                'Payment Method': payment_method,
                'Original Amount': payment_amount,
                'Charge Rate': f"{rate*100:.2f}%",
                'Total Charge': total_charge,
                'Net Receipt': net_receipt
            })

    # Create summary DataFrame
    print("\n" + "=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)

    summary_df = pd.DataFrame(results)
    if not summary_df.empty:
        print(summary_df.to_string(index=False))

        # Calculate totals
        print("\n" + "─" * 80)
        print("TOTALS:")
        print(f"  Total Original Amount: {summary_df['Original Amount'].sum():.2f} SAR")
        print(f"  Total Charges: {summary_df['Total Charge'].sum():.2f} SAR")
        print(f"  Total Net Receipt: {summary_df['Net Receipt'].sum():.2f} SAR")

        # Save to CSV
        output_file = Path(__file__).parent / "charges_calculation_output.csv"
        summary_df.to_csv(output_file, index=False)
        print(f"\n✓ Results saved to: {output_file}")
    else:
        print("No results to display")

    return summary_df

if __name__ == "__main__":
    # File paths
    repo_root = Path(__file__).parent

    sales_file = repo_root / "MAkkah_SAles_Line.xlsx"
    payment_file = repo_root / "MAKKAH payment line 5 to 31 March.xlsx"
    charges_file = repo_root / "SERVICE_PROVIDER_JOURNAL_META_Charges.csv"

    # Check if files exist
    if not sales_file.exists():
        print(f"❌ Sales file not found: {sales_file}")
        exit(1)
    if not payment_file.exists():
        print(f"❌ Payment file not found: {payment_file}")
        exit(1)
    if not charges_file.exists():
        print(f"❌ Charges file not found: {charges_file}")
        exit(1)

    # Process orders and calculate charges
    results = process_orders(sales_file, payment_file, charges_file)

    print("\n" + "=" * 80)
    print("✅ CALCULATION DEMONSTRATION COMPLETE")
    print("=" * 80)
