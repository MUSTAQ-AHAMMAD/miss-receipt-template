#!/usr/bin/env python3
"""
Test script to verify bank account numbers are preserved in full
when generating receipts in AR Invoice mode.

This test simulates the UI workflow:
1. Load Receipt_Methods.csv
2. Process an AR Invoice CSV
3. Generate Standard Receipts
4. Generate Misc Receipts
5. Verify RemittanceBankAccountNumber and BankAccountNumber contain full text
"""

import csv
import sys
from pathlib import Path

def test_bank_account_preservation():
    """Test that bank account numbers are preserved without trimming"""

    print("=" * 100)
    print("BANK ACCOUNT NUMBER VERIFICATION TEST")
    print("=" * 100)
    print()

    # Step 1: Read Receipt_Methods.csv and show what we expect
    print("Step 1: Reading Receipt_Methods.csv")
    print("-" * 100)

    receipt_methods_file = Path("Receipt_Methods.csv")
    if not receipt_methods_file.exists():
        print(f"❌ ERROR: {receipt_methods_file} not found!")
        return False

    # Read and display ABHATIMSQR entries
    expected_accounts = {}
    with open(receipt_methods_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            bank_name = row.get('BANK_ACCOUNT_NAME', '').strip()
            if 'ABHATIMSQR' in bank_name:
                method = row.get('RECEIPT_METHOD_NAME', '').strip()
                bank_num = row.get('BANK_ACCOUNT_NUMBER', '').strip()
                expected_accounts[method] = {
                    'bank_name': bank_name,
                    'bank_number': bank_num
                }
                print(f"   {method:10s} -> Bank Account: {bank_num}")

    if not expected_accounts:
        print("❌ ERROR: No ABHATIMSQR entries found in Receipt_Methods.csv")
        return False

    print(f"\n✓ Found {len(expected_accounts)} ABHATIMSQR entries")
    print()

    # Step 2: Expected values for verification
    print("Step 2: Expected Bank Account Numbers")
    print("-" * 100)

    test_expectations = {
        'AMEX': '157-95017321-ABHATIMSQR',
        'Cash': 'Cash ABHATIMSQR',
        'Mada': '157-95017321-ABHATIMSQR',
        'Master': '157-95017321-ABHATIMSQR',
        'Visa': '157-95017321-ABHATIMSQR',
    }

    for method, expected in test_expectations.items():
        print(f"   {method:10s} should have: '{expected}'")

    print()

    # Step 3: Check if output directory exists from previous runs
    print("Step 3: Checking for Generated Receipt Files")
    print("-" * 100)

    output_dirs = [
        Path("ORACLE_FUSION_OUTPUT"),
        Path("TEST_OUTPUT"),
    ]

    receipt_files_found = []
    for output_dir in output_dirs:
        if output_dir.exists():
            for receipt_file in output_dir.glob("Receipt_*.csv"):
                receipt_files_found.append(receipt_file)
            for misc_file in output_dir.glob("MiscReceipt_*.csv"):
                receipt_files_found.append(misc_file)

    if not receipt_files_found:
        print("   ℹ️  No generated receipt files found in output directories")
        print("   ℹ️  You need to run the generation process first through the UI")
        print()
        print("NEXT STEPS:")
        print("-" * 100)
        print("1. Access the web UI (typically at http://localhost:5000)")
        print("2. Select 'AR Invoice Mode'")
        print("3. Upload an AR Invoice CSV file (e.g., AR_Invoice_ALARDAH_5_31Mar.csv)")
        print("4. Click 'Generate' and wait for completion")
        print("5. Download and inspect the receipt files")
        print("6. Look for 'RemittanceBankAccountNumber' in Standard Receipts")
        print("7. Look for 'BankAccountNumber' in Miscellaneous Receipts")
        print()
        print("Expected values should be FULL text like: '157-95017321-ABHATIMSQR'")
        print("NOT trimmed like: '157-95017321' or '157'")
        return None

    # Step 4: Verify generated files
    print(f"   ✓ Found {len(receipt_files_found)} generated receipt files")
    print()

    print("Step 4: Verifying Bank Account Numbers in Generated Files")
    print("-" * 100)

    verification_results = []

    for receipt_file in receipt_files_found:
        print(f"\n   Checking: {receipt_file.name}")

        with open(receipt_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for idx, row in enumerate(reader):
                if idx >= 5:  # Check first 5 rows only
                    break

                # Check Standard Receipt files
                if 'RemittanceBankAccountNumber' in row:
                    bank_account = row.get('RemittanceBankAccountNumber', '')
                    receipt_method = row.get('ReceiptMethod', '')

                    if 'ABHATIMSQR' in bank_account or 'ABHATIMSQR' in str(row.get('CustomerSite', '')):
                        print(f"      Row {idx+1}: {receipt_method:10s} -> RemittanceBankAccountNumber = '{bank_account}'")

                        # Check if it's the expected full format
                        if receipt_method in test_expectations:
                            expected = test_expectations[receipt_method]
                            if bank_account == expected:
                                verification_results.append(('PASS', receipt_method, bank_account))
                                print(f"               ✓ CORRECT: Matches expected '{expected}'")
                            else:
                                verification_results.append(('FAIL', receipt_method, bank_account))
                                print(f"               ❌ WRONG: Expected '{expected}'")

                # Check Misc Receipt files
                if 'BankAccountNumber' in row:
                    bank_account = row.get('BankAccountNumber', '')
                    receipt_method = row.get('ReceiptMethodName', '')

                    if 'ABHATIMSQR' in bank_account:
                        print(f"      Row {idx+1}: {receipt_method:10s} -> BankAccountNumber = '{bank_account}'")

                        # Check if it's the expected full format
                        if receipt_method in test_expectations:
                            expected = test_expectations[receipt_method]
                            if bank_account == expected:
                                verification_results.append(('PASS', receipt_method, bank_account))
                                print(f"               ✓ CORRECT: Matches expected '{expected}'")
                            else:
                                verification_results.append(('FAIL', receipt_method, bank_account))
                                print(f"               ❌ WRONG: Expected '{expected}'")

    # Step 5: Summary
    print()
    print("=" * 100)
    print("VERIFICATION SUMMARY")
    print("=" * 100)

    if not verification_results:
        print("⚠️  No ABHATIMSQR bank accounts found in generated files")
        print("   This could mean:")
        print("   1. The test data doesn't include ABHATIMSQR stores")
        print("   2. The receipts were generated for different stores")
        print("   3. You need to generate receipts with data that includes ABHATIMSQR")
        return None

    passed = sum(1 for r in verification_results if r[0] == 'PASS')
    failed = sum(1 for r in verification_results if r[0] == 'FAIL')

    print(f"Total Checks: {len(verification_results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()

    if failed == 0:
        print("✅ ALL TESTS PASSED!")
        print("Bank account numbers are being preserved correctly.")
        return True
    else:
        print("❌ SOME TESTS FAILED!")
        print("Bank account numbers are NOT being preserved correctly.")
        for status, method, account in verification_results:
            if status == 'FAIL':
                print(f"   FAILED: {method} -> '{account}'")
        return False

if __name__ == "__main__":
    result = test_bank_account_preservation()
    if result is True:
        sys.exit(0)
    elif result is False:
        sys.exit(1)
    else:
        sys.exit(2)  # No data to verify
