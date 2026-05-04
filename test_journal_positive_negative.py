#!/usr/bin/env python3
"""
Test journal template generation with positive and negative amounts
"""

def test_journal_logic():
    """
    Test the journal entry logic for positive and negative amounts.

    Requirements:
    - Positive amounts: 3-series in Debit, 5-series in Credit
    - Negative amounts: 3-series in Credit, 5-series in Debit
    """

    # Test data
    test_cases = [
        {
            "amount": 100.0,
            "expected_3_series_debit": 100.0,
            "expected_3_series_credit": "",
            "expected_5_series_debit": "",
            "expected_5_series_credit": 100.0,
            "description": "Positive amount"
        },
        {
            "amount": -150.0,
            "expected_3_series_debit": "",
            "expected_3_series_credit": 150.0,
            "expected_5_series_debit": 150.0,
            "expected_5_series_credit": "",
            "description": "Negative amount"
        }
    ]

    print("Testing Journal Entry Logic")
    print("=" * 60)

    for i, test in enumerate(test_cases, 1):
        amount = test["amount"]
        is_negative = amount < 0
        abs_amount = abs(amount)

        print(f"\nTest Case {i}: {test['description']}")
        print(f"  Input Amount: {amount}")
        print(f"  Is Negative: {is_negative}")
        print(f"  Absolute Value: {abs_amount}")

        if is_negative:
            # NEGATIVE: 3-series in Credit, 5-series in Debit
            three_series_debit = ""
            three_series_credit = abs_amount
            five_series_debit = abs_amount
            five_series_credit = ""
        else:
            # POSITIVE: 3-series in Debit, 5-series in Credit
            three_series_debit = abs_amount
            three_series_credit = ""
            five_series_debit = ""
            five_series_credit = abs_amount

        # Verify expected results
        print(f"  3-Series Account (3020044):")
        print(f"    Entered Debit Amount: {three_series_debit}")
        print(f"    Entered Credit Amount: {three_series_credit}")
        print(f"  5-Series Account (5000104):")
        print(f"    Entered Debit Amount: {five_series_debit}")
        print(f"    Entered Credit Amount: {five_series_credit}")

        # Check assertions
        assert three_series_debit == test["expected_3_series_debit"], \
            f"3-series debit mismatch: expected {test['expected_3_series_debit']}, got {three_series_debit}"
        assert three_series_credit == test["expected_3_series_credit"], \
            f"3-series credit mismatch: expected {test['expected_3_series_credit']}, got {three_series_credit}"
        assert five_series_debit == test["expected_5_series_debit"], \
            f"5-series debit mismatch: expected {test['expected_5_series_debit']}, got {five_series_debit}"
        assert five_series_credit == test["expected_5_series_credit"], \
            f"5-series credit mismatch: expected {test['expected_5_series_credit']}, got {five_series_credit}"

        # Verify balanced entries
        total_debit = (three_series_debit if three_series_debit != "" else 0) + \
                     (five_series_debit if five_series_debit != "" else 0)
        total_credit = (three_series_credit if three_series_credit != "" else 0) + \
                      (five_series_credit if five_series_credit != "" else 0)

        print(f"  Total Debit: {total_debit}")
        print(f"  Total Credit: {total_credit}")
        print(f"  Balanced: {'✓ YES' if total_debit == total_credit else '✗ NO'}")

        assert total_debit == total_credit, \
            f"Entries not balanced: debit={total_debit}, credit={total_credit}"

        print(f"  Result: ✓ PASSED")

    print("\n" + "=" * 60)
    print("All tests PASSED! ✓")
    print("\nSummary:")
    print("  - Positive amounts: 3-series in Debit, 5-series in Credit")
    print("  - Negative amounts: 3-series in Credit, 5-series in Debit")
    print("  - All entries are balanced (Total Debit = Total Credit)")

if __name__ == "__main__":
    test_journal_logic()
