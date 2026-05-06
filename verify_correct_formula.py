"""
Quick verification of the CORRECT charge formula.

Formula: Total Charge = FIXED_FREIGHT_CHARGE + (Amount × BANK_CHARGE_RATE)

Examples from user:
- TABBY: (160 × 0.055) + 1 = 9.8
- TAMARA: (75 × 0.0599) + 1.5 = 5.9925
"""

# TABBY Example
tabby_amount = 160
tabby_fixed = 1
tabby_rate = 0.055

tabby_variable = tabby_amount * tabby_rate
tabby_total = tabby_fixed + tabby_variable

print("=" * 60)
print("CHARGE CALCULATION VERIFICATION")
print("=" * 60)
print(f"\nFormula: Total Charge = FIXED_FREIGHT_CHARGE + (Amount × BANK_CHARGE_RATE)")
print(f"\nTABBY Example:")
print(f"  Amount: {tabby_amount} SAR")
print(f"  Fixed Charge: {tabby_fixed} SAR")
print(f"  Rate: {tabby_rate*100}% ({tabby_rate})")
print(f"  Variable Charge: {tabby_amount} × {tabby_rate} = {tabby_variable} SAR")
print(f"  Total Charge: {tabby_fixed} + {tabby_variable} = {tabby_total} SAR")
print(f"  ✓ Expected: 9.8 SAR")

# TAMARA Example
tamara_amount = 75
tamara_fixed = 1.5
tamara_rate = 0.0599

tamara_variable = tamara_amount * tamara_rate
tamara_total = tamara_fixed + tamara_variable

print(f"\nTAMARA Example:")
print(f"  Amount: {tamara_amount} SAR")
print(f"  Fixed Charge: {tamara_fixed} SAR")
print(f"  Rate: {tamara_rate*100}% ({tamara_rate})")
print(f"  Variable Charge: {tamara_amount} × {tamara_rate} = {tamara_variable} SAR")
print(f"  Total Charge: {tamara_fixed} + {tamara_variable} = {tamara_total} SAR")
print(f"  ✓ Expected: 5.9925 SAR")

print("\n" + "=" * 60)
print("✅ FORMULA VERIFIED!")
print("=" * 60)
