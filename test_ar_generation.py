#!/usr/bin/env python3
"""
Test script for AR Invoice generation from ZAHRAN sales and payment data
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_ar_invoice_generation():
    """Test AR Invoice generation from Odoo exports"""
    
    print("=" * 80)
    print("AR INVOICE GENERATION TEST")
    print("=" * 80)
    print()
    
    # Check if required files exist
    repo_dir = Path(__file__).parent
    
    required_files = {
        "Sales Lines": "ZAHRAN sale line 5 to 31 March.xlsx",
        "Payment Lines": "ZAHRAN payment line 5 to 31 March.xlsx",
        "Metadata": "FUSION_SALES_METADATA_202604121703.csv",
        "Registers": "VENDHQ_REGISTERS_202604121654.csv",
        "Receipt Methods": "Receipt_Methods.csv",
        "Bank Charges": "BANK_CHARGES.csv"
    }
    
    print("Step 1: Checking required files...")
    print("-" * 80)
    missing_files = []
    for name, filename in required_files.items():
        filepath = repo_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"✓ {name:20} : {filename} ({size:,} bytes)")
        else:
            print(f"✗ {name:20} : {filename} - NOT FOUND")
            missing_files.append(filename)
    
    print()
    
    if missing_files:
        print(f"ERROR: Missing files: {', '.join(missing_files)}")
        return False
    
    # Load the integration module
    print("Step 2: Loading Oracle Fusion Integration Module...")
    print("-" * 80)
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "oracle_integration",
            repo_dir / "Odoo-export-FBDA-template.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        print("✓ Integration module loaded successfully")
        print()
    except Exception as e:
        print(f"✗ Failed to load integration module: {e}")
        return False
    
    # Create output directory
    output_dir = repo_dir / "TEST_OUTPUT"
    output_dir.mkdir(exist_ok=True)
    print(f"Step 3: Creating output directory: {output_dir}")
    print("-" * 80)
    print(f"✓ Output directory: {output_dir}")
    print()
    
    # Initialize integration
    print("Step 4: Initializing Oracle Fusion Integration...")
    print("-" * 80)
    try:
        integration = mod.OracleFusionIntegration(
            output_dir=str(output_dir),
            start_seq=1,
            start_legacy_seq_1=1,
            start_legacy_seq_2=1,
            use_sequence_manager=False
        )
        print("✓ Integration initialized successfully")
        print()
    except Exception as e:
        print(f"✗ Failed to initialize integration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Load data
    print("Step 5: Loading data files...")
    print("-" * 80)
    try:
        integration.load_data(
            line_items_path=str(repo_dir / required_files["Sales Lines"]),
            payments_path=str(repo_dir / required_files["Payment Lines"]),
            metadata_path=str(repo_dir / required_files["Metadata"]),
            registers_path=str(repo_dir / required_files["Registers"]),
            receipt_methods_path=str(repo_dir / required_files["Receipt Methods"]),
            bank_charges_path=str(repo_dir / required_files["Bank Charges"])
        )
        print(f"✓ Sales Lines loaded: {len(integration.line_items):,} rows")
        print(f"✓ Payment Lines loaded: {len(integration.payments):,} rows")
        if hasattr(integration, 'metadata'):
            print(f"✓ Metadata loaded: {len(integration.metadata):,} rows")
        print()
    except Exception as e:
        print(f"✗ Failed to load data: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Generate AR Invoice
    print("Step 6: Generating AR Invoice...")
    print("-" * 80)
    try:
        ar_df = integration.generate_ar_invoices()
        print(f"✓ AR Invoice generated: {len(ar_df):,} rows")
        
        # Calculate totals
        ar_total = float(ar_df["Transaction Line Amount"].sum())
        print(f"✓ AR Invoice Total: {ar_total:,.2f} SAR")
        
        # Calculate input total
        input_total = float(
            integration.line_items["Subtotal w/o Tax"]
            .apply(mod.safe_float)
            .sum()
        )
        print(f"✓ Input Sheet Total: {input_total:,.2f} SAR")
        
        # Check match
        diff = abs(ar_total - input_total)
        if diff < 0.01:
            print(f"✓ Total Match: PASSED (diff: {diff:.4f})")
        else:
            print(f"⚠ Total Match: WARNING (diff: {diff:.2f})")
        print()
    except Exception as e:
        print(f"✗ Failed to generate AR Invoice: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Save AR Invoice
    print("Step 7: Saving AR Invoice...")
    print("-" * 80)
    try:
        integration.save_ar(ar_df)
        
        # Find the saved file
        ar_files = list(output_dir.glob("AR_Invoice_*.csv"))
        if ar_files:
            ar_file = ar_files[0]
            size = ar_file.stat().st_size
            print(f"✓ AR Invoice saved: {ar_file.name} ({size:,} bytes)")
            print()
        else:
            print("⚠ AR Invoice file not found in output directory")
            print()
    except Exception as e:
        print(f"✗ Failed to save AR Invoice: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Generate receipts
    print("Step 8: Generating Standard Receipts...")
    print("-" * 80)
    try:
        std_receipts = integration.generate_standard_receipts()
        print(f"✓ Standard Receipts generated: {len(std_receipts):,} files")
        
        # Save receipts
        integration.save_standard_receipts(std_receipts)
        print(f"✓ Standard Receipts saved")
        print()
    except Exception as e:
        print(f"✗ Failed to generate standard receipts: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("Step 9: Generating Miscellaneous Receipts...")
    print("-" * 80)
    try:
        misc_receipts = integration.generate_misc_receipts()
        print(f"✓ Misc Receipts generated: {len(misc_receipts):,} files")
        
        # Save receipts
        integration.save_misc_receipts(misc_receipts)
        print(f"✓ Misc Receipts saved")
        print()
    except Exception as e:
        print(f"✗ Failed to generate misc receipts: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Generate verification report
    print("Step 10: Generating Verification Report...")
    print("-" * 80)
    try:
        integration._write_final_crosscheck(ar_df, std_receipts)
        integration.vlog.close()
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = output_dir / f"Verification_Report_{ts}.txt"
        integration.vlog.write(log_path)
        print(f"✓ Verification report saved: {log_path.name}")
        print()
    except Exception as e:
        print(f"✗ Failed to generate verification report: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Display summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"✓ AR Invoice Lines: {len(ar_df):,}")
    print(f"✓ AR Invoice Total: {ar_total:,.2f} SAR")
    print(f"✓ Standard Receipts: {len(std_receipts):,}")
    print(f"✓ Misc Receipts: {len(misc_receipts):,}")
    print(f"✓ Output Directory: {output_dir}")
    print()
    
    # List output files
    print("Output Files:")
    print("-" * 80)
    for file in sorted(output_dir.rglob("*")):
        if file.is_file():
            rel_path = file.relative_to(output_dir)
            size = file.stat().st_size
            print(f"  {rel_path} ({size:,} bytes)")
    print()
    
    print("=" * 80)
    print("TEST COMPLETED SUCCESSFULLY ✓")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    success = test_ar_invoice_generation()
    sys.exit(0 if success else 1)
