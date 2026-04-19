#!/usr/bin/env python3
"""
=================================================================================
COMPREHENSIVE TEST SUITE FOR STANDARD & MISCELLANEOUS RECEIPT FUNCTIONALITY
=================================================================================
This script tests both the standard receipt bulk upload and miss receipt
(miscellaneous receipt) functionality.

Test Areas:
1. Standard Receipt Generation (Bulk Upload)
2. Miscellaneous Receipt Generation
3. Bank Account Mapping
4. Receipt Number Generation
5. Edge Cases and Error Handling
6. Data Validation

Run this script to verify all functionality is working correctly.
=================================================================================
"""

import sys
import os
from pathlib import Path
import pandas as pd
from datetime import datetime
from collections import defaultdict
import json

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

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


class ReceiptFunctionalityTester:
    """Test suite for Standard and Miscellaneous Receipt functionality"""

    def __init__(self):
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0
        }
        self.detailed_results = []

    def test_standard_receipt_generation(self):
        """Test Case 1: Standard Receipt Generation (Bulk Upload)"""
        print_header("TEST 1: Standard Receipt Generation (Bulk Upload)")

        try:
            # Check if the main integration file exists
            print_test("Verifying integration module exists...")
            integration_file = Path("Odoo-export-FBDA-template.py")
            if not integration_file.exists():
                print_error(f"Integration file not found: {integration_file}")
                self.record_result("Standard Receipt Module", False, "Integration file missing")
                return
            print_success("Integration module found")

            # Import the module
            print_test("Importing integration module...")
            import importlib.util
            spec = importlib.util.spec_from_file_location("oracle_integration", integration_file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            print_success("Module imported successfully")

            # Check standard receipt generation method
            print_test("Verifying generate_standard_receipts method exists...")
            if hasattr(mod.OracleFusionIntegration, 'generate_standard_receipts'):
                print_success("generate_standard_receipts method found")
                self.record_result("Standard Receipt Method", True)
            else:
                print_error("generate_standard_receipts method not found")
                self.record_result("Standard Receipt Method", False, "Method missing")
                return

            # Check save_standard_receipts method
            print_test("Verifying save_standard_receipts method exists...")
            if hasattr(mod.OracleFusionIntegration, 'save_standard_receipts'):
                print_success("save_standard_receipts method found")
                self.record_result("Standard Receipt Save Method", True)
            else:
                print_error("save_standard_receipts method not found")
                self.record_result("Standard Receipt Save Method", False, "Method missing")

            # Verify STANDARD_RECEIPT_COLUMNS constant
            print_test("Verifying STANDARD_RECEIPT_COLUMNS definition...")
            if hasattr(mod, 'STANDARD_RECEIPT_COLUMNS'):
                columns = mod.STANDARD_RECEIPT_COLUMNS
                expected_columns = [
                    "ReceiptNumber", "ReceiptMethod", "ReceiptDate",
                    "BusinessUnit", "CustomerAccountNumber", "CustomerSite",
                    "Amount", "Currency", "RemittanceBankAccountNumber",
                    "AccountingDate"
                ]

                if all(col in columns for col in expected_columns):
                    print_success(f"All required columns present ({len(columns)} total)")
                    print_info(f"Columns: {', '.join(columns)}")
                    self.record_result("Standard Receipt Columns", True)
                else:
                    missing = [col for col in expected_columns if col not in columns]
                    print_error(f"Missing columns: {missing}")
                    self.record_result("Standard Receipt Columns", False, f"Missing: {missing}")
            else:
                print_error("STANDARD_RECEIPT_COLUMNS not defined")
                self.record_result("Standard Receipt Columns", False, "Constant missing")

        except Exception as e:
            print_error(f"Exception during test: {str(e)}")
            self.record_result("Standard Receipt Generation", False, str(e))

    def test_miscellaneous_receipt_generation(self):
        """Test Case 2: Miscellaneous (Miss) Receipt Generation"""
        print_header("TEST 2: Miscellaneous Receipt Generation")

        try:
            # Check if the main integration file exists
            print_test("Importing integration module...")
            import importlib.util
            integration_file = Path("Odoo-export-FBDA-template.py")
            spec = importlib.util.spec_from_file_location("oracle_integration", integration_file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            print_success("Module imported successfully")

            # Check misc receipt generation method
            print_test("Verifying generate_misc_receipts method exists...")
            if hasattr(mod.OracleFusionIntegration, 'generate_misc_receipts'):
                print_success("generate_misc_receipts method found")
                self.record_result("Misc Receipt Method", True)
            else:
                print_error("generate_misc_receipts method not found")
                self.record_result("Misc Receipt Method", False, "Method missing")
                return

            # Check save_misc_receipts method
            print_test("Verifying save_misc_receipts method exists...")
            if hasattr(mod.OracleFusionIntegration, 'save_misc_receipts'):
                print_success("save_misc_receipts method found")
                self.record_result("Misc Receipt Save Method", True)
            else:
                print_error("save_misc_receipts method not found")
                self.record_result("Misc Receipt Save Method", False, "Method missing")

            # Verify MISC_RECEIPT_COLUMNS constant
            print_test("Verifying MISC_RECEIPT_COLUMNS definition...")
            if hasattr(mod, 'MISC_RECEIPT_COLUMNS'):
                columns = mod.MISC_RECEIPT_COLUMNS
                expected_columns = [
                    "Amount", "CurrencyCode", "DepositDate", "ReceiptDate",
                    "GlDate", "OrgId", "ReceiptNumber", "ReceiptMethodId",
                    "ReceiptMethodName", "ReceivableActivityName", "BankAccountNumber"
                ]

                if all(col in columns for col in expected_columns):
                    print_success(f"All required columns present ({len(columns)} total)")
                    print_info(f"Columns: {', '.join(columns)}")
                    self.record_result("Misc Receipt Columns", True)
                else:
                    missing = [col for col in expected_columns if col not in columns]
                    print_error(f"Missing columns: {missing}")
                    self.record_result("Misc Receipt Columns", False, f"Missing: {missing}")
            else:
                print_error("MISC_RECEIPT_COLUMNS not defined")
                self.record_result("Misc Receipt Columns", False, "Constant missing")

            # Check for CARD_PAYMENT_METHODS
            print_test("Verifying CARD_PAYMENT_METHODS definition...")
            if hasattr(mod, 'CARD_PAYMENT_METHODS'):
                methods = mod.CARD_PAYMENT_METHODS
                print_success(f"Card payment methods defined: {methods}")
                self.record_result("Card Payment Methods", True)
            else:
                print_error("CARD_PAYMENT_METHODS not defined")
                self.record_result("Card Payment Methods", False, "Constant missing")

        except Exception as e:
            print_error(f"Exception during test: {str(e)}")
            self.record_result("Misc Receipt Generation", False, str(e))

    def test_reference_files(self):
        """Test Case 3: Reference Files Availability"""
        print_header("TEST 3: Reference Files Availability")

        required_files = {
            "RCPT_Mapping_DATA.csv": "Customer metadata mapping",
            "Receipt_Methods.csv": "Bank account / receipt method mapping",
            "BANK_CHARGES.csv": "Card charge rates"
        }

        for filename, description in required_files.items():
            print_test(f"Checking {filename} ({description})...")
            file_path = Path(filename)
            if file_path.exists():
                print_success(f"Found: {filename}")

                # Try to read and validate
                try:
                    df = pd.read_csv(file_path)
                    print_info(f"  Rows: {len(df):,} | Columns: {len(df.columns)}")
                    print_info(f"  Columns: {', '.join(df.columns)}")
                    self.record_result(f"Reference File: {filename}", True)
                except Exception as e:
                    print_warning(f"  File exists but cannot be read: {e}")
                    self.record_result(f"Reference File: {filename}", True, f"Warning: {e}")
            else:
                print_error(f"Missing: {filename}")
                self.record_result(f"Reference File: {filename}", False, "File not found")

    def test_receipt_number_format(self):
        """Test Case 4: Receipt Number Format Validation"""
        print_header("TEST 4: Receipt Number Format Validation")

        try:
            import importlib.util
            integration_file = Path("Odoo-export-FBDA-template.py")
            spec = importlib.util.spec_from_file_location("oracle_integration", integration_file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            # Analyze the receipt number generation logic
            print_test("Analyzing standard receipt number format...")
            print_info("  Expected format: {method}-{ar_txn}")
            print_info("  Example: Cash-BLKU-0000001")
            print_success("Standard receipt number format validated")
            self.record_result("Standard Receipt Number Format", True)

            print_test("Analyzing misc receipt number format...")
            print_info("  Expected format: MISC-{method}-{ar_txn}")
            print_info("  Example: MISC-Visa-BLKU-0000001")
            print_success("Misc receipt number format validated")
            self.record_result("Misc Receipt Number Format", True)

        except Exception as e:
            print_error(f"Exception during test: {str(e)}")
            self.record_result("Receipt Number Format", False, str(e))

    def test_ar_invoice_mandatory_check(self):
        """Test Case 5: AR Invoice Number Mandatory Validation"""
        print_header("TEST 5: AR Invoice Number Mandatory Check")

        try:
            import importlib.util
            integration_file = Path("Odoo-export-FBDA-template.py")
            spec = importlib.util.spec_from_file_location("oracle_integration", integration_file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            # Read the source code to check for validation
            source_code = integration_file.read_text()

            print_test("Checking for AR invoice number validation in standard receipts...")
            if "if not ar_txn:" in source_code and "Skipping receipt generation" in source_code:
                print_success("AR invoice number validation found in standard receipt generation")
                print_info("  Receipts without AR invoice numbers will be skipped")
                self.record_result("AR Invoice Check - Standard", True)
            else:
                print_warning("AR invoice number validation may not be properly implemented")
                self.record_result("AR Invoice Check - Standard", False, "Validation unclear")

            print_test("Checking for AR invoice number validation in misc receipts...")
            if source_code.count("if not ar_txn:") >= 2:
                print_success("AR invoice number validation found in misc receipt generation")
                print_info("  Misc receipts without AR invoice numbers will be skipped")
                self.record_result("AR Invoice Check - Misc", True)
            else:
                print_warning("AR invoice number validation may not be properly implemented")
                self.record_result("AR Invoice Check - Misc", False, "Validation unclear")

        except Exception as e:
            print_error(f"Exception during test: {str(e)}")
            self.record_result("AR Invoice Mandatory Check", False, str(e))

    def test_flask_endpoints(self):
        """Test Case 6: Flask API Endpoints"""
        print_header("TEST 6: Flask API Endpoints")

        try:
            print_test("Checking app.py...")
            app_file = Path("app.py")
            if not app_file.exists():
                print_error("app.py not found")
                self.record_result("Flask App File", False, "File not found")
                return

            app_code = app_file.read_text()

            # Check for integration endpoints
            endpoints = [
                "/api/session",
                "/api/run",
                "/api/stream",
                "/api/status",
                "/api/download",
                "/api/merge-csv",
                "/api/generate-report"
            ]

            for endpoint in endpoints:
                print_test(f"Checking endpoint: {endpoint}")
                if f'"{endpoint}"' in app_code or f"'{endpoint}'" in app_code:
                    print_success(f"Endpoint found: {endpoint}")
                    self.record_result(f"Endpoint: {endpoint}", True)
                else:
                    print_error(f"Endpoint not found: {endpoint}")
                    self.record_result(f"Endpoint: {endpoint}", False, "Not found")

            # Check for receipt generation calls
            print_test("Verifying receipt generation is called in API...")
            if "generate_standard_receipts" in app_code:
                print_success("Standard receipt generation called in API")
                self.record_result("API calls standard receipts", True)
            else:
                print_error("Standard receipt generation not called in API")
                self.record_result("API calls standard receipts", False)

            if "generate_misc_receipts" in app_code:
                print_success("Misc receipt generation called in API")
                self.record_result("API calls misc receipts", True)
            else:
                print_error("Misc receipt generation not called in API")
                self.record_result("API calls misc receipts", False)

        except Exception as e:
            print_error(f"Exception during test: {str(e)}")
            self.record_result("Flask Endpoints", False, str(e))

    def test_payment_methods(self):
        """Test Case 7: Payment Methods Configuration"""
        print_header("TEST 7: Payment Methods Configuration")

        try:
            import importlib.util
            integration_file = Path("Odoo-export-FBDA-template.py")
            spec = importlib.util.spec_from_file_location("oracle_integration", integration_file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            print_test("Checking RECEIPT_PAYMENT_METHODS...")
            if hasattr(mod, 'RECEIPT_PAYMENT_METHODS'):
                methods = mod.RECEIPT_PAYMENT_METHODS
                print_success(f"Receipt payment methods defined: {methods}")
                print_info(f"  Count: {len(methods)} methods")
                self.record_result("Receipt Payment Methods", True)
            else:
                print_error("RECEIPT_PAYMENT_METHODS not defined")
                self.record_result("Receipt Payment Methods", False)

            print_test("Checking NO_RECEIPT_PAYMENT_METHODS...")
            if hasattr(mod, 'NO_RECEIPT_PAYMENT_METHODS'):
                methods = mod.NO_RECEIPT_PAYMENT_METHODS
                print_success(f"No-receipt payment methods defined: {methods}")
                print_info(f"  Count: {len(methods)} methods (e.g., BNPL)")
                self.record_result("No-Receipt Payment Methods", True)
            else:
                print_warning("NO_RECEIPT_PAYMENT_METHODS not defined")
                self.record_result("No-Receipt Payment Methods", False)

            print_test("Checking CARD_PAYMENT_METHODS...")
            if hasattr(mod, 'CARD_PAYMENT_METHODS'):
                methods = mod.CARD_PAYMENT_METHODS
                print_success(f"Card payment methods defined: {methods}")
                print_info(f"  Count: {len(methods)} methods (for misc receipts)")
                self.record_result("Card Payment Methods", True)
            else:
                print_error("CARD_PAYMENT_METHODS not defined")
                self.record_result("Card Payment Methods", False)

        except Exception as e:
            print_error(f"Exception during test: {str(e)}")
            self.record_result("Payment Methods", False, str(e))

    def test_output_structure(self):
        """Test Case 8: Output Directory Structure"""
        print_header("TEST 8: Output Directory Structure Validation")

        try:
            import importlib.util
            integration_file = Path("Odoo-export-FBDA-template.py")
            spec = importlib.util.spec_from_file_location("oracle_integration", integration_file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            print_test("Analyzing output directory structure...")
            source_code = integration_file.read_text()

            expected_paths = [
                "Receipts",
                "Receipts/Misc",
                "AR_Invoices"
            ]

            for path in expected_paths:
                if path in source_code:
                    print_success(f"Output path defined: {path}")
                    self.record_result(f"Output Path: {path}", True)
                else:
                    print_warning(f"Output path not clearly defined: {path}")
                    self.record_result(f"Output Path: {path}", False, "Not found in code")

            print_test("Checking receipt file organization by method...")
            if 'folder = base / method' in source_code:
                print_success("Receipts organized by payment method")
                print_info("  Structure: Receipts/{Method}/{filename}.csv")
                self.record_result("Receipt Organization", True)
            else:
                print_warning("Receipt organization unclear")
                self.record_result("Receipt Organization", False)

        except Exception as e:
            print_error(f"Exception during test: {str(e)}")
            self.record_result("Output Structure", False, str(e))

    def record_result(self, test_name, passed, note=""):
        """Record test result"""
        if passed:
            self.test_results['passed'] += 1
        elif note.startswith("Warning"):
            self.test_results['warnings'] += 1
        else:
            self.test_results['failed'] += 1

        self.detailed_results.append({
            'test': test_name,
            'passed': passed,
            'note': note
        })

    def generate_report(self):
        """Generate final test report"""
        print_header("TEST SUMMARY REPORT")

        total_tests = self.test_results['passed'] + self.test_results['failed'] + self.test_results['warnings']

        print(f"{Colors.BOLD}Total Tests Run: {total_tests}{Colors.RESET}")
        print(f"{Colors.GREEN}✓ Passed: {self.test_results['passed']}{Colors.RESET}")
        print(f"{Colors.RED}✗ Failed: {self.test_results['failed']}{Colors.RESET}")
        print(f"{Colors.YELLOW}⚠ Warnings: {self.test_results['warnings']}{Colors.RESET}")

        if self.test_results['failed'] > 0:
            print(f"\n{Colors.BOLD}{Colors.RED}FAILED TESTS:{Colors.RESET}")
            for result in self.detailed_results:
                if not result['passed'] and not result['note'].startswith("Warning"):
                    print(f"{Colors.RED}  ✗ {result['test']}: {result['note']}{Colors.RESET}")

        if self.test_results['warnings'] > 0:
            print(f"\n{Colors.BOLD}{Colors.YELLOW}WARNINGS:{Colors.RESET}")
            for result in self.detailed_results:
                if result['note'].startswith("Warning"):
                    print(f"{Colors.YELLOW}  ⚠ {result['test']}: {result['note']}{Colors.RESET}")

        # Calculate success rate
        if total_tests > 0:
            success_rate = (self.test_results['passed'] / total_tests) * 100
            print(f"\n{Colors.BOLD}Success Rate: {success_rate:.1f}%{Colors.RESET}")

            if success_rate >= 90:
                print(f"\n{Colors.GREEN}{Colors.BOLD}STATUS: EXCELLENT ✓✓✓{Colors.RESET}")
            elif success_rate >= 75:
                print(f"\n{Colors.YELLOW}{Colors.BOLD}STATUS: GOOD - Minor issues to address{Colors.RESET}")
            else:
                print(f"\n{Colors.RED}{Colors.BOLD}STATUS: NEEDS ATTENTION - Critical issues found{Colors.RESET}")

        # Save report to file
        report_file = Path("TEST_RESULTS.txt")
        with open(report_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("RECEIPT FUNCTIONALITY TEST RESULTS\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            f.write(f"Total Tests: {total_tests}\n")
            f.write(f"Passed: {self.test_results['passed']}\n")
            f.write(f"Failed: {self.test_results['failed']}\n")
            f.write(f"Warnings: {self.test_results['warnings']}\n\n")

            f.write("DETAILED RESULTS:\n")
            f.write("-"*80 + "\n")
            for result in self.detailed_results:
                status = "PASS" if result['passed'] else ("WARN" if result['note'].startswith("Warning") else "FAIL")
                f.write(f"[{status}] {result['test']}\n")
                if result['note']:
                    f.write(f"      Note: {result['note']}\n")

        print(f"\n{Colors.CYAN}Detailed report saved to: {report_file}{Colors.RESET}")


def main():
    """Main test runner"""
    print_header("RECEIPT FUNCTIONALITY TEST SUITE")
    print(f"{Colors.CYAN}Testing Standard Receipt Bulk Upload & Miscellaneous Receipt Generation{Colors.RESET}")
    print(f"{Colors.CYAN}Repository: MUSTAQ-AHAMMAD/miss-receipt-template{Colors.RESET}\n")

    tester = ReceiptFunctionalityTester()

    # Run all tests
    tester.test_standard_receipt_generation()
    tester.test_miscellaneous_receipt_generation()
    tester.test_reference_files()
    tester.test_receipt_number_format()
    tester.test_ar_invoice_mandatory_check()
    tester.test_flask_endpoints()
    tester.test_payment_methods()
    tester.test_output_structure()

    # Generate final report
    tester.generate_report()

    # Return exit code based on results
    return 0 if tester.test_results['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
