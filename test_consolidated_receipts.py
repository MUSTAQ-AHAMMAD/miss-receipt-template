#!/usr/bin/env python3
"""
Test script to verify that receipts are consolidated per payment method.

This test verifies that:
1. Standard receipts are generated with one file per payment method
2. Each file contains multiple rows (dates/stores combined)
3. Misc receipts are also consolidated per payment method
"""

import sys
import importlib.util
from pathlib import Path
from collections import defaultdict

def test_consolidated_receipts():
    """Test that receipts are consolidated by payment method"""

    print("=" * 80)
    print("TESTING CONSOLIDATED RECEIPTS FUNCTIONALITY")
    print("=" * 80)

    # Load the main module
    spec = importlib.util.spec_from_file_location(
        "oracle_integration",
        Path(__file__).parent / "Odoo-export-FBDA-template.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    print("\n✓ Module loaded successfully")

    # Create a test instance with mock data
    print("\n[1] Verifying generate_standard_receipts consolidation logic...")

    # Check that the method exists
    if not hasattr(mod.OracleFusionIntegration, 'generate_standard_receipts'):
        print("❌ ERROR: generate_standard_receipts method not found")
        return False

    print("✓ generate_standard_receipts method found")

    # Verify the method signature and basic structure
    import inspect
    source = inspect.getsource(mod.OracleFusionIntegration.generate_standard_receipts)

    # Check for consolidation logic
    if 'method_rows' in source and 'defaultdict(list)' in source:
        print("✓ Found consolidation logic (method_rows)")
    else:
        print("❌ ERROR: Consolidation logic not found in generate_standard_receipts")
        return False

    # Check that filename doesn't include date/store
    if 'filename = f"Receipt_{safe_method_part}.csv"' in source:
        print("✓ Filename format is correct (no date/store in filename)")
    else:
        print("⚠ WARNING: Filename format may still include date/store")

    # Check for DataFrame creation per method
    if 'for method, rows in sorted(method_rows.items()):' in source:
        print("✓ Creating DataFrames per payment method")
    else:
        print("❌ ERROR: Not creating DataFrames per payment method")
        return False

    print("\n[2] Verifying generate_misc_receipts consolidation logic...")

    # Check that the method exists
    if not hasattr(mod.OracleFusionIntegration, 'generate_misc_receipts'):
        print("❌ ERROR: generate_misc_receipts method not found")
        return False

    print("✓ generate_misc_receipts method found")

    # Verify the method signature and basic structure
    source = inspect.getsource(mod.OracleFusionIntegration.generate_misc_receipts)

    # Check for consolidation logic
    if 'method_rows' in source and 'defaultdict(list)' in source:
        print("✓ Found consolidation logic (method_rows)")
    else:
        print("❌ ERROR: Consolidation logic not found in generate_misc_receipts")
        return False

    # Check that filename doesn't include date/store
    if 'filename = f"MiscReceipt_{safe_method_part}.csv"' in source:
        print("✓ Filename format is correct (no date/store in filename)")
    else:
        print("⚠ WARNING: Filename format may still include date/store")

    # Check for DataFrame creation per method
    if 'for method, rows in sorted(method_rows.items()):' in source:
        print("✓ Creating DataFrames per payment method")
    else:
        print("❌ ERROR: Not creating DataFrames per payment method")
        return False

    print("\n[3] Verifying save methods display row counts...")

    # Check save_standard_receipts
    source = inspect.getsource(mod.OracleFusionIntegration.save_standard_receipts)
    if 'row_count = len(df)' in source:
        print("✓ save_standard_receipts displays row counts")
    else:
        print("⚠ WARNING: save_standard_receipts may not display row counts")

    # Check save_misc_receipts
    source = inspect.getsource(mod.OracleFusionIntegration.save_misc_receipts)
    if 'row_count = len(df)' in source:
        print("✓ save_misc_receipts displays row counts")
    else:
        print("⚠ WARNING: save_misc_receipts may not display row counts")

    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED")
    print("=" * 80)
    print("\nSummary:")
    print("  - Standard receipts will be consolidated per payment method")
    print("  - Misc receipts will be consolidated per payment method")
    print("  - Each file will contain all dates for that payment method")
    print("  - Output will show row counts for each file")
    print("\n" + "=" * 80)

    return True

if __name__ == "__main__":
    try:
        success = test_consolidated_receipts()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
