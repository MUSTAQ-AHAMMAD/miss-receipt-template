#!/usr/bin/env python3
"""
Trace Journal Entry Amount Flow
================================
This script demonstrates exactly where invoice amounts are picked from
and how they're used in journal entry generation.

It shows:
1. Where the invoice amount comes from (Transaction Line Amount column)
2. How it's used to calculate charges
3. What actually goes into the journal entries (only charges, not full invoice)
"""

import pandas as pd
from pathlib import Path

# Simulate the data flow
print("="*80)
print("JOURNAL ENTRY AMOUNT FLOW ANALYSIS")
print("="*80)
print()

# Step 1: Show where the amount is picked from
print("STEP 1: Source Data (Payment/Invoice File)")
print("-" * 80)
print("The system reads from a payment file with these columns:")
print("  - Transaction Number")
print("  - Receipt Method Name (TABBY/TAMARA)")
print("  - Transaction Date")
print("  - Transaction Line Amount  ← THIS IS THE INVOICE AMOUNT")
print()

# Example data
example_data = pd.DataFrame([
    {
        "Transaction Number": "INV-001",
        "Receipt Method Name": "TABBY",
        "Transaction Date": "2026-03-15",
        "Transaction Line Amount": 1000.0,  # Full invoice amount
        "Warehouse Code": "STORE01"
    },
    {
        "Transaction Number": "INV-002",
        "Receipt Method Name": "TAMARA",
        "Transaction Date": "2026-03-15",
        "Transaction Line Amount": 500.0,  # Full invoice amount
        "Warehouse Code": "STORE01"
    }
])

print("Example Payment Data:")
print(example_data.to_string(index=False))
print()

# Step 2: Grouping and aggregation
print("STEP 2: Data Grouping (Odoo-export-FBDA-template.py:4355-4357)")
print("-" * 80)
print("Code: grouped = invoices.groupby([...]).agg({'Transaction Line Amount': 'sum'})")
print()
grouped = example_data.groupby(
    ["Transaction Number", "Receipt Method Name", "Transaction Date", "Warehouse Code"],
    dropna=False
).agg({
    "Transaction Line Amount": "sum"
}).reset_index()

print("Grouped Data:")
print(grouped.to_string(index=False))
print()

# Step 3: Amount extraction
print("STEP 3: Amount Extraction (Odoo-export-FBDA-template.py:4425)")
print("-" * 80)
print("Code: amount = float(row['Transaction Line Amount'])")
print()
print("For each row, the system extracts:")
for idx, row in grouped.iterrows():
    amount = float(row["Transaction Line Amount"])
    method = row["Receipt Method Name"]
    print(f"  {method}: amount = {amount:.2f} SAR (from Transaction Line Amount)")
print()

# Step 4: Charge calculation
print("STEP 4: Charge Calculation (Odoo-export-FBDA-template.py:4449-4456)")
print("-" * 80)
print("Code: total_charge = fixed_charge + (abs_amount * rate)")
print()

# Load actual charge rates from CSV
charges_file = Path(__file__).parent / "SERVICE_PROVIDER_JOURNAL_META_Charges.csv"
if charges_file.exists():
    charges_df = pd.read_csv(charges_file)
    print("Charge Configuration from SERVICE_PROVIDER_JOURNAL_META_Charges.csv:")

    for provider in ["TABBY", "TAMARA"]:
        provider_rows = charges_df[
            (charges_df["SERVICE_PROVIDER"] == provider) &
            (charges_df["IS_CASH"] == "0")
        ]
        if not provider_rows.empty:
            fixed = provider_rows.iloc[0]["FIXED_FREIGHT_CHARGE"]
            rate = provider_rows.iloc[0]["BANK_CHARGE_RATE"]
            print(f"  {provider}: Fixed={fixed} SAR, Rate={rate*100:.2f}%")
    print()

    # Calculate charges for example data
    print("Charge Calculations:")
    for idx, row in grouped.iterrows():
        amount = float(row["Transaction Line Amount"])
        method = row["Receipt Method Name"]

        provider_rows = charges_df[
            (charges_df["SERVICE_PROVIDER"] == method) &
            (charges_df["IS_CASH"] == "0")
        ]
        if not provider_rows.empty:
            fixed = float(provider_rows.iloc[0]["FIXED_FREIGHT_CHARGE"])
            rate = float(provider_rows.iloc[0]["BANK_CHARGE_RATE"])
            total_charge = fixed + (amount * rate)

            print(f"  {method} (Invoice: {amount:.2f} SAR):")
            print(f"    Formula: {fixed} + ({amount:.2f} × {rate})")
            print(f"    Calculation: {fixed} + {amount * rate:.2f} = {total_charge:.2f} SAR")
            print()
else:
    print("  (Charges file not found - using example values)")
    print("  TABBY: Fixed=1 SAR, Rate=5%")
    print("  TAMARA: Fixed=1.5 SAR, Rate=4.25%")
    print()

# Step 5: Journal entry generation
print("STEP 5: Journal Entry Generation (Odoo-export-FBDA-template.py:4576-4632)")
print("-" * 80)
print("IMPORTANT: Lines 4576-4583 show that payment entries are COMMENTED OUT")
print()
print("Code comments state:")
print("  # ── JOURNAL TEMPLATE CHANGE: Only generate charge entries, not payment entries ──")
print("  # The payment amounts are already recorded elsewhere in the system.")
print("  # Journal template should ONLY show the service provider charges (TABBY/TAMARA fees).")
print()
print("Therefore:")
print("  ❌ Payment amount entries (lines 4582-4583) are SKIPPED (commented out)")
print("  ✅ Only charge entries (lines 4629-4630) are ADDED to journal")
print()

# Step 6: What goes into the journal
print("STEP 6: What Actually Goes Into the Journal Entries")
print("-" * 80)
print("For TABBY invoice of 1,000 SAR:")
print("  Invoice Amount: 1,000 SAR")
print("  Calculated Charge: 1 + (1,000 × 0.05) = 51 SAR")
print("  Journal Entry 1: Debit 3020044 = 51 SAR")
print("  Journal Entry 2: Credit 5000104 = 51 SAR")
print("  ❌ Invoice amount (1,000 SAR) is NOT in the journal")
print()
print("For TAMARA invoice of 500 SAR:")
print("  Invoice Amount: 500 SAR")
print("  Calculated Charge: 1.5 + (500 × 0.0425) = 22.75 SAR")
print("  Journal Entry 1: Debit 3020044 = 22.75 SAR")
print("  Journal Entry 2: Credit 5000104 = 22.75 SAR")
print("  ❌ Invoice amount (500 SAR) is NOT in the journal")
print()

# Summary
print("="*80)
print("SUMMARY: Where Invoice Amount is Picked From & How It's Used")
print("="*80)
print()
print("1. SOURCE: Invoice amount comes from 'Transaction Line Amount' column")
print("   Location: Odoo-export-FBDA-template.py:4425")
print("   Code: amount = float(row['Transaction Line Amount'])")
print()
print("2. USAGE: Invoice amount is used ONLY to calculate the service charge")
print("   Location: Odoo-export-FBDA-template.py:4456")
print("   Code: total_charge = fixed_charge + (abs_amount * rate)")
print()
print("3. OUTPUT: Only the CHARGE amount goes into journal entries, NOT invoice amount")
print("   Location: Odoo-export-FBDA-template.py:4629-4630")
print("   Code: journal_entries.append(charge_credit_entry)")
print("         journal_entries.append(charge_debit_entry)")
print()
print("4. VERIFICATION: Payment amount entries are explicitly SKIPPED")
print("   Location: Odoo-export-FBDA-template.py:4582-4583 (commented out)")
print("   Code: # journal_entries.append(credit_account_entry)")
print("         # journal_entries.append(debit_account_entry)")
print()
print("="*80)
print("CONCLUSION")
print("="*80)
print("The invoice amount IS picked from the payment file (Transaction Line Amount),")
print("but it's ONLY used to calculate the service charge percentage.")
print("The FULL INVOICE AMOUNT itself is NOT included in the journal entries.")
print("Only the CALCULATED CHARGE amounts appear in the journal.")
print()
print("If you're seeing the full invoice amount in journal entries, this means:")
print("  1. Someone uncommented lines 4582-4583 (payment entries), OR")
print("  2. The charge calculation is producing values equal to the invoice (unlikely), OR")
print("  3. You're looking at an old version of the output before this fix")
print("="*80)
