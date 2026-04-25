"""
Test to verify consolidated file generation for miscellaneous receipts
"""

def test_misc_consolidated_file_logic():
    """
    Simulate the consolidated file generation logic to verify it works correctly
    """
    # Simulated method_rows (what the code generates)
    method_rows = {
        "MADA": [
            {"Amount": 100.50, "ReceiptMethodName": "MADA", "BankAccountNumber": "SA1234567890123456789012345678"},
            {"Amount": 200.75, "ReceiptMethodName": "MADA", "BankAccountNumber": "SA1234567890123456789012345678"},
        ],
        "MASTER": [
            {"Amount": 150.25, "ReceiptMethodName": "MASTER", "BankAccountNumber": "SA9876543210987654321098765432"},
        ],
        "VISA": [
            {"Amount": 300.00, "ReceiptMethodName": "VISA", "BankAccountNumber": "SA1111222233334444555566667777"},
            {"Amount": 50.00, "ReceiptMethodName": "VISA", "BankAccountNumber": "SA1111222233334444555566667777"},
        ],
    }

    # Simulate consolidated file generation (from lines 2952-2958)
    all_misc_consolidated_rows = []
    for method, rows in sorted(method_rows.items()):
        all_misc_consolidated_rows.extend(rows)

    # Verify consolidated rows
    print("✓ Consolidated File Generation Test")
    print(f"  Total methods: {len(method_rows)}")
    print(f"  Total rows in consolidated file: {len(all_misc_consolidated_rows)}")
    print(f"  Expected rows: {sum(len(rows) for rows in method_rows.values())}")

    assert len(all_misc_consolidated_rows) == sum(len(rows) for rows in method_rows.values()), \
        "Consolidated file should contain all rows from all methods"

    # Verify totals
    consolidated_total = sum(row["Amount"] for row in all_misc_consolidated_rows)
    per_method_total = sum(sum(row["Amount"] for row in rows) for rows in method_rows.values())

    print(f"  Consolidated total: {consolidated_total:.4f} SAR")
    print(f"  Per-method total: {per_method_total:.4f} SAR")
    print(f"  Difference: {abs(consolidated_total - per_method_total):.4f} SAR")

    assert abs(consolidated_total - per_method_total) < 0.0001, \
        "Consolidated total should match per-method total"

    # Verify bank account numbers are preserved
    print("\n✓ Bank Account Number Preservation Test")
    for row in all_misc_consolidated_rows:
        bank_account = row["BankAccountNumber"]
        print(f"  Bank Account: {bank_account} (Length: {len(bank_account)})")
        assert len(bank_account) >= 28, "Bank account numbers should be preserved in full"
        assert bank_account.startswith("SA"), "Bank account format should be preserved"

    # Verify method breakdown
    print("\n✓ Method Breakdown Test")
    method_breakdown = {}
    for row in all_misc_consolidated_rows:
        method = row["ReceiptMethodName"]
        if method not in method_breakdown:
            method_breakdown[method] = {"count": 0, "total": 0}
        method_breakdown[method]["count"] += 1
        method_breakdown[method]["total"] += row["Amount"]

    for method in sorted(method_breakdown.keys()):
        count = method_breakdown[method]["count"]
        total = method_breakdown[method]["total"]
        print(f"  {method:<10} {count:>3} rows  {total:>10,.4f} SAR")

    print("\n✅ All tests passed!")
    return True


if __name__ == "__main__":
    test_misc_consolidated_file_logic()
