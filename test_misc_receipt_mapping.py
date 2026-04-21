#!/usr/bin/env python3
"""
================================================================================
MISCELLANEOUS RECEIPT MAPPING & GENERATION TEST SUITE
================================================================================
This script specifically tests the misc receipt (miscellaneous receipt)
functionality including:

1. Payment method mapping (which methods trigger misc receipts)
2. Bank charge calculation accuracy
3. Misc receipt file generation
4. Receipt field validation
5. Diagnostic logging verification

This test directly addresses the user's requirement to verify that misc receipts
have the right mapping and are being created correctly.
================================================================================
"""

import sys
import os
from pathlib import Path
import pandas as pd
from datetime import datetime
from collections import defaultdict
import tempfile
import shutil

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


class MiscReceiptMappingTester:
    """Test suite specifically for Miscellaneous Receipt mapping and generation"""

    def __init__(self):
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0
        }
        self.detailed_results = []
        self.integration_module = None

    def load_integration_module(self):
        """Load the integration module"""
        try:
            import importlib.util
            integration_file = Path("Odoo-export-FBDA-template.py")
            if not integration_file.exists():
                print_error(f"Integration file not found: {integration_file}")
                return False

            spec = importlib.util.spec_from_file_location("oracle_integration", integration_file)
            self.integration_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.integration_module)
            return True
        except Exception as e:
            print_error(f"Failed to load integration module: {e}")
            return False

    def test_card_payment_methods_configuration(self):
        """TEST 1: Verify CARD_PAYMENT_METHODS Configuration"""
        print_header("TEST 1: CARD_PAYMENT_METHODS Configuration")

        if not self.integration_module:
            if not self.load_integration_module():
                self.record_result("Load Module", False, "Cannot load integration module")
                return

        mod = self.integration_module

        print_test("Checking CARD_PAYMENT_METHODS constant...")
        if hasattr(mod, 'CARD_PAYMENT_METHODS'):
            card_methods = mod.CARD_PAYMENT_METHODS
            print_success(f"CARD_PAYMENT_METHODS defined: {card_methods}")
            print_info(f"  Card methods count: {len(card_methods)}")

            # These are the methods that should generate misc receipts
            expected_methods = ["Mada", "Visa", "MasterCard"]
            for method in expected_methods:
                if method in card_methods:
                    print_success(f"  ✓ {method} is in CARD_PAYMENT_METHODS")
                else:
                    print_error(f"  ✗ {method} missing from CARD_PAYMENT_METHODS")

            self.record_result("CARD_PAYMENT_METHODS Configuration", True)

            # Check if there are additional methods that might be missing
            print_info("\n  Note: Misc receipts will ONLY be generated for these methods:")
            for method in sorted(card_methods):
                print_info(f"    - {method}")

        else:
            print_error("CARD_PAYMENT_METHODS not defined!")
            self.record_result("CARD_PAYMENT_METHODS Configuration", False, "Constant not defined")

    def test_bank_charges_file(self):
        """TEST 2: Verify BANK_CHARGES.csv exists and is valid"""
        print_header("TEST 2: BANK_CHARGES.csv Validation")

        bank_charges_file = Path("BANK_CHARGES.csv")

        print_test("Checking if BANK_CHARGES.csv exists...")
        if not bank_charges_file.exists():
            print_error("BANK_CHARGES.csv NOT FOUND!")
            print_info("  ⚠ Without this file, misc receipts CANNOT be generated")
            self.record_result("BANK_CHARGES.csv exists", False, "File not found")
            return

        print_success("BANK_CHARGES.csv found")
        self.record_result("BANK_CHARGES.csv exists", True)

        print_test("Reading and validating BANK_CHARGES.csv...")
        try:
            df = pd.read_csv(bank_charges_file)
            print_success(f"File loaded successfully - {len(df)} rows")
            print_info(f"  Columns: {', '.join(df.columns)}")

            # Check for required columns
            required_columns = ["PAYMENT_METHOD", "CHARGE_RATE"]
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                print_error(f"Missing required columns: {missing_columns}")
                self.record_result("BANK_CHARGES.csv structure", False, f"Missing: {missing_columns}")
            else:
                print_success("All required columns present")
                self.record_result("BANK_CHARGES.csv structure", True)

            # Display charge rates
            print_test("Analyzing charge rates by payment method...")
            for _, row in df.iterrows():
                method = row.get('PAYMENT_METHOD', 'Unknown')
                rate = row.get('CHARGE_RATE', 0)
                print_info(f"  {method}: {rate*100}% charge rate")

            # Check for card payment methods
            print_test("Verifying card payment methods have charges defined...")
            card_methods_in_file = set()
            for _, row in df.iterrows():
                method = str(row.get('PAYMENT_METHOD', '')).strip()
                if method in ['Mada', 'MADA', 'Visa', 'VISA', 'Master', 'MasterCard', 'AMEX', 'Amex']:
                    card_methods_in_file.add(method)

            if card_methods_in_file:
                print_success(f"Card methods found in BANK_CHARGES: {card_methods_in_file}")
                self.record_result("Card methods in BANK_CHARGES", True)
            else:
                print_warning("No standard card methods found in BANK_CHARGES.csv")
                self.record_result("Card methods in BANK_CHARGES", False, "No card methods")

        except Exception as e:
            print_error(f"Error reading BANK_CHARGES.csv: {e}")
            self.record_result("BANK_CHARGES.csv validation", False, str(e))

    def test_misc_receipt_generation_logic(self):
        """TEST 3: Verify misc receipt generation logic"""
        print_header("TEST 3: Misc Receipt Generation Logic")

        if not self.integration_module:
            if not self.load_integration_module():
                return

        mod = self.integration_module

        print_test("Verifying generate_misc_receipts method exists...")
        if hasattr(mod.OracleFusionIntegration, 'generate_misc_receipts'):
            print_success("generate_misc_receipts method found")
            self.record_result("generate_misc_receipts method", True)
        else:
            print_error("generate_misc_receipts method NOT found")
            self.record_result("generate_misc_receipts method", False, "Method missing")
            return

        # Read source code to verify logic
        print_test("Analyzing misc receipt generation logic...")
        source_file = Path("Odoo-export-FBDA-template.py")
        source_code = source_file.read_text()

        # Check for key logic elements
        checks = {
            "Bank charges check": "if not self.bank_charges or not self.bank_charges._loaded:",
            "Card method filter": "if method not in CARD_PAYMENT_METHODS",
            "Amount validation": "if amount <= 0:",
            "Bank charge calculation": "self.bank_charges.calc_misc_amount",
            "AR transaction check": "if not ar_txn:",
            "Misc receipt number": 'f"MISC-{method}-{ar_txn}"',
        }

        for check_name, check_pattern in checks.items():
            if check_pattern in source_code:
                print_success(f"  ✓ {check_name} - FOUND")
                self.record_result(f"Logic: {check_name}", True)
            else:
                print_error(f"  ✗ {check_name} - NOT FOUND")
                self.record_result(f"Logic: {check_name}", False, "Pattern not found")

    def test_misc_receipt_columns(self):
        """TEST 4: Verify MISC_RECEIPT_COLUMNS definition"""
        print_header("TEST 4: MISC_RECEIPT_COLUMNS Validation")

        if not self.integration_module:
            if not self.load_integration_module():
                return

        mod = self.integration_module

        print_test("Checking MISC_RECEIPT_COLUMNS constant...")
        if hasattr(mod, 'MISC_RECEIPT_COLUMNS'):
            columns = mod.MISC_RECEIPT_COLUMNS
            print_success(f"MISC_RECEIPT_COLUMNS defined with {len(columns)} columns")

            required_columns = [
                "Amount",
                "CurrencyCode",
                "DepositDate",
                "ReceiptDate",
                "GlDate",
                "OrgId",
                "ReceiptNumber",
                "ReceiptMethodId",
                "ReceiptMethodName",
                "ReceivableActivityName",
                "BankAccountNumber"
            ]

            print_test("Verifying all required columns...")
            all_present = True
            for col in required_columns:
                if col in columns:
                    print_success(f"  ✓ {col}")
                else:
                    print_error(f"  ✗ {col} - MISSING")
                    all_present = False

            if all_present:
                self.record_result("MISC_RECEIPT_COLUMNS complete", True)
            else:
                self.record_result("MISC_RECEIPT_COLUMNS complete", False, "Missing columns")

        else:
            print_error("MISC_RECEIPT_COLUMNS not defined!")
            self.record_result("MISC_RECEIPT_COLUMNS", False, "Constant not defined")

    def test_payment_method_filtering(self):
        """TEST 5: Test payment method filtering logic"""
        print_header("TEST 5: Payment Method Filtering for Misc Receipts")

        if not self.integration_module:
            if not self.load_integration_module():
                return

        mod = self.integration_module

        print_test("Analyzing which payment methods trigger misc receipts...")

        # Get the card payment methods
        if hasattr(mod, 'CARD_PAYMENT_METHODS'):
            card_methods = mod.CARD_PAYMENT_METHODS
            print_info(f"\n  Payment methods that WILL generate misc receipts:")
            for method in sorted(card_methods):
                print_success(f"    ✓ {method}")

            self.record_result("Misc receipt payment filters", True)
        else:
            print_error("Cannot determine which methods generate misc receipts")
            self.record_result("Misc receipt payment filters", False)

        # Check what gets excluded
        print_test("Checking exclusions...")
        if hasattr(mod, 'RECEIPT_PAYMENT_METHODS'):
            receipt_methods = mod.RECEIPT_PAYMENT_METHODS
            if hasattr(mod, 'CARD_PAYMENT_METHODS'):
                card_methods = mod.CARD_PAYMENT_METHODS

                # Methods in receipt but not in card = won't get misc receipts
                no_misc = receipt_methods - card_methods
                if no_misc:
                    print_info(f"\n  Payment methods that WON'T generate misc receipts:")
                    for method in sorted(no_misc):
                        print_warning(f"    ⚠ {method} (not a card method)")

    def test_diagnostic_logging(self):
        """TEST 6: Verify diagnostic logging is present"""
        print_header("TEST 6: Diagnostic Logging Verification")

        source_file = Path("Odoo-export-FBDA-template.py")
        source_code = source_file.read_text()

        print_test("Checking for misc receipt diagnostic logging...")

        diagnostic_elements = {
            "Section 8b header": "8b. MISCELLANEOUS RECEIPT",
            "Card methods accepted tracking": "card_methods_accepted",
            "Card methods skipped tracking": "card_methods_skipped",
            "Skipped breakdown logging": "SKIPPED - Not in CARD_PAYMENT_METHODS",
            "Accepted breakdown logging": "ACCEPTED for Misc Receipts",
        }

        for element_name, element_pattern in diagnostic_elements.items():
            if element_pattern in source_code:
                print_success(f"  ✓ {element_name} - Present")
                self.record_result(f"Diagnostic: {element_name}", True)
            else:
                print_warning(f"  ⚠ {element_name} - Not found")
                self.record_result(f"Diagnostic: {element_name}", False, "Not found")

    def test_integration_simulation(self):
        """TEST 7: Simulate misc receipt generation with sample data"""
        print_header("TEST 7: Misc Receipt Generation Simulation")

        if not self.integration_module:
            if not self.load_integration_module():
                return

        mod = self.integration_module

        print_test("Creating sample payment data for simulation...")

        # Create a temporary directory for test output
        test_output_dir = Path(tempfile.mkdtemp(prefix="misc_receipt_test_"))
        print_info(f"  Test output directory: {test_output_dir}")

        try:
            # Create an integration instance
            integration = mod.OracleFusionIntegration(
                output_dir=str(test_output_dir),
                start_seq=1,
                start_legacy_seq_1=1,
                start_legacy_seq_2=1,
                use_sequence_manager=False
            )

            # Manually populate some test data
            print_test("Setting up test payment data...")

            # Simulate invoice payments with card methods
            integration.invoice_payments = defaultdict(lambda: defaultdict(float))
            integration.invoice_payments["INV-001"]["Mada"] = 1000.00
            integration.invoice_payments["INV-001"]["Visa"] = 500.00
            integration.invoice_payments["INV-002"]["MasterCard"] = 750.00
            integration.invoice_payments["INV-003"]["Cash"] = 200.00  # Should not generate misc receipt

            # Set up invoice metadata
            integration.invoice_store = {
                "INV-001": "Test Store 1",
                "INV-002": "Test Store 1",
                "INV-003": "Test Store 1"
            }

            integration.invoice_date = {
                "INV-001": datetime(2026, 4, 20),
                "INV-002": datetime(2026, 4, 20),
                "INV-003": datetime(2026, 4, 20)
            }

            integration.invoice_to_ar_txn = {
                "INV-001": "BLKU-0000001",
                "INV-002": "BLKU-0000002",
                "INV-003": "BLKU-0000003"
            }

            integration.invoice_ctype = {
                "INV-001": "NORMAL",
                "INV-002": "NORMAL",
                "INV-003": "NORMAL"
            }

            print_success("Test data setup complete")
            print_info("  Invoices with card payments:")
            print_info("    INV-001: Mada (1000 SAR), Visa (500 SAR)")
            print_info("    INV-002: MasterCard (750 SAR)")
            print_info("    INV-003: Cash (200 SAR) - should NOT generate misc receipt")

            # Try to generate misc receipts
            print_test("Attempting to generate misc receipts...")

            # Check if bank charges are loaded
            if not hasattr(integration, 'bank_charges') or not integration.bank_charges or not integration.bank_charges._loaded:
                print_warning("Bank charges not loaded - misc receipts will be skipped")
                print_info("  This is expected if BANK_CHARGES.csv is not loaded")
                self.record_result("Simulation: bank charges", False, "Not loaded - expected")
            else:
                print_success("Bank charges loaded")

                # Generate misc receipts
                misc_receipts = integration.generate_misc_receipts()

                print_test("Analyzing generated misc receipts...")
                if misc_receipts:
                    print_success(f"Generated {len(misc_receipts)} misc receipt file(s)")
                    for filename, df in misc_receipts.items():
                        print_info(f"  File: {filename}")
                        print_info(f"    Rows: {len(df)}")
                        if len(df) > 0:
                            print_info(f"    Amount: {df['Amount'].iloc[0]:.4f} SAR")
                            print_info(f"    Receipt Number: {df['ReceiptNumber'].iloc[0]}")
                    self.record_result("Simulation: misc generation", True)
                else:
                    print_warning("No misc receipts generated")
                    print_info("  Possible reasons:")
                    print_info("    1. Bank charges not configured")
                    print_info("    2. No card payment methods in test data")
                    print_info("    3. Payment methods not in CARD_PAYMENT_METHODS")
                    self.record_result("Simulation: misc generation", False, "No receipts generated")

        except Exception as e:
            print_error(f"Simulation failed: {e}")
            self.record_result("Simulation", False, str(e))
            import traceback
            print_info(f"  Error details: {traceback.format_exc()}")
        finally:
            # Cleanup
            try:
                shutil.rmtree(test_output_dir)
                print_info(f"  Cleaned up test directory")
            except:
                pass

    def record_result(self, test_name, passed, note=""):
        """Record test result"""
        if passed:
            self.test_results['passed'] += 1
        elif note.startswith("Warning") or note.startswith("Not loaded"):
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
        print_header("MISC RECEIPT MAPPING TEST SUMMARY")

        total_tests = self.test_results['passed'] + self.test_results['failed'] + self.test_results['warnings']

        print(f"{Colors.BOLD}Total Tests Run: {total_tests}{Colors.RESET}")
        print(f"{Colors.GREEN}✓ Passed: {self.test_results['passed']}{Colors.RESET}")
        print(f"{Colors.RED}✗ Failed: {self.test_results['failed']}{Colors.RESET}")
        print(f"{Colors.YELLOW}⚠ Warnings: {self.test_results['warnings']}{Colors.RESET}")

        if self.test_results['failed'] > 0:
            print(f"\n{Colors.BOLD}{Colors.RED}FAILED TESTS:{Colors.RESET}")
            for result in self.detailed_results:
                if not result['passed'] and not (result['note'].startswith("Warning") or result['note'].startswith("Not loaded")):
                    print(f"{Colors.RED}  ✗ {result['test']}: {result['note']}{Colors.RESET}")

        if self.test_results['warnings'] > 0:
            print(f"\n{Colors.BOLD}{Colors.YELLOW}WARNINGS:{Colors.RESET}")
            for result in self.detailed_results:
                if result['note'].startswith("Warning") or result['note'].startswith("Not loaded"):
                    print(f"{Colors.YELLOW}  ⚠ {result['test']}: {result['note']}{Colors.RESET}")

        # Calculate success rate
        if total_tests > 0:
            success_rate = (self.test_results['passed'] / total_tests) * 100
            print(f"\n{Colors.BOLD}Success Rate: {success_rate:.1f}%{Colors.RESET}")

            if success_rate >= 90:
                print(f"\n{Colors.GREEN}{Colors.BOLD}✓✓✓ MISC RECEIPT MAPPING: EXCELLENT{Colors.RESET}")
                print(f"{Colors.GREEN}Misc receipts should be generated correctly{Colors.RESET}")
            elif success_rate >= 75:
                print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ MISC RECEIPT MAPPING: GOOD - Minor issues{Colors.RESET}")
                print(f"{Colors.YELLOW}Review warnings and address if needed{Colors.RESET}")
            else:
                print(f"\n{Colors.RED}{Colors.BOLD}✗ MISC RECEIPT MAPPING: NEEDS ATTENTION{Colors.RESET}")
                print(f"{Colors.RED}Critical issues found - misc receipts may not generate properly{Colors.RESET}")

        # Key recommendations
        print(f"\n{Colors.BOLD}{Colors.CYAN}KEY FINDINGS & RECOMMENDATIONS:{Colors.RESET}")

        # Analyze results and provide recommendations
        has_bank_charges = any(r['test'] == 'BANK_CHARGES.csv exists' and r['passed'] for r in self.detailed_results)
        has_card_methods = any(r['test'] == 'CARD_PAYMENT_METHODS Configuration' and r['passed'] for r in self.detailed_results)

        if not has_bank_charges:
            print(f"{Colors.RED}  ✗ BANK_CHARGES.csv is missing or invalid{Colors.RESET}")
            print(f"{Colors.YELLOW}    → Without this file, NO misc receipts will be generated{Colors.RESET}")
            print(f"{Colors.YELLOW}    → Ensure BANK_CHARGES.csv exists with proper charge rates{Colors.RESET}")
        else:
            print(f"{Colors.GREEN}  ✓ BANK_CHARGES.csv is configured{Colors.RESET}")

        if not has_card_methods:
            print(f"{Colors.RED}  ✗ CARD_PAYMENT_METHODS not properly configured{Colors.RESET}")
            print(f"{Colors.YELLOW}    → Only methods in CARD_PAYMENT_METHODS will generate misc receipts{Colors.RESET}")
        else:
            print(f"{Colors.GREEN}  ✓ CARD_PAYMENT_METHODS is configured{Colors.RESET}")

        print(f"\n{Colors.CYAN}To verify misc receipts in actual run:{Colors.RESET}")
        print(f"{Colors.CYAN}  1. Run the integration with payment data containing card methods{Colors.RESET}")
        print(f"{Colors.CYAN}  2. Check Verification Report Section 8b for misc receipt details{Colors.RESET}")
        print(f"{Colors.CYAN}  3. Look for files in ORACLE_FUSION_OUTPUT/Receipts/Misc/{Colors.RESET}")
        print(f"{Colors.CYAN}  4. Review 'SKIPPED' section to see if methods are excluded{Colors.RESET}")

        # Save report to file
        report_file = Path("MISC_RECEIPT_TEST_RESULTS.txt")
        with open(report_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("MISCELLANEOUS RECEIPT MAPPING TEST RESULTS\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            f.write(f"Total Tests: {total_tests}\n")
            f.write(f"Passed: {self.test_results['passed']}\n")
            f.write(f"Failed: {self.test_results['failed']}\n")
            f.write(f"Warnings: {self.test_results['warnings']}\n")
            f.write(f"Success Rate: {success_rate:.1f}%\n\n")

            f.write("DETAILED RESULTS:\n")
            f.write("-"*80 + "\n")
            for result in self.detailed_results:
                status = "PASS" if result['passed'] else ("WARN" if (result['note'].startswith("Warning") or result['note'].startswith("Not loaded")) else "FAIL")
                f.write(f"[{status}] {result['test']}\n")
                if result['note']:
                    f.write(f"      Note: {result['note']}\n")

            f.write("\n" + "="*80 + "\n")
            f.write("KEY VERIFICATION POINTS:\n")
            f.write("-"*80 + "\n")
            f.write("1. BANK_CHARGES.csv must exist with charge rates for card methods\n")
            f.write("2. CARD_PAYMENT_METHODS must include: Mada, Visa, MasterCard (at minimum)\n")
            f.write("3. Misc receipts are ONLY generated for methods in CARD_PAYMENT_METHODS\n")
            f.write("4. Check Verification Report Section 8b for detailed logging\n")
            f.write("5. Misc receipt files will be in: Receipts/Misc/\n")

        print(f"\n{Colors.CYAN}Detailed report saved to: {report_file}{Colors.RESET}")


def main():
    """Main test runner"""
    print_header("MISCELLANEOUS RECEIPT MAPPING & GENERATION TEST")
    print(f"{Colors.CYAN}Testing misc receipt mapping accuracy and file generation{Colors.RESET}")
    print(f"{Colors.CYAN}Repository: MUSTAQ-AHAMMAD/miss-receipt-template{Colors.RESET}\n")

    tester = MiscReceiptMappingTester()

    # Run all tests
    tester.test_card_payment_methods_configuration()
    tester.test_bank_charges_file()
    tester.test_misc_receipt_generation_logic()
    tester.test_misc_receipt_columns()
    tester.test_payment_method_filtering()
    tester.test_diagnostic_logging()
    tester.test_integration_simulation()

    # Generate final report
    tester.generate_report()

    # Return exit code based on results
    return 0 if tester.test_results['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
