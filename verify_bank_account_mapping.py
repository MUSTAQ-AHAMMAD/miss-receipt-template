#!/usr/bin/env python3
"""
================================================================================
BANK ACCOUNT MAPPING VERIFICATION TOOL
================================================================================
This script analyzes the Receipt_Methods.csv file and verifies bank account
mapping accuracy for both standard and MISS receipts.

It checks for:
1. Substring conflicts in store names
2. Duplicate mappings
3. Missing mappings for known stores
4. Ambiguous bank account assignments
================================================================================
"""

import csv
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")


def print_section(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BLUE}{'-'*80}{Colors.RESET}")


def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_info(text):
    print(f"  {text}")


def normalize_store(store: str) -> str:
    """Normalize store name similar to the actual implementation"""
    return store.upper().strip().replace(" ", "").replace("-", "").replace("_", "")


def extract_store_from_account_name(account_name: str) -> str:
    """
    Extract store identifier from bank account name.
    Examples:
        "AL Jazeerah Bank ZAHRAN" → "ZAHRAN"
        "AL Jazeerah Bank AL DAHRAN MALL" → "ALDAHRANMALL"
    """
    parts = account_name.upper().strip().split()
    # Skip common bank name parts
    skip_words = {'AL', 'JAZEERAH', 'BANK', 'ACCOUNT', 'ACC#', 'ACC'}
    store_parts = [p for p in parts if p not in skip_words and not p.startswith('#')]
    return ''.join(store_parts)


def load_receipt_methods(file_path: str) -> List[Dict]:
    """Load and parse Receipt_Methods.csv"""
    records = []
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({
                'org_id': row.get('ORGANIZATION_ID', ''),
                'org_name': row.get('ORG_NAME', ''),
                'method': row.get('RECEIPT_METHOD_NAME', '').strip(),
                'account_name': row.get('BANK_ACCOUNT_NAME', '').strip(),
                'account_number': row.get('BANK_ACCOUNT_NUMBER', '').strip(),
            })
    return records


def load_store_names(file_path: str) -> Set[str]:
    """Load store names from RCPT_Mapping_DATA.csv"""
    stores = set()
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            store = row.get('SUBINVENTORY', '').strip()
            if store:
                stores.add(store)
    return stores


def analyze_substring_conflicts(records: List[Dict]) -> List[Tuple[str, str, str]]:
    """
    Detect potential substring matching conflicts.
    Returns list of (store1, store2, account_name) tuples where store1 is substring of store2
    """
    conflicts = []

    # Extract all unique store identifiers from account names
    store_identifiers = set()
    for record in records:
        store_id = extract_store_from_account_name(record['account_name'])
        if store_id:
            store_identifiers.add(store_id)

    # Check for substring relationships
    store_list = sorted(store_identifiers)
    for i, store1 in enumerate(store_list):
        for store2 in store_list[i+1:]:
            if store1 in store2:
                # Find accounts that could be confused
                for record in records:
                    account_store = extract_store_from_account_name(record['account_name'])
                    if account_store == store2:
                        conflicts.append((store1, store2, record['account_name']))

    return conflicts


def analyze_duplicate_mappings(records: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Find duplicate mappings for the same method + store combination.
    Returns dict of (method, store) -> list of account records
    """
    mappings = defaultdict(list)

    for record in records:
        method = record['method']
        store = extract_store_from_account_name(record['account_name'])
        if method and store:
            key = f"{method}|{store}"
            mappings[key].append(record)

    # Filter to only duplicates
    duplicates = {k: v for k, v in mappings.items() if len(v) > 1}
    return duplicates


def analyze_method_coverage(records: List[Dict]) -> Dict[str, Set[str]]:
    """
    Analyze which payment methods have bank accounts defined.
    Returns dict of method -> set of stores with accounts
    """
    coverage = defaultdict(set)

    for record in records:
        method = record['method']
        store = extract_store_from_account_name(record['account_name'])
        if method and store:
            coverage[method].add(store)

    return coverage


def simulate_get_bank_account(records: List[Dict], store_name: str, method: str) -> Tuple[str, str, List[str]]:
    """
    Simulate the actual get_bank_account() logic to see what gets matched.
    Returns (account_name, account_number, list of all matches)
    """
    store_upper = normalize_store(store_name)
    matches = []

    for record in records:
        if record['method'] == method:
            account_upper = record['account_name'].upper()
            # This is the actual logic used in the code
            if store_upper in account_upper:
                matches.append(record)

    if matches:
        # Return first match (this is what the code does)
        first = matches[0]
        return (first['account_name'], first['account_number'], matches)
    else:
        return ("NOT FOUND", "", [])


def main():
    print_header("BANK ACCOUNT MAPPING VERIFICATION TOOL")

    # Check if files exist
    receipt_methods_file = Path("Receipt_Methods.csv")
    mapping_data_file = Path("RCPT_Mapping_DATA.csv")

    if not receipt_methods_file.exists():
        print_error(f"Receipt_Methods.csv not found in current directory")
        return 1

    if not mapping_data_file.exists():
        print_warning(f"RCPT_Mapping_DATA.csv not found - skipping store validation")
        known_stores = set()
    else:
        print_info(f"Loading store names from RCPT_Mapping_DATA.csv...")
        known_stores = load_store_names(str(mapping_data_file))
        print_success(f"Loaded {len(known_stores)} store names")

    # Load receipt methods
    print_info(f"Loading bank account mappings from Receipt_Methods.csv...")
    records = load_receipt_methods(str(receipt_methods_file))
    print_success(f"Loaded {len(records)} bank account records")

    # Extract unique values
    methods = sorted(set(r['method'] for r in records if r['method']))
    stores_in_accounts = set()
    for r in records:
        store = extract_store_from_account_name(r['account_name'])
        if store:
            stores_in_accounts.add(store)

    print_info(f"  Payment methods: {len(methods)}")
    print_info(f"  Unique stores: {len(stores_in_accounts)}")

    # ========================================================================
    # TEST 1: Check for substring conflicts
    # ========================================================================
    print_section("TEST 1: Substring Matching Conflicts")

    conflicts = analyze_substring_conflicts(records)

    if conflicts:
        print_error(f"Found {len(conflicts)} potential substring conflicts!")
        print_info("\n  These store names could cause incorrect matching:\n")

        seen = set()
        for store1, store2, account_name in conflicts:
            key = (store1, store2)
            if key not in seen:
                print_warning(f"  '{store1}' is substring of '{store2}'")
                print_info(f"    → Searching for '{store1}' could match '{account_name}'")
                seen.add(key)

        print_info("\n  RECOMMENDATION: Review these conflicts and consider using exact matching")
    else:
        print_success("No substring conflicts detected")

    # ========================================================================
    # TEST 2: Check for duplicate mappings
    # ========================================================================
    print_section("TEST 2: Duplicate Mappings")

    duplicates = analyze_duplicate_mappings(records)

    if duplicates:
        print_warning(f"Found {len(duplicates)} store/method combinations with multiple accounts")
        print_info("\n  Multiple bank accounts for same store + method:\n")

        for key, records_list in sorted(duplicates.items())[:10]:  # Show first 10
            method, store = key.split('|')
            print_warning(f"  {method} + {store}:")
            for rec in records_list:
                print_info(f"    → {rec['account_number']} ({rec['account_name']})")

        if len(duplicates) > 10:
            print_info(f"\n  ... and {len(duplicates) - 10} more")

        print_info("\n  IMPACT: First match will be used, which may not be deterministic")
    else:
        print_success("No duplicate mappings found")

    # ========================================================================
    # TEST 3: Method Coverage Analysis
    # ========================================================================
    print_section("TEST 3: Payment Method Coverage")

    coverage = analyze_method_coverage(records)

    print_info("Bank account mappings per payment method:\n")
    for method in sorted(coverage.keys()):
        store_count = len(coverage[method])
        print_success(f"  {method:<20} {store_count:>4} stores")

    # Check for card methods (important for MISS receipts)
    card_methods = ['Mada', 'Visa', 'MasterCard', 'AMEX', 'Amex']
    print_info("\n  Card payment methods (required for MISS receipts):")
    for method in card_methods:
        if method in coverage:
            print_success(f"    ✓ {method:<20} {len(coverage[method]):>4} stores")
        else:
            print_error(f"    ✗ {method:<20} NOT FOUND")

    # ========================================================================
    # TEST 4: Simulate Bank Account Lookup
    # ========================================================================
    print_section("TEST 4: Bank Account Lookup Simulation")

    # Test some sample lookups
    test_cases = []

    # Add test cases from known stores
    if known_stores:
        sample_stores = sorted(known_stores)[:5]  # First 5 stores
        for store in sample_stores:
            test_cases.append((store, "Cash"))
            test_cases.append((store, "Mada"))
    else:
        # Fallback test cases
        test_cases = [
            ("ZAHRAN", "Cash"),
            ("ZAHRAN", "Mada"),
            ("DAHRAN", "Cash"),
            ("AJAWEED", "Cash"),
            ("ARABMALL", "Mada"),
        ]

    print_info("Simulating bank account lookups for sample stores:\n")

    issues_found = False
    for store, method in test_cases[:10]:  # Test first 10
        account_name, account_number, all_matches = simulate_get_bank_account(records, store, method)

        if not all_matches:
            print_warning(f"  {store:<15} + {method:<10} → NO MATCH")
            issues_found = True
        elif len(all_matches) > 1:
            print_warning(f"  {store:<15} + {method:<10} → {len(all_matches)} matches (ambiguous!)")
            print_info(f"    Selected: {account_number}")
            for match in all_matches[1:]:
                print_info(f"    Ignored:  {match['account_number']}")
            issues_found = True
        else:
            print_success(f"  {store:<15} + {method:<10} → {account_number}")

    if not issues_found:
        print_success("\n  All test lookups produced single unambiguous matches")

    # ========================================================================
    # TEST 5: Missing Store Coverage
    # ========================================================================
    if known_stores:
        print_section("TEST 5: Missing Store Coverage")

        # Check which known stores don't have bank accounts
        missing_stores = []
        for store in known_stores:
            # Check if this store has at least one account for any method
            found = False
            for record in records:
                account_store = extract_store_from_account_name(record['account_name'])
                if normalize_store(store) == normalize_store(account_store):
                    found = True
                    break
            if not found:
                missing_stores.append(store)

        if missing_stores:
            print_warning(f"Found {len(missing_stores)} stores without bank account mappings")
            print_info("\n  Stores missing from Receipt_Methods.csv:")
            for store in sorted(missing_stores)[:20]:  # Show first 20
                print_warning(f"    {store}")
            if len(missing_stores) > 20:
                print_info(f"    ... and {len(missing_stores) - 20} more")
            print_info("\n  IMPACT: These stores will use fallback bank accounts")
        else:
            print_success("All known stores have bank account mappings")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print_section("SUMMARY & RECOMMENDATIONS")

    issues = []
    if conflicts:
        issues.append(f"❌ {len(conflicts)} substring conflicts detected")
    if duplicates:
        issues.append(f"⚠️  {len(duplicates)} duplicate mappings found")
    if known_stores and missing_stores:
        issues.append(f"⚠️  {len(missing_stores)} stores missing bank accounts")

    if issues:
        print_error("ISSUES FOUND:")
        for issue in issues:
            print_info(f"  {issue}")

        print_info("\n  RECOMMENDATIONS:")
        if conflicts:
            print_info("  1. Review substring conflicts and consider exact matching logic")
        if duplicates:
            print_info("  2. Review duplicate mappings - ensure intended account is listed first")
        if known_stores and missing_stores:
            print_info("  3. Add bank accounts for missing stores to Receipt_Methods.csv")

        print_info("\n  NEXT STEPS:")
        print_info("  - Review the detailed output above")
        print_info("  - Generate test receipts and verify bank account assignments")
        print_info("  - Check verification reports for actual bank account usage")

        return 1
    else:
        print_success("✓ No critical issues detected!")
        print_info("\n  Bank account mapping configuration looks good.")
        print_info("  However, still recommended to verify actual receipt generation:")
        print_info("  - Generate receipts with your data")
        print_info("  - Review verification report for bank account details")
        print_info("  - Spot-check generated receipt files")

        return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
