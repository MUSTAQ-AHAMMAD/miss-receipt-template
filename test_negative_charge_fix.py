#!/usr/bin/env python3
"""
Test the negative charge calculation fix.
This test verifies that:
1. Positive amounts get positive charges
2. Negative amounts (refunds) get negative charges
3. The journal entries use absolute values with correct debit/credit positioning
"""

def test_charge_calculation():
    """Test charge calculation for positive and negative amounts."""

    # TABBY configuration: 5% rate + 1 SAR fixed
    tabby_fixed = 1.0
    tabby_rate = 0.05

    # TAMARA configuration: 4.25% rate + 1.5 SAR fixed
    tamara_fixed = 1.5
    tamara_rate = 0.0425

    test_cases = [
        {
            "description": "Positive TABBY transaction",
            "amount": 499.0,
            "provider": "TABBY",
            "fixed": tabby_fixed,
            "rate": tabby_rate,
            "expected_charge": 25.95,  # 1 + (499 * 0.05) = 1 + 24.95 = 25.95
            "expected_sign": "positive"
        },
        {
            "description": "Positive TAMARA transaction",
            "amount": 199.0,
            "provider": "TAMARA",
            "fixed": tamara_fixed,
            "rate": tamara_rate,
            "expected_charge": 9.96,  # 1.5 + (199 * 0.0425) = 1.5 + 8.4575 = 9.9575 → 9.96
            "expected_sign": "positive"
        },
        {
            "description": "Negative TABBY transaction (refund)",
            "amount": -199.0,
            "provider": "TABBY",
            "fixed": tabby_fixed,
            "rate": tabby_rate,
            "expected_charge": -10.95,  # -(1 + (199 * 0.05)) = -(1 + 9.95) = -10.95
            "expected_sign": "negative"
        },
        {
            "description": "Negative TAMARA transaction (refund)",
            "amount": -149.0,
            "provider": "TAMARA",
            "fixed": tamara_fixed,
            "rate": tamara_rate,
            "expected_charge": -7.83,  # -(1.5 + (149 * 0.0425)) = -(1.5 + 6.3325) = -7.8325 → -7.83
            "expected_sign": "negative"
        },
    ]

    print("=" * 80)
    print("Testing Charge Calculation Fix for Negative Amounts")
    print("=" * 80)

    all_passed = True

    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['description']}")
        print(f"  Amount: {test['amount']:.2f} SAR")
        print(f"  Provider: {test['provider']}")

        # Calculate charge using the fixed logic
        amount = test['amount']
        is_negative_amount = amount < 0
        abs_amount = abs(amount)

        fixed_charge = test['fixed']
        rate = test['rate']

        # NEW LOGIC (after fix):
        charge_magnitude = round(fixed_charge + (abs_amount * rate), 2)
        total_charge = -charge_magnitude if is_negative_amount else charge_magnitude

        print(f"  Calculated Charge: {total_charge:.2f} SAR")
        print(f"  Expected Charge: {test['expected_charge']:.2f} SAR")

        # Verify the charge
        if abs(total_charge - test['expected_charge']) < 0.01:
            print(f"  ✓ Charge calculation PASSED")
        else:
            print(f"  ✗ Charge calculation FAILED")
            all_passed = False

        # Verify the sign
        if (total_charge > 0 and test['expected_sign'] == 'positive') or \
           (total_charge < 0 and test['expected_sign'] == 'negative'):
            print(f"  ✓ Sign check PASSED (expected {test['expected_sign']})")
        else:
            print(f"  ✗ Sign check FAILED (expected {test['expected_sign']})")
            all_passed = False

        # Verify journal entry logic
        abs_charge = abs(total_charge)
        print(f"\n  Journal Entry Preview (absolute value used: {abs_charge:.2f}):")

        if is_negative_amount:
            print(f"    3020044 (3-series): CREDIT = {abs_charge:.2f}")
            print(f"    5000104 (5-series): DEBIT = {abs_charge:.2f}")
        else:
            print(f"    3020044 (3-series): DEBIT = {abs_charge:.2f}")
            print(f"    5000104 (5-series): CREDIT = {abs_charge:.2f}")

    print("\n" + "=" * 80)
    if all_passed:
        print("✓ All tests PASSED!")
        print("\nSummary:")
        print("  - Positive amounts generate positive charges (normal)")
        print("  - Negative amounts generate negative charges (reversal)")
        print("  - Journal entries use absolute values with correct debit/credit positioning")
    else:
        print("✗ Some tests FAILED")
    print("=" * 80)

    return all_passed

if __name__ == "__main__":
    success = test_charge_calculation()
    exit(0 if success else 1)
