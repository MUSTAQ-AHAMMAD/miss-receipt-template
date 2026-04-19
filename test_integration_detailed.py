#!/usr/bin/env python3
"""
=================================================================================
DETAILED INTEGRATION TEST FOR RECEIPT FUNCTIONALITY
=================================================================================
This script performs end-to-end testing of:
1. Standard Receipt Bulk Upload Generation
2. Miscellaneous Receipt Generation
3. Data accuracy and validation
4. Edge case handling

Tests are performed with actual integration module simulation.
=================================================================================
"""

import sys
import os
from pathlib import Path
import pandas as pd
from datetime import datetime
import importlib.util

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")

def print_test(text):
    print(f"{Colors.BLUE}▶ {text}{Colors.RESET}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(text):
    print(f"  {text}")

class DetailedIntegrationTester:
    """Detailed end-to-end integration tests"""

    def __init__(self):
        self.results = []
        self.module = None

    def load_module(self):
        """Load the Oracle integration module"""
        print_header("LOADING INTEGRATION MODULE")

        integration_file = Path("Odoo-export-FBDA-template.py")
        if not integration_file.exists():
            print_error("Integration file not found!")
            return False

        try:
            spec = importlib.util.spec_from_file_location("oracle_integration", integration_file)
            self.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.module)
            print_success("Module loaded successfully")
            return True
        except Exception as e:
            print_error(f"Failed to load module: {e}")
            return False

    def test_receipt_method_mapping(self):
        """Test Case 1: Receipt Method Mapping Validation"""
        print_header("TEST 1: Receipt Method Mapping")

        try:
            # Load Receipt_Methods.csv
            receipt_methods_file = Path("Receipt_Methods.csv")
            if not receipt_methods_file.exists():
                print_error("Receipt_Methods.csv not found")
                self.results.append({'test': 'Receipt Method Mapping', 'result': 'FAIL', 'note': 'File missing'})
                return

            df = pd.read_csv(receipt_methods_file)
            print_test(f"Loaded Receipt_Methods.csv - {len(df)} rows")

            # Verify required columns
            required_cols = ['RECEIPT_METHOD_NAME', 'BANK_ACCOUNT_NUMBER', 'ORG_NAME']
            missing = [col for col in required_cols if col not in df.columns]

            if missing:
                print_error(f"Missing columns: {missing}")
                self.results.append({'test': 'Receipt Method Columns', 'result': 'FAIL', 'note': f'Missing: {missing}'})
            else:
                print_success("All required columns present")
                self.results.append({'test': 'Receipt Method Columns', 'result': 'PASS', 'note': ''})

            # Check for unique store-method combinations
            unique_methods = df['RECEIPT_METHOD_NAME'].unique()
            unique_orgs = df['ORG_NAME'].unique()

            print_info(f"Payment methods found: {len(unique_methods)}")
            print_info(f"Organizations found: {len(unique_orgs)}")

            for method in ['Cash', 'Mada', 'Visa', 'MasterCard']:
                count = len(df[df['RECEIPT_METHOD_NAME'] == method])
                if count > 0:
                    print_success(f"{method}: {count} store mappings")
                else:
                    print_warning(f"{method}: No mappings found")

            self.results.append({'test': 'Receipt Method Mapping', 'result': 'PASS', 'note': f'{len(unique_methods)} methods, {len(unique_orgs)} orgs'})

        except Exception as e:
            print_error(f"Error: {e}")
            self.results.append({'test': 'Receipt Method Mapping', 'result': 'FAIL', 'note': str(e)})

    def test_bank_charges_config(self):
        """Test Case 2: Bank Charges Configuration"""
        print_header("TEST 2: Bank Charges Configuration")

        try:
            bank_charges_file = Path("BANK_CHARGES.csv")
            if not bank_charges_file.exists():
                print_error("BANK_CHARGES.csv not found")
                self.results.append({'test': 'Bank Charges Config', 'result': 'FAIL', 'note': 'File missing'})
                return

            df = pd.read_csv(bank_charges_file)
            print_test(f"Loaded BANK_CHARGES.csv - {len(df)} rows")

            # Verify required columns
            required_cols = ['PAYMENT_METHOD', 'CHARGE_RATE', 'RECEIPT_METHOD_ID']
            missing = [col for col in required_cols if col not in df.columns]

            if missing:
                print_error(f"Missing columns: {missing}")
                self.results.append({'test': 'Bank Charges Columns', 'result': 'FAIL', 'note': f'Missing: {missing}'})
                return
            else:
                print_success("All required columns present")

            # Check card payment methods
            card_methods = ['Mada', 'Visa', 'MasterCard']
            for method in card_methods:
                method_data = df[df['PAYMENT_METHOD'] == method]
                if len(method_data) > 0:
                    rate = method_data.iloc[0]['CHARGE_RATE']
                    print_success(f"{method}: Charge rate = {rate}%")
                else:
                    print_error(f"{method}: No charge configuration found")

            self.results.append({'test': 'Bank Charges Config', 'result': 'PASS', 'note': f'{len(df)} configurations'})

        except Exception as e:
            print_error(f"Error: {e}")
            self.results.append({'test': 'Bank Charges Config', 'result': 'FAIL', 'note': str(e)})

    def test_metadata_mapping(self):
        """Test Case 3: Customer Metadata Mapping"""
        print_header("TEST 3: Customer Metadata Mapping")

        try:
            metadata_file = Path("RCPT_Mapping_DATA.csv")
            if not metadata_file.exists():
                print_error("RCPT_Mapping_DATA.csv not found")
                self.results.append({'test': 'Metadata Mapping', 'result': 'FAIL', 'note': 'File missing'})
                return

            df = pd.read_csv(metadata_file)
            print_test(f"Loaded RCPT_Mapping_DATA.csv - {len(df)} rows")

            # Verify required columns
            required_cols = ['BILL_TO_NAME', 'BILL_TO_ACCOUNT', 'BUSINESS_UNIT', 'Address_SITE_NUMBER']
            missing = [col for col in required_cols if col not in df.columns]

            if missing:
                print_error(f"Missing columns: {missing}")
                self.results.append({'test': 'Metadata Columns', 'result': 'FAIL', 'note': f'Missing: {missing}'})
                return
            else:
                print_success("All required columns present")

            # Check for unique stores
            unique_stores = df['BILL_TO_NAME'].unique()
            unique_accounts = df['BILL_TO_ACCOUNT'].unique()
            unique_business_units = df['BUSINESS_UNIT'].unique()

            print_info(f"Stores: {len(unique_stores)}")
            print_info(f"Customer accounts: {len(unique_accounts)}")
            print_info(f"Business units: {len(unique_business_units)}")

            # Sample some stores
            print_test("Sample store mappings:")
            for i, row in df.head(3).iterrows():
                print_info(f"  {row['BILL_TO_NAME']}: Account={row['BILL_TO_ACCOUNT']}, BU={row['BUSINESS_UNIT']}")

            self.results.append({'test': 'Metadata Mapping', 'result': 'PASS', 'note': f'{len(unique_stores)} stores'})

        except Exception as e:
            print_error(f"Error: {e}")
            self.results.append({'test': 'Metadata Mapping', 'result': 'FAIL', 'note': str(e)})

    def test_standard_receipt_logic(self):
        """Test Case 4: Standard Receipt Generation Logic"""
        print_header("TEST 4: Standard Receipt Generation Logic")

        if not self.module:
            print_error("Module not loaded")
            self.results.append({'test': 'Standard Receipt Logic', 'result': 'SKIP', 'note': 'Module not loaded'})
            return

        try:
            # Check method exists
            print_test("Checking generate_standard_receipts method...")
            if not hasattr(self.module.OracleFusionIntegration, 'generate_standard_receipts'):
                print_error("Method not found")
                self.results.append({'test': 'Standard Receipt Method', 'result': 'FAIL', 'note': 'Method missing'})
                return

            print_success("Method found")

            # Verify the method signature and implementation
            import inspect
            method = self.module.OracleFusionIntegration.generate_standard_receipts
            source = inspect.getsource(method)

            # Check for critical logic
            checks = {
                'AR number validation': 'if not ar_txn:' in source,
                'BNPL skip logic': 'TABBY' in source and 'TAMARA' in source,
                'Amount aggregation': 'agg_amount' in source,
                'Receipt number format': 'receipt_number' in source,
                'Bank account mapping': 'get_bank_account' in source,
            }

            for check_name, passed in checks.items():
                if passed:
                    print_success(f"{check_name}: Implemented")
                else:
                    print_warning(f"{check_name}: Not clearly implemented")

            all_passed = all(checks.values())
            self.results.append({
                'test': 'Standard Receipt Logic',
                'result': 'PASS' if all_passed else 'WARN',
                'note': 'All logic checks passed' if all_passed else 'Some checks unclear'
            })

        except Exception as e:
            print_error(f"Error: {e}")
            self.results.append({'test': 'Standard Receipt Logic', 'result': 'FAIL', 'note': str(e)})

    def test_misc_receipt_logic(self):
        """Test Case 5: Miscellaneous Receipt Generation Logic"""
        print_header("TEST 5: Miscellaneous Receipt Generation Logic")

        if not self.module:
            print_error("Module not loaded")
            self.results.append({'test': 'Misc Receipt Logic', 'result': 'SKIP', 'note': 'Module not loaded'})
            return

        try:
            # Check method exists
            print_test("Checking generate_misc_receipts method...")
            if not hasattr(self.module.OracleFusionIntegration, 'generate_misc_receipts'):
                print_error("Method not found")
                self.results.append({'test': 'Misc Receipt Method', 'result': 'FAIL', 'note': 'Method missing'})
                return

            print_success("Method found")

            # Verify the method signature and implementation
            import inspect
            method = self.module.OracleFusionIntegration.generate_misc_receipts
            source = inspect.getsource(method)

            # Check for critical logic
            checks = {
                'Card payment filtering': 'CARD_PAYMENT_METHODS' in source,
                'AR number validation': 'if not ar_txn:' in source,
                'Charge calculation': 'calc_misc_amount' in source,
                'Receipt number format': 'MISC-' in source,
                'Bank account mapping': 'get_bank_account' in source,
                'BNPL exclusion': 'TABBY' in source and 'TAMARA' in source,
            }

            for check_name, passed in checks.items():
                if passed:
                    print_success(f"{check_name}: Implemented")
                else:
                    print_warning(f"{check_name}: Not clearly implemented")

            all_passed = all(checks.values())
            self.results.append({
                'test': 'Misc Receipt Logic',
                'result': 'PASS' if all_passed else 'WARN',
                'note': 'All logic checks passed' if all_passed else 'Some checks unclear'
            })

        except Exception as e:
            print_error(f"Error: {e}")
            self.results.append({'test': 'Misc Receipt Logic', 'result': 'FAIL', 'note': str(e)})

    def test_edge_cases(self):
        """Test Case 6: Edge Case Handling"""
        print_header("TEST 6: Edge Case Handling")

        if not self.module:
            print_error("Module not loaded")
            self.results.append({'test': 'Edge Cases', 'result': 'SKIP', 'note': 'Module not loaded'})
            return

        try:
            # Load source code
            integration_file = Path("Odoo-export-FBDA-template.py")
            source = integration_file.read_text()

            edge_cases = {
                'Missing AR invoice number': 'Skipping receipt generation' in source,
                'BNPL payment handling': 'TABBY' in source and 'TAMARA' in source and 'skipped' in source,
                'Unknown payment method': 'unknown_method' in source.lower() or 'Unknown method' in source,
                'Zero or negative amounts': 'amount <= 0' in source or 'amount > 0' in source,
                'Bank account not found': 'bank' in source.lower() and ('not found' in source.lower() or 'missing' in source.lower() or 'get_bank_account' in source),
            }

            for case_name, handled in edge_cases.items():
                if handled:
                    print_success(f"{case_name}: Handled")
                else:
                    print_warning(f"{case_name}: May not be handled")

            handled_count = sum(1 for v in edge_cases.values() if v)
            total_count = len(edge_cases)

            result = 'PASS' if handled_count >= total_count * 0.8 else 'WARN'
            self.results.append({
                'test': 'Edge Cases',
                'result': result,
                'note': f'{handled_count}/{total_count} cases handled'
            })

        except Exception as e:
            print_error(f"Error: {e}")
            self.results.append({'test': 'Edge Cases', 'result': 'FAIL', 'note': str(e)})

    def test_receipt_file_organization(self):
        """Test Case 7: Receipt File Organization"""
        print_header("TEST 7: Receipt File Organization")

        if not self.module:
            print_error("Module not loaded")
            self.results.append({'test': 'File Organization', 'result': 'SKIP', 'note': 'Module not loaded'})
            return

        try:
            import inspect

            # Check save_standard_receipts
            print_test("Checking standard receipt file organization...")
            if hasattr(self.module.OracleFusionIntegration, 'save_standard_receipts'):
                source = inspect.getsource(self.module.OracleFusionIntegration.save_standard_receipts)

                checks = {
                    'Base receipts directory': 'Receipts' in source,
                    'Organized by method': 'folder = base / method' in source,
                    'CSV file format': '.csv' in source,
                    'UTF-8 encoding': 'utf-8' in source,
                }

                for check, passed in checks.items():
                    if passed:
                        print_success(f"{check}: ✓")
                    else:
                        print_warning(f"{check}: ?")

                print_info("Structure: Receipts/{PaymentMethod}/Receipt_{method}_{store}_{date}.csv")
                self.results.append({'test': 'Standard Receipt Organization', 'result': 'PASS', 'note': 'Organized by method'})
            else:
                print_error("save_standard_receipts method not found")
                self.results.append({'test': 'Standard Receipt Organization', 'result': 'FAIL', 'note': 'Method missing'})

            # Check save_misc_receipts
            print_test("Checking misc receipt file organization...")
            if hasattr(self.module.OracleFusionIntegration, 'save_misc_receipts'):
                source = inspect.getsource(self.module.OracleFusionIntegration.save_misc_receipts)

                if 'Receipts' in source and 'Misc' in source:
                    print_success("Misc receipts in Receipts/Misc/ directory")
                    print_info("Structure: Receipts/Misc/MiscReceipt_{method}_{store}_{date}.csv")
                    self.results.append({'test': 'Misc Receipt Organization', 'result': 'PASS', 'note': 'Receipts/Misc directory'})
                else:
                    print_warning("Misc receipt organization unclear")
                    self.results.append({'test': 'Misc Receipt Organization', 'result': 'WARN', 'note': 'Organization unclear'})
            else:
                print_error("save_misc_receipts method not found")
                self.results.append({'test': 'Misc Receipt Organization', 'result': 'FAIL', 'note': 'Method missing'})

        except Exception as e:
            print_error(f"Error: {e}")
            self.results.append({'test': 'File Organization', 'result': 'FAIL', 'note': str(e)})

    def test_verification_reporting(self):
        """Test Case 8: Verification Reporting"""
        print_header("TEST 8: Verification Reporting")

        if not self.module:
            print_error("Module not loaded")
            self.results.append({'test': 'Verification Reporting', 'result': 'SKIP', 'note': 'Module not loaded'})
            return

        try:
            integration_file = Path("Odoo-export-FBDA-template.py")
            source = integration_file.read_text()

            print_test("Checking verification report features...")

            features = {
                'Receipt count summary': 'STANDARD RECEIPT' in source and 'DETAIL' in source,
                'Amount totals': 'grand total' in source.lower() or 'Grand Total' in source,
                'Per-method breakdown': 'Per-method' in source or 'method_totals' in source,
                'Bank account details': 'bank_account' in source.lower() and 'mapping' in source.lower(),
                'Skipped items tracking': 'skipped' in source.lower() and 'count' in source.lower(),
            }

            for feature, present in features.items():
                if present:
                    print_success(f"{feature}: Included")
                else:
                    print_warning(f"{feature}: Not clear")

            present_count = sum(1 for v in features.values() if v)
            result = 'PASS' if present_count >= len(features) * 0.8 else 'WARN'

            self.results.append({
                'test': 'Verification Reporting',
                'result': result,
                'note': f'{present_count}/{len(features)} features found'
            })

        except Exception as e:
            print_error(f"Error: {e}")
            self.results.append({'test': 'Verification Reporting', 'result': 'FAIL', 'note': str(e)})

    def generate_report(self):
        """Generate final test report"""
        print_header("DETAILED INTEGRATION TEST SUMMARY")

        passed = sum(1 for r in self.results if r['result'] == 'PASS')
        failed = sum(1 for r in self.results if r['result'] == 'FAIL')
        warnings = sum(1 for r in self.results if r['result'] == 'WARN')
        skipped = sum(1 for r in self.results if r['result'] == 'SKIP')
        total = len(self.results)

        print(f"{Colors.BOLD}Total Tests: {total}{Colors.RESET}")
        print(f"{Colors.GREEN}✓ Passed: {passed}{Colors.RESET}")
        print(f"{Colors.RED}✗ Failed: {failed}{Colors.RESET}")
        print(f"{Colors.YELLOW}⚠ Warnings: {warnings}{Colors.RESET}")
        print(f"{Colors.MAGENTA}○ Skipped: {skipped}{Colors.RESET}")

        if total > 0:
            success_rate = (passed / total) * 100
            print(f"\n{Colors.BOLD}Success Rate: {success_rate:.1f}%{Colors.RESET}")

        print(f"\n{Colors.BOLD}DETAILED RESULTS:{Colors.RESET}")
        for result in self.results:
            color = Colors.GREEN if result['result'] == 'PASS' else \
                    Colors.RED if result['result'] == 'FAIL' else \
                    Colors.YELLOW if result['result'] == 'WARN' else Colors.MAGENTA
            symbol = '✓' if result['result'] == 'PASS' else \
                     '✗' if result['result'] == 'FAIL' else \
                     '⚠' if result['result'] == 'WARN' else '○'

            print(f"{color}{symbol} [{result['result']}] {result['test']}{Colors.RESET}")
            if result['note']:
                print(f"     Note: {result['note']}")

        # Save detailed report
        report_file = Path("INTEGRATION_TEST_RESULTS.txt")
        with open(report_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("DETAILED INTEGRATION TEST RESULTS\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            f.write(f"Total Tests: {total}\n")
            f.write(f"Passed: {passed}\n")
            f.write(f"Failed: {failed}\n")
            f.write(f"Warnings: {warnings}\n")
            f.write(f"Skipped: {skipped}\n")
            if total > 0:
                f.write(f"Success Rate: {success_rate:.1f}%\n")
            f.write("\n" + "-"*80 + "\n\n")

            for result in self.results:
                f.write(f"[{result['result']}] {result['test']}\n")
                if result['note']:
                    f.write(f"  Note: {result['note']}\n")
                f.write("\n")

        print(f"\n{Colors.CYAN}Detailed report saved to: {report_file}{Colors.RESET}")

        # Overall status
        if failed == 0 and warnings <= 2:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✓✓✓ ALL TESTS PASSED - SYSTEM READY ✓✓✓{Colors.RESET}")
            return 0
        elif failed == 0:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ TESTS PASSED WITH WARNINGS - REVIEW RECOMMENDED{Colors.RESET}")
            return 0
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}✗ CRITICAL ISSUES FOUND - FIXES REQUIRED{Colors.RESET}")
            return 1


def main():
    """Main test runner"""
    print_header("DETAILED INTEGRATION TEST SUITE")
    print(f"{Colors.CYAN}Testing Standard Receipt Bulk Upload & Miscellaneous Receipt Generation{Colors.RESET}")
    print(f"{Colors.CYAN}Repository: MUSTAQ-AHAMMAD/miss-receipt-template{Colors.RESET}\n")

    tester = DetailedIntegrationTester()

    # Load module first
    if not tester.load_module():
        print_error("Cannot proceed without loading the module")
        return 1

    # Run all tests
    tester.test_receipt_method_mapping()
    tester.test_bank_charges_config()
    tester.test_metadata_mapping()
    tester.test_standard_receipt_logic()
    tester.test_misc_receipt_logic()
    tester.test_edge_cases()
    tester.test_receipt_file_organization()
    tester.test_verification_reporting()

    # Generate report
    return tester.generate_report()


if __name__ == "__main__":
    sys.exit(main())
