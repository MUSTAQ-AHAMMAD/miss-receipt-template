#!/usr/bin/env python3
"""
Demonstration script showing the alphanumeric transaction and receipt number generation.
This script demonstrates how the new alphanumeric format works.
"""

def to_alphanumeric(num: int, length: int = 7) -> str:
    """Convert a number to alphanumeric format using base-36 (0-9, A-Z)."""
    if num == 0:
        return '0' * length

    digits = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    result = ''
    while num > 0:
        result = digits[num % 36] + result
        num //= 36

    return result.zfill(length)

def from_alphanumeric(alphanumeric: str) -> int:
    """Convert an alphanumeric string back to a number."""
    digits = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    result = 0
    for char in alphanumeric.upper():
        result = result * 36 + digits.index(char)
    return result

def main():
    print("=" * 70)
    print("ALPHANUMERIC TRANSACTION & RECEIPT NUMBER DEMONSTRATION")
    print("=" * 70)

    # Demonstrate transaction number generation
    print("\n1. TRANSACTION NUMBER EXAMPLES")
    print("-" * 70)
    print(f"{'Sequence':<12} {'Transaction Number':<25} {'Receipt Number':<30}")
    print("-" * 70)

    test_sequences = [1, 2, 5, 9, 10, 11, 35, 36, 37, 100, 500, 1000, 5000, 10000]

    for seq in test_sequences:
        alphanumeric = to_alphanumeric(seq, 7)
        txn_num = f"BLKU-{alphanumeric}"
        receipt_num = f"CASH-{txn_num}"
        print(f"{seq:<12} {txn_num:<25} {receipt_num:<30}")

    # Show the pattern where letters start appearing
    print("\n2. TRANSITION FROM NUMERIC TO ALPHANUMERIC")
    print("-" * 70)
    print("Notice how at sequence 10, the letter 'A' appears:")
    for i in range(8, 13):
        alphanumeric = to_alphanumeric(i, 7)
        print(f"  Sequence {i:2d}: BLKU-{alphanumeric}")

    # Demonstrate different receipt types
    print("\n3. DIFFERENT RECEIPT TYPES")
    print("-" * 70)
    txn = "BLKU-000000A"  # Sequence 10
    print(f"Transaction Number: {txn}")
    print(f"  Standard Receipt (CASH):    CASH-{txn}")
    print(f"  Standard Receipt (VISA):    VISA-{txn}")
    print(f"  Standard Receipt (MADA):    MADA-{txn}")
    print(f"  Misc Receipt (BANK):        MISC-BANK-{txn}")
    print(f"  Misc Receipt (ADJUST):      MISC-ADJUST-{txn}")

    # Show capacity improvement
    print("\n4. CAPACITY COMPARISON")
    print("-" * 70)
    print(f"Old Format (7 numeric digits):     Max = 9,999,999 transactions")
    print(f"New Format (7 alphanumeric chars): Max = 78,364,164,096 transactions")
    print(f"Improvement: ~7,836x larger capacity!")

    # Round-trip verification
    print("\n5. ROUND-TRIP CONVERSION VERIFICATION")
    print("-" * 70)
    print(f"{'Original':<12} {'Alphanumeric':<15} {'Converted Back':<15} {'Status'}")
    print("-" * 70)
    test_nums = [1, 10, 100, 1000, 10000, 99999]
    for num in test_nums:
        alphanumeric = to_alphanumeric(num, 7)
        back = from_alphanumeric(alphanumeric)
        status = "✓ PASS" if num == back else "✗ FAIL"
        print(f"{num:<12} {alphanumeric:<15} {back:<15} {status}")

    print("\n" + "=" * 70)
    print("✓ DEMONSTRATION COMPLETE")
    print("=" * 70)
    print("\nSummary:")
    print("  - Transaction numbers now use alphanumeric format (0-9, A-Z)")
    print("  - Receipt numbers automatically inherit the alphanumeric format")
    print("  - System maintains backward compatibility for tracking")
    print("  - All conversions are reversible and verified")

if __name__ == "__main__":
    main()
