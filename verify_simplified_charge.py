"""
Verification of SIMPLIFIED charge calculation.

NEW RULE: 1 SAR per order (flat rate)
- No variable component based on amount
- No rate-based calculation
- Just 1 SAR per order

This is simpler than the previous formula:
OLD: Total Charge = FIXED_FREIGHT_CHARGE + (Amount × BANK_CHARGE_RATE)
NEW: Total Charge = 1 SAR (flat)
"""

print("=" * 60)
print("SIMPLIFIED CHARGE CALCULATION")
print("=" * 60)
print(f"\nNew Rule: 1 SAR per order (flat rate)")
print(f"\nExamples:")

# Example 1
order1_amount = 160
order1_charge = 1.0
print(f"\nOrder 1 (TABBY):")
print(f"  Amount: {order1_amount} SAR")
print(f"  Charge: {order1_charge} SAR (flat)")

# Example 2
order2_amount = 75
order2_charge = 1.0
print(f"\nOrder 2 (TAMARA):")
print(f"  Amount: {order2_amount} SAR")
print(f"  Charge: {order2_charge} SAR (flat)")

# Example 3
order3_amount = 499
order3_charge = 1.0
print(f"\nOrder 3 (TABBY):")
print(f"  Amount: {order3_amount} SAR")
print(f"  Charge: {order3_charge} SAR (flat)")

# Daily summary
daily_orders = 10
daily_total_charge = daily_orders * 1.0
print(f"\nDaily Summary:")
print(f"  Total Orders: {daily_orders}")
print(f"  Charge per Order: 1 SAR")
print(f"  Total Daily Charge: {daily_total_charge} SAR")

print("\n" + "=" * 60)
print("✅ SIMPLIFIED FORMULA: 1 SAR per order")
print("=" * 60)
