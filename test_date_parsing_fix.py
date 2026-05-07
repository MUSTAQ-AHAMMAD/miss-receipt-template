#!/usr/bin/env python3
"""
Test date parsing fix for bulk file upload.

This test verifies that dates in various formats are parsed correctly
for different stores.
"""

import sys
from datetime import datetime
import pandas as pd

# Import the parse_flexible_date function
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# We need to import from the main module
import importlib.util
spec = importlib.util.spec_from_file_location(
    "odoo_module",
    Path(__file__).parent / "Odoo-export-FBDA-template.py"
)
odoo_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(odoo_module)

parse_flexible_date = odoo_module.parse_flexible_date

def test_date_formats():
    """Test various date formats that might appear in bulk files."""

    test_cases = [
        # (input, expected_year, expected_month, expected_day, description)
        ("2026-03-05 23:50:01", 2026, 3, 5, "ISO datetime format"),
        ("2026-03-05", 2026, 3, 5, "ISO date format"),
        ("3/9/2026", 2026, 9, 3, "Ambiguous format - interpreted as day/month (3rd Sept)"),
        ("09/03/2026", 2026, 3, 9, "Day-first format (9th March)"),
        ("05-Mar-2026", 2026, 3, 5, "Month name format"),
        ("05-03-2026", 2026, 3, 5, "Dash separated format (5th March)"),
        ("2026/03/05", 2026, 3, 5, "Slash separated ISO format"),
        ("05.03.2026", 2026, 3, 5, "Dot separated format (5th March)"),
        ("05 Mar 2026", 2026, 3, 5, "Space separated month name"),
        ("05-Mar-26", 2026, 3, 5, "Short year format"),
        ("3/9/26", 2026, 9, 3, "Ambiguous short format - interpreted as day/month"),
    ]

    print("Testing date parsing with various formats:")
    print("=" * 80)

    passed = 0
    failed = 0

    for input_date, exp_year, exp_month, exp_day, description in test_cases:
        result = parse_flexible_date(input_date)

        if pd.notna(result):
            if (result.year == exp_year and
                result.month == exp_month and
                result.day == exp_day):
                status = "✓ PASS"
                passed += 1
            else:
                status = f"✗ FAIL (got {result.year}-{result.month:02d}-{result.day:02d})"
                failed += 1
        else:
            status = "✗ FAIL (returned NaT)"
            failed += 1

        print(f"{status:20} | {description:35} | '{input_date}'")

    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")

    return failed == 0

def test_invalid_dates():
    """Test that invalid dates return NaT."""

    print("\nTesting invalid date handling:")
    print("=" * 80)

    invalid_dates = [
        "",
        None,
        "invalid",
        "99/99/9999",
        "not-a-date",
    ]

    passed = 0
    failed = 0

    for input_date in invalid_dates:
        result = parse_flexible_date(input_date)

        if pd.isna(result):
            status = "✓ PASS (correctly returned NaT)"
            passed += 1
        else:
            status = f"✗ FAIL (parsed as {result})"
            failed += 1

        print(f"{status:40} | '{input_date}'")

    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(invalid_dates)} tests")

    return failed == 0

def test_store_specific_dates():
    """Test dates that might be specific to different stores."""

    print("\nTesting store-specific date scenarios:")
    print("=" * 80)

    # Simulate different stores with different date formats
    store_dates = [
        ("ZAHRAN", "5/3/2026", 2026, 3, 5, "ZAHRAN store - day/month (5th March)"),
        ("MAKKAH", "2026-03-15", 2026, 3, 15, "MAKKAH store - ISO format"),
        ("SALAMJED", "15-Mar-2026", 2026, 3, 15, "SALAMJED store - month name"),
        ("ALARIDAH", "3/9/2026", 2026, 9, 3, "ALARIDAH store - day/month (3rd Sept)"),
    ]

    passed = 0
    failed = 0

    for store, input_date, exp_year, exp_month, exp_day, description in store_dates:
        result = parse_flexible_date(input_date)

        if pd.notna(result):
            if (result.year == exp_year and
                result.month == exp_month and
                result.day == exp_day):
                status = "✓ PASS"
                passed += 1
            else:
                status = f"✗ FAIL (got {result.year}-{result.month:02d}-{result.day:02d})"
                failed += 1
        else:
            status = "✗ FAIL (returned NaT)"
            failed += 1

        print(f"{status:20} | {description:45} | '{input_date}'")

    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(store_dates)} tests")

    return failed == 0

def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("DATE PARSING FIX - TEST SUITE")
    print("=" * 80 + "\n")

    test1_passed = test_date_formats()
    test2_passed = test_invalid_dates()
    test3_passed = test_store_specific_dates()

    print("\n" + "=" * 80)
    print("OVERALL TEST RESULTS")
    print("=" * 80)

    if test1_passed and test2_passed and test3_passed:
        print("✓ ALL TESTS PASSED")
        print("\nThe date parsing fix correctly handles:")
        print("  - Multiple date formats (ISO, US, EU, month names)")
        print("  - Invalid dates (returns NaT)")
        print("  - Store-specific date scenarios")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        if not test1_passed:
            print("  - Date format parsing needs attention")
        if not test2_passed:
            print("  - Invalid date handling needs attention")
        if not test3_passed:
            print("  - Store-specific scenarios need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())
