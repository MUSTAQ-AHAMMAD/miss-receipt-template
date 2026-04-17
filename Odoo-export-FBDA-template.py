"""
================================================================================
ORACLE FUSION FINANCIAL INTEGRATION MODULE - CORRECTED & RELIABLE
================================================================================

FIXES IN THIS VERSION:
- Input row count == Output AR row count (no dropped rows)
- Order Ref values cleaned of whitespace/invisible chars at load time
- Pre-built index used for per-invoice row lookup (no filter mismatch)
- Quantity sign matches amount sign (returns handled correctly — both directions)
- Unit Selling Price always positive (abs(amount)/abs(quantity))
- Customer Ordered Quantity always empty
- Standard receipt columns match standard_receipt_template.csv exactly
- Misc receipt columns match misc_receipt_template.csv exactly
- Receipt amounts from payments file (not AR totals)
- Cap logic fixed (> not compareTo-style bug)
- Unit of Measure Code blank; value read from "Order Lines/Base UoM" → Name field
- Segment 1 & 2 use random alphanumeric prefix per run (no cross-run conflicts)
- Max transaction number logged in report for next-run sequencing
- AR invoice filename includes org name + date (e.g. AR_Invoice_ALQURASHI_KSA_05_31_May2026.csv)
- Empty barcode treated as discount item: Memo Line Name = "Discount Item", Inventory Item Number = ""
- Positive amount + negative quantity (return) now forces amount negative to match quantity sign

================================================================================
"""

from __future__ import annotations

import json
import random
import re
import string
import warnings
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ============================================================================
# CONSTANTS
# ============================================================================

RECEIPT_PAYMENT_METHODS    = {"Cash", "Mada", "Visa", "MasterCard"}
NO_RECEIPT_PAYMENT_METHODS = {"TABBY", "TAMARA"}
CARD_PAYMENT_METHODS       = {"Mada", "Visa", "MasterCard"}

PAYMENT_METHOD_NORM: Dict[str, str] = {
    "CASH":        "Cash",
    "MADA":        "Mada",
    "VISA":        "Visa",
    "MASTERCARD":  "MasterCard",
    "MASTER CARD": "MasterCard",
    "MASTER":      "MasterCard",
    "MC":          "MasterCard",
    "TAMARA":      "TAMARA",
    "TABBY":       "TABBY",
    "AMEX":        "Amex",
    "APPLE PAY":   "Apple Pay",
    "APPLEPAY":    "Apple Pay",
    "STC PAY":     "STC Pay",
    "STCPAY":      "STC Pay",
    "GCCNET":      "GCCNET",
}

PAYMENT_BANK_MAP_FALLBACK: Dict[str, Tuple[str, str]] = {
    "Cash":       ("Cash Bank",       "Cash Account"),
    "Mada":       ("Mada Bank",       "Mada Account"),
    "Visa":       ("Visa Bank",       "Visa Account"),
    "MasterCard": ("MasterCard Bank", "MasterCard Account"),
    "Amex":       ("Amex Bank",       "Amex Account"),
    "Apple Pay":  ("Apple Pay Bank",  "Apple Pay Account"),
    "STC Pay":    ("STC Pay Bank",    "STC Pay Account"),
}
DEFAULT_BANK: Tuple[str, str] = ("Cash Bank", "Cash Account")

AR_STATIC: Dict[str, str] = {
    "Transaction Batch Source Name":       "Manual_Imported",
    "Transaction Type Name":               "Vend Invoice",
    "Payment Terms":                       "IMMEDIATE",
    "Transaction Line Type":               "LINE",
    "Currency Code":                       "SAR",
    "Currency Conversion Type":            "Corporate",
    "Currency Conversion Rate":            "1",
    "Line Transactions Flexfield Context": "Legacy",
    "Default Taxation Country":            "SA",
    "Comments":                            "AlQurashi-KSA",
    "END":                                 "END",
}

DEFAULT_TAX_CODE = "OUTPUT-GOODS-DOM-15%"

STANDARD_RECEIPT_COLUMNS = [
    "ReceiptNumber",
    "ReceiptMethod",
    "ReceiptDate",
    "BusinessUnit",
    "CustomerAccountNumber",
    "CustomerSite",
    "Amount",
    "Currency",
    "RemittanceBankAccountNumber",
    "AccountingDate",
]

MISC_RECEIPT_COLUMNS = [
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
    "BankAccountNumber",
]


# ============================================================================
# AR INVOICE COLUMN HEADERS
# ============================================================================

def get_ar_columns() -> List[str]:
    return [
        "ID",
        "Transaction Batch Source Name",
        "Transaction Type Name",
        "Payment Terms",
        "Transaction Date",
        "Accounting Date",
        "Transaction Number",
        "Original System Bill-to Customer Reference",
        "Original System Bill-to Customer Address Reference",
        "Original System Bill-to Customer Contact Reference",
        "Original System Ship-to Customer Reference",
        "Original System Ship-to Customer Address Reference",
        "Original System Ship-to Customer Contact Reference",
        "Original System Ship-to Customer Account Reference",
        "Original System Ship-to Customer Account Address Reference",
        "Original System Ship-to Customer Account Contact Reference",
        "Original System Sold-to Customer Reference",
        "Original System Sold-to Customer Account Reference",
        "Bill-to Customer Account Number",
        "Bill-to Customer Site Number",
        "Bill-to Contact Party Number",
        "Ship-to Customer Account Number",
        "Ship-to Customer Site Number",
        "Ship-to Contact Party Number",
        "Sold-to Customer Account Number",
        "Transaction Line Type",
        "Transaction Line Description",
        "Currency Code",
        "Currency Conversion Type",
        "Currency Conversion Date",
        "Currency Conversion Rate",
        "Transaction Line Amount",
        "Transaction Line Quantity",
        "Customer Ordered Quantity",
        "Unit Selling Price",
        "Unit Standard Price",
        "Line Transactions Flexfield Context",
        "Line Transactions Flexfield Segment 1",
        "Line Transactions Flexfield Segment 2",
        "Line Transactions Flexfield Segment 3",
        "Line Transactions Flexfield Segment 4",
        "Line Transactions Flexfield Segment 5",
        "Line Transactions Flexfield Segment 6",
        "Line Transactions Flexfield Segment 7",
        "Line Transactions Flexfield Segment 8",
        "Line Transactions Flexfield Segment 9",
        "Line Transactions Flexfield Segment 10",
        "Line Transactions Flexfield Segment 11",
        "Line Transactions Flexfield Segment 12",
        "Line Transactions Flexfield Segment 13",
        "Line Transactions Flexfield Segment 14",
        "Line Transactions Flexfield Segment 15",
        "Primary Salesperson Number",
        "Tax Classification Code",
        "Legal Entity Identifier",
        "Accounted Amount in Ledger Currency",
        "Sales Order Number",
        "Sales Order Date",
        "Actual Ship Date",
        "Warehouse Code",
        "Unit of Measure Code",
        "Unit of Measure Name",
        "Invoicing Rule Name",
        "Revenue Scheduling Rule Name",
        "Number of Revenue Periods",
        "Revenue Scheduling Rule Start Date",
        "Revenue Scheduling Rule End Date",
        "Reason Code Meaning",
        "Last Period to Credit",
        "Transaction Business Category Code",
        "Product Fiscal Classification Code",
        "Product Category Code",
        "Product Type",
        "Line Intended Use Code",
        "Assessable Value",
        "Document Sub Type",
        "Default Taxation Country",
        "User Defined Fiscal Classification",
        "Tax Invoice Number",
        "Tax Invoice Date",
        "Tax Regime Code",
        "Tax",
        "Tax Status Code",
        "Tax Rate Code",
        "Tax Jurisdiction Code",
        "First Party Registration Number",
        "Third Party Registration Number",
        "Final Discharge Location",
        "Taxable Amount",
        "Taxable Flag",
        "Tax Exemption Flag",
        "Tax Exemption Reason Code",
        "Tax Exemption Reason Code Meaning",
        "Tax Exemption Certificate Number",
        "Line Amount Includes Tax Flag",
        "Tax Precedence",
        "Credit Method To Be Used For Lines With Revenue Scheduling Rules",
        "Credit Method To Be Used For Transactions With Split Payment Terms",
        "Reason Code",
        "Tax Rate",
        "FOB Point",
        "Carrier",
        "Shipping Reference",
        "Sales Order Line Number",
        "Sales Order Source",
        "Sales Order Revision Number",
        "Purchase Order Number",
        "Purchase Order Revision Number",
        "Purchase Order Date",
        "Agreement Name",
        "Memo Line Name",
        "Document Number",
        "Original System Batch Name",
        "Link-to Transactions Flexfield Context",
        "Link-to Transactions Flexfield Segment 1",
        "Link-to Transactions Flexfield Segment 2",
        "Link-to Transactions Flexfield Segment 3",
        "Link-to Transactions Flexfield Segment 4",
        "Link-to Transactions Flexfield Segment 5",
        "Link-to Transactions Flexfield Segment 6",
        "Link-to Transactions Flexfield Segment 7",
        "Link-to Transactions Flexfield Segment 8",
        "Link-to Transactions Flexfield Segment 9",
        "Link-to Transactions Flexfield Segment 10",
        "Link-to Transactions Flexfield Segment 11",
        "Link-to Transactions Flexfield Segment 12",
        "Link-to Transactions Flexfield Segment 13",
        "Link-to Transactions Flexfield Segment 14",
        "Link-to Transactions Flexfield Segment 15",
        "Reference Transactions Flexfield Context",
        "Reference Transactions Flexfield Segment 1",
        "Reference Transactions Flexfield Segment 2",
        "Reference Transactions Flexfield Segment 3",
        "Reference Transactions Flexfield Segment 4",
        "Reference Transactions Flexfield Segment 5",
        "Reference Transactions Flexfield Segment 6",
        "Reference Transactions Flexfield Segment 7",
        "Reference Transactions Flexfield Segment 8",
        "Reference Transactions Flexfield Segment 9",
        "Reference Transactions Flexfield Segment 10",
        "Reference Transactions Flexfield Segment 11",
        "Reference Transactions Flexfield Segment 12",
        "Reference Transactions Flexfield Segment 13",
        "Reference Transactions Flexfield Segment 14",
        "Reference Transactions Flexfield Segment 15",
        "Link To Parent Line Context",
        "Link To Parent Line Segment 1",
        "Link To Parent Line Segment 2",
        "Link To Parent Line Segment 3",
        "Link To Parent Line Segment 4",
        "Link To Parent Line Segment 5",
        "Link To Parent Line Segment 6",
        "Link To Parent Line Segment 7",
        "Link To Parent Line Segment 8",
        "Link To Parent Line Segment 9",
        "Link To Parent Line Segment 10",
        "Link To Parent Line Segment 11",
        "Link To Parent Line Segment 12",
        "Link To Parent Line Segment 13",
        "Link To Parent Line Segment 14",
        "Link To Parent Line Segment 15",
        "Receipt Method Name",
        "Printing Option",
        "Related Batch Source Name",
        "Related Transaction Number",
        "Inventory Item Number",
        "Inventory Item Segment 2",
        "Inventory Item Segment 3",
        "Inventory Item Segment 4",
        "Inventory Item Segment 5",
        "Inventory Item Segment 6",
        "Inventory Item Segment 7",
        "Inventory Item Segment 8",
        "Inventory Item Segment 9",
        "Inventory Item Segment 10",
        "Inventory Item Segment 11",
        "Inventory Item Segment 12",
        "Inventory Item Segment 13",
        "Inventory Item Segment 14",
        "Inventory Item Segment 15",
        "Inventory Item Segment 16",
        "Inventory Item Segment 17",
        "Inventory Item Segment 18",
        "Inventory Item Segment 19",
        "Inventory Item Segment 20",
        "Bill To Customer Bank Account Name",
        "Reset Transaction Date Flag",
        "Payment Server Order Number",
        "Last Transaction on Debit Authorization",
        "Approval Code",
        "Address Verification Code",
        "Transaction Line Translated Description",
        "Consolidated Billing Number",
        "Promised Commitment Amount",
        "Payment Set Identifier",
        "Original Accounting Date",
        "Invoiced Line Accounting Level",
        "Override AutoAccounting Flag",
        "Historical Flag",
        "Deferral Exclusion Flag",
        "Payment Attributes",
        "Invoice Billing Date",
        "Invoice Lines Flexfield Context",
        "Invoice Lines Flexfield Segment 1",
        "Invoice Lines Flexfield Segment 2",
        "Invoice Lines Flexfield Segment 3",
        "Invoice Lines Flexfield Segment 4",
        "Invoice Lines Flexfield Segment 5",
        "Invoice Lines Flexfield Segment 6",
        "Invoice Lines Flexfield Segment 7",
        "Invoice Lines Flexfield Segment 8",
        "Invoice Lines Flexfield Segment 9",
        "Invoice Lines Flexfield Segment 10",
        "Invoice Lines Flexfield Segment 11",
        "Invoice Lines Flexfield Segment 12",
        "Invoice Lines Flexfield Segment 13",
        "Invoice Lines Flexfield Segment 14",
        "Invoice Lines Flexfield Segment 15",
        "Invoice Transactions Flexfield Context",
        "Invoice Transactions Flexfield Segment 1",
        "Invoice Transactions Flexfield Segment 2",
        "Invoice Transactions Flexfield Segment 3",
        "Invoice Transactions Flexfield Segment 4",
        "Invoice Transactions Flexfield Segment 5",
        "Invoice Transactions Flexfield Segment 6",
        "Invoice Transactions Flexfield Segment 7",
        "Invoice Transactions Flexfield Segment 8",
        "Invoice Transactions Flexfield Segment 9",
        "Invoice Transactions Flexfield Segment 10",
        "Invoice Transactions Flexfield Segment 11",
        "Invoice Transactions Flexfield Segment 12",
        "Invoice Transactions Flexfield Segment 13",
        "Invoice Transactions Flexfield Segment 14",
        "Invoice Transactions Flexfield Segment 15",
        "Receivables Transaction Region Information Flexfield Context",
        "Receivables Transaction Region Information Flexfield Segment 1",
        "Receivables Transaction Region Information Flexfield Segment 2",
        "Receivables Transaction Region Information Flexfield Segment 3",
        "Receivables Transaction Region Information Flexfield Segment 4",
        "Receivables Transaction Region Information Flexfield Segment 5",
        "Receivables Transaction Region Information Flexfield Segment 6",
        "Receivables Transaction Region Information Flexfield Segment 7",
        "Receivables Transaction Region Information Flexfield Segment 8",
        "Receivables Transaction Region Information Flexfield Segment 9",
        "Receivables Transaction Region Information Flexfield Segment 10",
        "Receivables Transaction Region Information Flexfield Segment 11",
        "Receivables Transaction Region Information Flexfield Segment 12",
        "Receivables Transaction Region Information Flexfield Segment 13",
        "Receivables Transaction Region Information Flexfield Segment 14",
        "Receivables Transaction Region Information Flexfield Segment 15",
        "Receivables Transaction Region Information Flexfield Segment 16",
        "Receivables Transaction Region Information Flexfield Segment 17",
        "Receivables Transaction Region Information Flexfield Segment 18",
        "Receivables Transaction Region Information Flexfield Segment 19",
        "Receivables Transaction Region Information Flexfield Segment 20",
        "Receivables Transaction Region Information Flexfield Segment 21",
        "Receivables Transaction Region Information Flexfield Segment 22",
        "Receivables Transaction Region Information Flexfield Segment 23",
        "Receivables Transaction Region Information Flexfield Segment 24",
        "Receivables Transaction Region Information Flexfield Segment 25",
        "Receivables Transaction Region Information Flexfield Segment 26",
        "Receivables Transaction Region Information Flexfield Segment 27",
        "Receivables Transaction Region Information Flexfield Segment 28",
        "Receivables Transaction Region Information Flexfield Segment 29",
        "Receivables Transaction Region Information Flexfield Segment 30",
        "Line Global Descriptive Flexfield Attribute Category",
        "Line Global Descriptive Flexfield Segment 1",
        "Line Global Descriptive Flexfield Segment 2",
        "Line Global Descriptive Flexfield Segment 3",
        "Line Global Descriptive Flexfield Segment 4",
        "Line Global Descriptive Flexfield Segment 5",
        "Line Global Descriptive Flexfield Segment 6",
        "Line Global Descriptive Flexfield Segment 7",
        "Line Global Descriptive Flexfield Segment 8",
        "Line Global Descriptive Flexfield Segment 9",
        "Line Global Descriptive Flexfield Segment 10",
        "Line Global Descriptive Flexfield Segment 11",
        "Line Global Descriptive Flexfield Segment 12",
        "Line Global Descriptive Flexfield Segment 13",
        "Line Global Descriptive Flexfield Segment 14",
        "Line Global Descriptive Flexfield Segment 15",
        "Line Global Descriptive Flexfield Segment 16",
        "Line Global Descriptive Flexfield Segment 17",
        "Line Global Descriptive Flexfield Segment 18",
        "Line Global Descriptive Flexfield Segment 19",
        "Line Global Descriptive Flexfield Segment 20",
        "Comments",
        "Notes from Source",
        "Credit Card Token Number",
        "Credit Card Expiration Date",
        "First Name of the Credit Card Holder",
        "Last Name of the Credit Card Holder",
        "Credit Card Issuer Code",
        "Masked Credit Card Number",
        "Credit Card Authorization Request Identifier",
        "Credit Card Voice Authorization Code",
        "Receivables Transaction Region Information Flexfield Number Segment 1",
        "Receivables Transaction Region Information Flexfield Number Segment 2",
        "Receivables Transaction Region Information Flexfield Number Segment 3",
        "Receivables Transaction Region Information Flexfield Number Segment 4",
        "Receivables Transaction Region Information Flexfield Number Segment 5",
        "Receivables Transaction Region Information Flexfield Number Segment 6",
        "Receivables Transaction Region Information Flexfield Number Segment 7",
        "Receivables Transaction Region Information Flexfield Number Segment 8",
        "Receivables Transaction Region Information Flexfield Number Segment 9",
        "Receivables Transaction Region Information Flexfield Number Segment 10",
        "Receivables Transaction Region Information Flexfield Number Segment 11",
        "Receivables Transaction Region Information Flexfield Number Segment 12",
        "Receivables Transaction Region Information Flexfield Date Segment 1",
        "Receivables Transaction Region Information Flexfield Date Segment 2",
        "Receivables Transaction Region Information Flexfield Date Segment 3",
        "Receivables Transaction Region Information Flexfield Date Segment 4",
        "Receivables Transaction Region Information Flexfield Date Segment 5",
        "Receivables Transaction Line Region Information Flexfield Number Segment 1",
        "Receivables Transaction Line Region Information Flexfield Number Segment 2",
        "Receivables Transaction Line Region Information Flexfield Number Segment 3",
        "Receivables Transaction Line Region Information Flexfield Number Segment 4",
        "Receivables Transaction Line Region Information Flexfield Number Segment 5",
        "Receivables Transaction Line Region Information Flexfield Date Segment 1",
        "Receivables Transaction Line Region Information Flexfield Date Segment 2",
        "Receivables Transaction Line Region Information Flexfield Date Segment 3",
        "Receivables Transaction Line Region Information Flexfield Date Segment 4",
        "Receivables Transaction Line Region Information Flexfield Date Segment 5",
        "Freight Charge",
        "Insurance Charge",
        "Packing Charge",
        "Miscellaneous Charge",
        "Commercial Discount",
        "Enforce Chronological Document Sequencing",
        "Payments transaction identifier",
        "Interface Status",
        "Invoice Lines Flexfield Number Segment 1",
        "Invoice Lines Flexfield Number Segment 2",
        "Invoice Lines Flexfield Number Segment 3",
        "Invoice Lines Flexfield Number Segment 4",
        "Invoice Lines Flexfield Number Segment 5",
        "Invoice Lines Flexfield Date Segment 1",
        "Invoice Lines Flexfield Date Segment 2",
        "Invoice Lines Flexfield Date Segment 3",
        "Invoice Lines Flexfield Date Segment 4",
        "Invoice Lines Flexfield Date Segment 5",
        "Invoice Transactions Flexfield Number Segment 1",
        "Invoice Transactions Flexfield Number Segment 2",
        "Invoice Transactions Flexfield Number Segment 3",
        "Invoice Transactions Flexfield Number Segment 4",
        "Invoice Transactions Flexfield Number Segment 5",
        "Invoice Transactions Flexfield Date Segment 1",
        "Invoice Transactions Flexfield Date Segment 2",
        "Invoice Transactions Flexfield Date Segment 3",
        "Invoice Transactions Flexfield Date Segment 4",
        "Invoice Transactions Flexfield Date Segment 5",
        "ADDITIONAL_LINE_CONTEXT",
        "ADDITIONAL_LINE_ATTRIBUTE1",
        "ADDITIONAL_LINE_ATTRIBUTE2",
        "ADDITIONAL_LINE_ATTRIBUTE3",
        "ADDITIONAL_LINE_ATTRIBUTE4",
        "ADDITIONAL_LINE_ATTRIBUTE5",
        "ADDITIONAL_LINE_ATTRIBUTE6",
        "ADDITIONAL_LINE_ATTRIBUTE7",
        "ADDITIONAL_LINE_ATTRIBUTE8",
        "ADDITIONAL_LINE_ATTRIBUTE9",
        "ADDITIONAL_LINE_ATTRIBUTE10",
        "ADDITIONAL_LINE_ATTRIBUTE11",
        "ADDITIONAL_LINE_ATTRIBUTE12",
        "ADDITIONAL_LINE_ATTRIBUTE13",
        "ADDITIONAL_LINE_ATTRIBUTE14",
        "ADDITIONAL_LINE_ATTRIBUTE15",
        "END",
    ]


# ============================================================================
# HELPER UTILITIES
# ============================================================================

def _generate_run_prefix(length: int = 8) -> str:
    """Generate a unique numeric run prefix to avoid cross-run conflicts."""
    return ''.join(random.choices(string.digits, k=length))


def safe_str(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    return str(val).strip()


def clean_order_ref(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    s = str(val).strip()
    s = s.replace("\ufeff", "").replace("\u200b", "").replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if s.endswith(".0") and s[:-2].replace("/", "").replace("-", "").isalnum():
        s = s[:-2]
    return s


def normalise_col_name(name: str) -> str:
    name = name.replace("\ufeff", "").replace("\u200b", "").replace("\u00a0", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return name


def normalise_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [normalise_col_name(c) for c in df.columns]
    return df


def normalise_store(name: str) -> str:
    return name.upper().strip()


def barcode_to_text(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    raw = str(val).strip()
    if "e" in raw.lower():
        try:
            raw = str(int(float(raw)))
        except (ValueError, OverflowError):
            pass
    if raw.endswith(".0"):
        raw = raw[:-2]
    return raw


def safe_float(val, default: float = 0.0) -> float:
    if val is None:
        return default
    if isinstance(val, float):
        return default if np.isnan(val) else val
    if isinstance(val, (int, np.integer)):
        return float(val)
    if isinstance(val, np.floating):
        return default if np.isnan(float(val)) else float(val)
    s = str(val).strip()
    if not s or s in ("nan", "NaN", "None", ""):
        return default
    try:
        return float(s)
    except (TypeError, ValueError):
        return default


def format_datetime(dt) -> str:
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(dt, pd.Timestamp):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(dt)


def format_date(dt) -> str:
    if isinstance(dt, (datetime, pd.Timestamp)):
        return dt.strftime("%Y-%m-%d")
    return str(dt)[:10]


def normalise_payment(raw: str) -> str:
    key = raw.upper().strip()
    if key in PAYMENT_METHOD_NORM:
        return PAYMENT_METHOD_NORM[key]
    if "MADA"   in key: return "Mada"
    if "VISA"   in key: return "Visa"
    if "MASTER" in key or key.startswith("MC"): return "MasterCard"
    if "CASH"   in key: return "Cash"
    if "TAMARA" in key: return "TAMARA"
    if "TABBY"  in key: return "TABBY"
    if "APPLE"  in key: return "Apple Pay"
    if "STC"    in key: return "STC Pay"
    return raw.strip()


def is_discount_line(product_name: str) -> bool:
    if not product_name:
        return False
    lower = product_name.lower()
    return any(k in lower for k in ("discount", "100.0% discount", "100% discount"))


def safe_filename(text: str) -> str:
    return re.sub(r"[^A-Z0-9_]", "", text.upper().replace(" ", "_"))


def find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    norm_map = {normalise_col_name(c): c for c in df.columns}
    for cand in candidates:
        norm_cand = normalise_col_name(cand)
        if norm_cand in norm_map:
            return norm_map[norm_cand]
    return None


# ============================================================================
# COLUMN MAPS
# ============================================================================

LINE_ITEMS_COL_MAP = {
    "Order Ref": [
        "Order Lines/Order Ref",
        "Order Ref",
    ],
    "Barcode": [
        "Order Lines/Product/Barcode",
        "Barcode",
        "Product/Barcode",
    ],
    "Product Name": [
        "Order Lines/Product/Name",
        "Order Lines/Product Name",
        "Product/Name",
        "Product Name",
    ],
    "Quantity": [
        "Order Lines/Base Quantity",
        "Order Lines/Quantity",
        "Base Quantity",
        "Quantity",
    ],
    "Subtotal w/o Tax": [
        "Order Lines/Subtotal w/o Tax",
        "Order Lines/Subtotal excl tax",
        "Order Lines/Price excl. tax",
        "Order Lines/Subtotal",
        "Subtotal w/o Tax",
        "Subtotal",
    ],
    "Sale Date": [
        "Order Lines/Order Ref/Date",
        "Order Lines/Date",
        "Sale Date",
        "Date",
    ],
    "Store Name": [
        "Order Lines/Register Name",
        "Register Name",
        "Store Name",
    ],
    "Unit of Measure": [
        "Order Lines/Base UoM",
        "Order Lines/Unit of Measure",
        "Order Lines/UoM",
        "Unit of Measure",
        "UoM",
        "UOM",
    ],
}

PAYMENTS_COL_MAP = {
    "Order Ref": [
        "Order Ref",
        "Payments/Order Ref",
    ],
    "Payment Method": [
        "Payments/Payment Method",
        "Payment Method",
    ],
    "Amount": [
        "Payments/Amount",
        "Amount",
    ],
}


# ============================================================================
# INVOICE SEQUENCE MANAGER
# ============================================================================

class InvoiceSequenceManager:
    """Manage invoice sequence numbers with persistence"""
    
    def __init__(self, sequence_file: str = "invoice_sequence.json"):
        self.sequence_file = Path(sequence_file)
        self.data = self._load()
    
    def _load(self) -> dict:
        """Load sequence data from file"""
        if self.sequence_file.exists():
            try:
                with open(self.sequence_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                print(f"  ✓ Loaded invoice sequence: BLKU-{data.get('last_transaction_number', 0):07d}")
                return data
            except Exception as e:
                print(f"  ⚠ Error loading sequence file: {e} — starting fresh")
        
        return {
            "last_transaction_number": 0,
            "last_segment_1": 0,
            "last_segment_2": 0,
            "last_updated": "",
            "notes": "Auto-generated invoice sequence tracking"
        }
    
    def get_next_transaction_number(self) -> int:
        """Get the next transaction number to use"""
        return self.data["last_transaction_number"] + 1
    
    def get_next_segment_1(self) -> int:
        """Get the next segment 1 value"""
        return self.data["last_segment_1"] + 1
    
    def get_next_segment_2(self) -> int:
        """Get the next segment 2 value"""
        return self.data["last_segment_2"] + 1
    
    def update(self, transaction_number: int, segment_1: int, segment_2: int):
        """Update sequence numbers and persist to file"""
        self.data["last_transaction_number"] = transaction_number
        self.data["last_segment_1"] = segment_1
        self.data["last_segment_2"] = segment_2
        self.data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save()
    
    def _save(self):
        """Save sequence data to file"""
        try:
            with open(self.sequence_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            print(f"  ✓ Invoice sequence saved: BLKU-{self.data['last_transaction_number']:07d}")
        except Exception as e:
            print(f"  ⚠ Error saving sequence file: {e}")


# ============================================================================
# VERIFICATION LOGGER
# ============================================================================

class VerificationLog:
    
    # Display width constants for summary formatting
    MAX_LABEL_WIDTH = 40
    MAX_VALUE_WIDTH = 20
    TRUNCATE_SUFFIX = "..."
    
    # Keywords for identifying major sections that need enhanced formatting
    MAJOR_SECTION_KEYWORDS = [
        "FINAL CROSS-CHECK", "VERIFICATION", "VALIDATION", 
        "SUMMARY", "MAJOR VERIFICATION POINTS"
    ]

    def __init__(self):
        self.run_ts    = datetime.now()
        self.sections: List[Tuple[str, List[str]]] = []
        self._current: Optional[Tuple[str, List[str]]] = None
        self._summary_items: List[Tuple[str, str, str]] = []  # (label, value, status)

    def section(self, title: str):
        self._flush()
        self._current = (title, [])

    def _flush(self):
        if self._current:
            self.sections.append(self._current)
        self._current = None

    def add(self, line: str = ""):
        if self._current is None:
            self._current = ("GENERAL", [])
        self._current[1].append(line)

    def close(self):
        self._flush()

    def kv(self, label: str, value, width: int = 40):
        self.add(f"  {label:<{width}} {value}")
    
    def add_summary(self, label: str, value: str, status: str = "INFO"):
        """Add item to verification summary (status: PASS, FAIL, WARN, INFO)"""
        self._summary_items.append((label, value, status))

    def table_row(self, *cols, widths=(30, 12, 12, 12, 20)):
        parts = [f"{str(c):<{w}}" for c, w in zip(cols, widths)]
        self.add("  " + "  ".join(parts))

    def divider(self, char: str = "-", width: int = 70):
        self.add("  " + char * width)
    
    def highlight_box(self, title: str, items: List[Tuple[str, str]], box_char: str = "█"):
        """Add a highlighted box for important information"""
        self.add()
        self.add(f"  {box_char * 70}")
        self.add(f"  {box_char}  {title.upper():<64}  {box_char}")
        self.add(f"  {box_char * 70}")
        for label, value in items:
            self.add(f"  {box_char}  {label:<40} {value:<21}  {box_char}")
        self.add(f"  {box_char * 70}")
        self.add()

    def write(self, path: Path):
        with open(path, "w", encoding="utf-8") as f:
            # Header
            f.write("=" * 72 + "\n")
            f.write("  ORACLE FUSION INTEGRATION — VERIFICATION REPORT\n")
            f.write(f"  Generated : {self.run_ts.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 72 + "\n\n")
            
            # Executive Summary Section (if we have summary items)
            if self._summary_items:
                f.write("╔" + "═" * 70 + "╗\n")
                f.write("║" + " " * 18 + "VERIFICATION SUMMARY" + " " * 32 + "║\n")
                f.write("╠" + "═" * 70 + "╣\n")
                
                pass_count = sum(1 for _, _, s in self._summary_items if s == "PASS")
                fail_count = sum(1 for _, _, s in self._summary_items if s == "FAIL")
                warn_count = sum(1 for _, _, s in self._summary_items if s == "WARN")
                
                overall_status = "✓ ALL CHECKS PASSED" if fail_count == 0 else "⚠ ISSUES DETECTED"
                f.write(f"║  Overall Status: {overall_status:<51}║\n")
                f.write(f"║  Passed: {pass_count:<3}  |  Failed: {fail_count:<3}  |  Warnings: {warn_count:<3}{' ' * 26}║\n")
                f.write("╠" + "═" * 70 + "╣\n")
                
                for label, value, status in self._summary_items:
                    icon = {"PASS": "✓", "FAIL": "✗", "WARN": "⚠", "INFO": "ℹ"}.get(status, "•")
                    # Truncate to fit in display width using class constants
                    # Take first (MAX_WIDTH - len(SUFFIX)) chars and add SUFFIX to make exactly MAX_WIDTH chars total
                    suffix_len = len(self.TRUNCATE_SUFFIX)
                    label_truncated = (label[:self.MAX_LABEL_WIDTH - suffix_len] + self.TRUNCATE_SUFFIX) if len(label) > self.MAX_LABEL_WIDTH else label
                    value_truncated = (value[:self.MAX_VALUE_WIDTH - suffix_len] + self.TRUNCATE_SUFFIX) if len(value) > self.MAX_VALUE_WIDTH else value
                    f.write(f"║  {icon} {label_truncated:<{self.MAX_LABEL_WIDTH}} {value_truncated:<{self.MAX_VALUE_WIDTH}} ║\n")
                
                f.write("╚" + "═" * 70 + "╝\n\n")
            
            # Detailed Sections
            for title, lines in self.sections:
                # Highlight major verification sections using class constant
                is_major = any(kw in title.upper() for kw in self.MAJOR_SECTION_KEYWORDS)
                
                if is_major:
                    f.write("╔" + "═" * 70 + "╗\n")
                    f.write(f"║  {title:<67} ║\n")
                    f.write("╚" + "═" * 70 + "╝\n")
                else:
                    f.write(f"{'─'*72}\n")
                    f.write(f"  {title}\n")
                    f.write(f"{'─'*72}\n")
                
                for line in lines:
                    f.write(line + "\n")
                f.write("\n")
        print(f"  ✓ Verification report : {path}")

    def print_summary(self):
        print("\n" + "=" * 72)
        print("  VERIFICATION SUMMARY")
        print("=" * 72)
        for title, lines in self.sections:
            if any(kw in title.upper() for kw in
                   ("INPUT", "INVOICE", "AR RECORD", "RECEIPT", "METADATA",
                    "PAYMENT", "ANOMAL", "FINAL", "SEQUENCE", "COLUMN", "MISC")):
                print(f"\n  ── {title}")
                for line in lines[:40]:
                    print(line)
                if len(lines) > 40:
                    print(f"       ... {len(lines)-40} more lines in report file")
        print("=" * 72 + "\n")


# ============================================================================
# RECEIPT METHODS CACHE
# ============================================================================

class ReceiptMethodsCache:

    def __init__(self, path: str):
        self._exact:  Dict[Tuple[str, str], Tuple[str, str]] = {}
        self._method: Dict[str, Tuple[str, str]]             = {}
        self._loaded  = False
        if path and Path(path).exists():
            self._load(path)

    def _load(self, path: str):
        df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
        df = normalise_dataframe_columns(df)

        required = {"RECEIPT_METHOD_NAME", "BANK_ACCOUNT_NAME", "BANK_ACCOUNT_NUMBER"}
        if not required.issubset(set(df.columns)):
            print(f"  ⚠ Receipt_Methods.csv missing columns "
                  f"{required - set(df.columns)} — using fallback")
            return

        for _, row in df.iterrows():
            method      = safe_str(row.get("RECEIPT_METHOD_NAME")).strip()
            acct_name   = safe_str(row.get("BANK_ACCOUNT_NAME")).strip()
            acct_number = safe_str(row.get("BANK_ACCOUNT_NUMBER")).strip()
            if not method or not acct_name:
                continue
            canonical  = normalise_payment(method)
            acct_upper = acct_name.upper()
            key        = (acct_upper, canonical)
            if key not in self._exact:
                self._exact[key] = (acct_name, acct_number)
            if canonical not in self._method:
                self._method[canonical] = (acct_name, acct_number)

        self._loaded = True
        print(f"  ✓ Receipt_Methods.csv loaded: {len(self._exact):,} entries")

    def get_bank_account(self, store_name: str, method: str) -> Tuple[str, str]:
        if not self._loaded:
            return PAYMENT_BANK_MAP_FALLBACK.get(method, DEFAULT_BANK)
        store_upper = normalise_store(store_name)
        for (acct_upper, canon_method), (acct_name, acct_number) in self._exact.items():
            if canon_method == method and store_upper in acct_upper:
                return (acct_name, acct_number)
        if method in self._method:
            return self._method[method]
        return PAYMENT_BANK_MAP_FALLBACK.get(method, DEFAULT_BANK)


# ============================================================================
# BANK CHARGES CACHE
# ============================================================================

class BankChargesCache:

    DEFAULT_VAT_RATE = 0.15

    def __init__(self, path: Optional[str] = None):
        self._store_method: Dict[Tuple[str, str], dict] = {}
        self._method_only:  Dict[str, dict]             = {}
        self._loaded = False
        if path and Path(path).exists():
            self._load(path)

    def _load(self, path: str):
        df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
        df = normalise_dataframe_columns(df)
        df.columns = df.columns.str.upper()

        method_col   = next((c for c in df.columns if "METHOD" in c), None)
        store_col    = next((c for c in df.columns if "STORE" in c or "SUBINV" in c), None)
        rate_col     = next((c for c in df.columns
                             if ("CHARGE" in c and "RATE" in c) or c == "RATE"), None)
        vat_col      = next((c for c in df.columns if "VAT" in c or "TAX_RATE" in c), None)
        cap_col      = next((c for c in df.columns if "CAP" in c or "MAX" in c), None)
        activity_col = next((c for c in df.columns if "ACTIVITY" in c), None)
        mid_col      = next((c for c in df.columns if "METHOD_ID" in c), None)
        org_col      = next((c for c in df.columns if "ORG" in c), None)

        if method_col is None or rate_col is None:
            print("  ⚠ Bank_Charges.csv: cannot find METHOD or RATE column.")
            return

        for _, row in df.iterrows():
            method_raw = safe_str(row.get(method_col, ""))
            if not method_raw:
                continue
            method_norm = normalise_payment(method_raw)
            method_key  = method_norm.upper()

            rate     = safe_float(row.get(rate_col, 0))
            vat      = (safe_float(row.get(vat_col, self.DEFAULT_VAT_RATE))
                        if vat_col else self.DEFAULT_VAT_RATE)
            cap      = safe_float(row.get(cap_col, 0))      if cap_col      else 0.0
            activity = (safe_str(row.get(activity_col, "Misc Activity"))
                        if activity_col else "Misc Activity")
            mid      = safe_str(row.get(mid_col, ""))       if mid_col      else ""
            org_id   = safe_str(row.get(org_col, ""))       if org_col      else ""

            entry = {
                "rate":      rate,
                "vat":       vat,
                "cap":       cap,
                "activity":  activity or "Misc Activity",
                "method_id": mid,
                "org_id":    org_id,
                "method":    method_norm,
            }

            if store_col and safe_str(row.get(store_col, "")):
                store_key = normalise_store(safe_str(row.get(store_col, "")))
                self._store_method[(method_key, store_key)] = entry
            else:
                if method_key not in self._method_only:
                    self._method_only[method_key] = entry

        self._loaded = True
        print(f"  ✓ Bank_Charges.csv loaded: "
              f"{len(self._store_method)} store + {len(self._method_only)} method entries")

    def get(self, method: str, store: str = "") -> Optional[dict]:
        if not self._loaded:
            return None
        method_key = method.upper()
        store_key  = normalise_store(store)
        return (self._store_method.get((method_key, store_key))
                or self._method_only.get(method_key))

    def calc_misc_amount(self, payment_amount: float, method: str,
                         store: str = "") -> Optional[float]:
        cfg = self.get(method, store)
        if cfg is None or cfg["rate"] == 0:
            return None
        temp1        = payment_amount * cfg["rate"]
        temp2        = 1.0 + cfg["vat"]
        misc_charges = temp1 * temp2
        if cfg["cap"] > 0 and misc_charges > cfg["cap"]:
            misc_charges = cfg["cap"]
        return round(0.0 - misc_charges, 4)


# ============================================================================
# METADATA LOADER
# ============================================================================

class MetadataCache:

    _SITE_COL_ALIASES = ("BILL_TO_SITE_NUMBER", "SITE_NUMBER",
                          "Address_SITE_NUMBER", "ADDRESS_SITE_NUMBER")

    def __init__(self, metadata_path: str):
        self.path            = metadata_path
        self.primary:        Dict[Tuple[str, str], dict] = {}
        self.by_type:        Dict[str, dict]             = {}
        self._site_col_used: str                         = ""
        self._load()

    def _load(self):
        df = pd.read_csv(self.path, encoding="utf-8-sig", dtype=str)
        df = normalise_dataframe_columns(df)

        site_col_found = None
        for alias in self._SITE_COL_ALIASES:
            if alias in df.columns:
                site_col_found = alias
                break

        if site_col_found is None:
            raise ValueError(
                f"Metadata CSV missing site-number column. "
                f"Expected one of: {self._SITE_COL_ALIASES}. "
                f"Available: {list(df.columns)}"
            )

        if site_col_found != "SITE_NUMBER":
            df.rename(columns={site_col_found: "SITE_NUMBER"}, inplace=True)
        self._site_col_used = site_col_found

        required = {"SUBINVENTORY", "CUSTOMER_TYPE", "BILL_TO_ACCOUNT",
                    "SITE_NUMBER", "BILL_TO_NAME", "BUSINESS_UNIT"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Metadata CSV missing columns: {missing}")

        for _, row in df.iterrows():
            subinv = safe_str(row.get("SUBINVENTORY")).upper()
            ctype  = safe_str(row.get("CUSTOMER_TYPE")).upper()
            if not subinv or not ctype:
                continue
            entry = {
                "BILL_TO_ACCOUNT":  safe_str(row.get("BILL_TO_ACCOUNT")),
                "SITE_NUMBER":      safe_str(row.get("SITE_NUMBER")),
                "BILL_TO_NAME":     safe_str(row.get("BILL_TO_NAME")),
                "BUSINESS_UNIT":    safe_str(row.get("BUSINESS_UNIT", "AlQurashi-KSA")),
                "CUSTOMER_TYPE":    safe_str(row.get("CUSTOMER_TYPE")),
                "SUBINVENTORY":     safe_str(row.get("SUBINVENTORY")),
                "REGION":           safe_str(row.get("REGION", "SA")),
                "COST_CENTER_CODE": safe_str(row.get("COST_CENTER_CODE", "")),
            }
            self.primary[(subinv, ctype)] = entry
            if ctype not in self.by_type:
                self.by_type[ctype] = entry

    def get(self, store_name: str, customer_type: str) -> Tuple[dict, str]:
        subinv = normalise_store(store_name)
        ctype  = customer_type.upper().strip()

        row = self.primary.get((subinv, ctype))
        if row:
            return row, "exact"

        for (s, t), v in self.primary.items():
            if t == ctype and (subinv.startswith(s) or s.startswith(subinv)):
                return v, "partial"

        row = self.by_type.get(ctype)
        if row:
            return row, "type_only"

        return {
            "BILL_TO_ACCOUNT": "", "SITE_NUMBER": "",
            "BILL_TO_NAME": store_name, "BUSINESS_UNIT": "AlQurashi-KSA",
            "CUSTOMER_TYPE": customer_type, "SUBINVENTORY": store_name,
            "REGION": "SA", "COST_CENTER_CODE": "",
        }, "none"


# ============================================================================
# REGISTER CACHE
# ============================================================================

class RegisterCache:

    def __init__(self, registers_path: str = ""):
        self.name_map: Dict[str, str] = {}
        if registers_path and Path(registers_path).exists():
            self._load(registers_path)
        elif registers_path:
            print(f"  ⚠ Registers file not found: {registers_path} — register name mapping skipped")
        else:
            print("  ℹ No registers file provided — register name mapping skipped")

    def _load(self, path: str):
        df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
        df = normalise_dataframe_columns(df)
        reg_col = next((c for c in df.columns if "REGISTER_NAME" in c.upper()), None)
        if reg_col is None:
            return
        for _, row in df.iterrows():
            reg = safe_str(row.get(reg_col))
            if reg:
                self.name_map[reg.upper()] = reg

    def resolve(self, raw_name: str) -> str:
        return self.name_map.get(normalise_store(raw_name), raw_name)


# ============================================================================
# TRANSACTION NUMBER GENERATOR
# ============================================================================

class TxnNumberGenerator:

    def __init__(self, start_seq: int = 1):
        self._start         = max(1, int(start_seq))
        self._normal_cache: Dict[Tuple[str, str], str]      = {}
        self._normal_seq    = self._start
        self._bnpl_cache:   Dict[Tuple[str, str, str], str] = {}
        self._bnpl_seq      = self._start

    def get_normal(self, store_name: str, sale_date) -> str:
        ds  = format_date(sale_date)
        key = (store_name.upper().strip(), ds)
        if key not in self._normal_cache:
            self._normal_cache[key] = f"BLKU-{self._normal_seq:07d}"
            self._normal_seq += 1
        return self._normal_cache[key]

    def get_bnpl(self, store_name: str, sale_date, customer_type: str) -> str:
        ds  = format_date(sale_date)
        ct  = customer_type.upper()
        key = (store_name.upper().strip(), ds, ct)
        if key not in self._bnpl_cache:
            self._bnpl_cache[key] = f"BLKU-{self._bnpl_seq:04d}"
            self._bnpl_seq += 1
        return self._bnpl_cache[key]

    def get(self, store_name: str, sale_date, customer_type: str) -> str:
        if customer_type.upper() in NO_RECEIPT_PAYMENT_METHODS:
            return self.get_bnpl(store_name, sale_date, customer_type)
        return self.get_normal(store_name, sale_date)


# ============================================================================
# MAIN INTEGRATION CLASS
# ============================================================================

class OracleFusionIntegration:

    AR_COLUMNS = get_ar_columns()

    def __init__(
        self,
        output_dir:         str = "ORACLE_FUSION_OUTPUT",
        start_seq:          int = 1,
        start_legacy_seq_1: int = 1,
        start_legacy_seq_2: int = 1,
        use_sequence_manager: bool = False,
    ):
        self.output_dir         = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Invoice sequence manager for auto-incrementing
        self.seq_manager = None
        if use_sequence_manager:
            self.seq_manager = InvoiceSequenceManager()
            # Override start sequences with saved values
            if start_seq == 1:  # Only use saved if not explicitly provided
                start_seq = self.seq_manager.get_next_transaction_number()
            if start_legacy_seq_1 == 1:
                start_legacy_seq_1 = self.seq_manager.get_next_segment_1()
            if start_legacy_seq_2 == 1:
                start_legacy_seq_2 = self.seq_manager.get_next_segment_2()

        self.start_seq          = max(1, int(start_seq))
        self.start_legacy_seq_1 = max(1, int(start_legacy_seq_1))
        self.start_legacy_seq_2 = max(1, int(start_legacy_seq_2))

        self.txn_gen            = TxnNumberGenerator(start_seq=self.start_seq)
        self.vlog               = VerificationLog()

        self.segment_seq_1      = self.start_legacy_seq_1
        self.segment_seq_2      = self.start_legacy_seq_2

        # ── Random alphanumeric prefix per run — no cross-run conflicts ──
        self._seg1_prefix       = _generate_run_prefix(8)
        self._seg2_prefix       = _generate_run_prefix(8)

        self.metadata_cache:    Optional[MetadataCache]       = None
        self.register_cache:    Optional[RegisterCache]       = None
        self.receipt_methods:   Optional[ReceiptMethodsCache] = None
        self.bank_charges:      Optional[BankChargesCache]    = None

        self.line_items:        Optional[pd.DataFrame]        = None
        self.payments:          Optional[pd.DataFrame]        = None

        self.invoice_store:     Dict[str, str]                = {}
        self.invoice_ctype:     Dict[str, str]                = {}
        self.invoice_payments:  Dict[str, Dict[str, float]]   = defaultdict(
                                                                    lambda: defaultdict(float))
        self.invoice_to_ar_txn: Dict[str, str]                = {}
        self.invoice_date:      Dict[str, datetime]           = {}
        self.invoice_ar_total:  Dict[str, float]              = {}
        self._inv_row_index:    Dict[str, List[int]]          = {}

    # ──────────────────────────────────────────────────────────────────
    # DATA LOADING
    # ──────────────────────────────────────────────────────────────────

    def load_data(
        self,
        line_items_path:      str,
        payments_path:        str,
        metadata_path:        str,
        registers_path:       str = "",
        receipt_methods_path: str = "",
        bank_charges_path:    str = "",
    ):
        vl = self.vlog
        vl.section("1. INPUT FILES & SEQUENCE SETTINGS")

        vl.kv("Transaction number start seq",  str(self.start_seq))
        vl.kv("  NORMAL  first number",        f"BLKU-{self.start_seq:07d}")
        vl.kv("  TABBY   first number",        f"BLKU-{self.start_seq:04d}")
        vl.kv("  TAMARA  first number",        f"BLKU-{self.start_seq:04d}")
        vl.kv("Segment 1 prefix (this run)",   self._seg1_prefix)
        vl.kv("Segment 2 prefix (this run)",   self._seg2_prefix)
        vl.kv("LEGACY Segment 1 start seq",    str(self.start_legacy_seq_1))
        vl.kv("LEGACY Segment 2 start seq",    str(self.start_legacy_seq_2))
        vl.add()

        self.metadata_cache  = MetadataCache(metadata_path)
        self.register_cache  = RegisterCache(registers_path)
        self.receipt_methods = ReceiptMethodsCache(receipt_methods_path)
        self.bank_charges    = BankChargesCache(bank_charges_path)

        vl.kv("Metadata file",              Path(metadata_path).name)
        vl.kv("Site column used",           self.metadata_cache._site_col_used)
        vl.kv("(store, type) pairs loaded", len(self.metadata_cache.primary))

        # ── LINE ITEMS ────────────────────────────────────────────────
        self.line_items = self._read_file(line_items_path)
        raw_line_count  = len(self.line_items)
        vl.add()
        vl.kv("Line items file",  Path(line_items_path).name)
        vl.kv("Raw rows read",    raw_line_count)

        vl.section("1b. LINE ITEMS — COLUMN DIAGNOSTIC")
        vl.add("  Raw column names (after BOM/space normalisation):")
        for col in self.line_items.columns:
            vl.add(f"    [{col}]")

        self._normalise_line_items()

        vl.section("1. INPUT FILES & SEQUENCE SETTINGS")
        vl.kv("Rows after cleaning",            len(self.line_items))
        vl.kv("Rows dropped (blank Order Ref)", raw_line_count - len(self.line_items))
        vl.kv("Unique invoices",                len(self.invoice_store))

        # ── PAYMENTS ──────────────────────────────────────────────────
        self.payments = self._read_file(payments_path)
        vl.kv("Payments file",     Path(payments_path).name)
        vl.kv("Raw payment rows",  len(self.payments))

        vl.section("1c. PAYMENTS — COLUMN DIAGNOSTIC")
        vl.add("  Raw column names detected:")
        for col in self.payments.columns:
            vl.add(f"    [{col}]")

        self._normalise_payments()

        vl.section("2. PAYMENT METHOD BREAKDOWN")
        method_counts:  Dict[str, int]   = defaultdict(int)
        method_amounts: Dict[str, float] = defaultdict(float)
        for inv_methods in self.invoice_payments.values():
            for m, amt in inv_methods.items():
                method_counts[m]  += 1
                method_amounts[m] += amt

        vl.table_row("Payment Method", "Invoices", "Total Amount (SAR)",
                     widths=(25, 12, 22))
        vl.divider()
        for m in sorted(method_counts.keys()):
            vl.table_row(m, method_counts[m],
                         f"{method_amounts[m]:,.2f}", widths=(25, 12, 22))
        vl.divider()
        vl.table_row("TOTAL",
                     sum(method_counts.values()),
                     f"{sum(method_amounts.values()):,.2f}",
                     widths=(25, 12, 22))

        vl.section("3. INVOICE TYPE BREAKDOWN")
        type_counts: Dict[str, int] = defaultdict(int)
        for ct in self.invoice_ctype.values():
            type_counts[ct] += 1
        for ct, cnt in sorted(type_counts.items()):
            vl.kv(ct, f"{cnt:,} invoices")
        vl.kv("Total unique invoices", f"{len(self.invoice_ctype):,}")

    # ──────────────────────────────────────────────────────────────────

    def _read_file(self, path: str) -> pd.DataFrame:
        p = path.lower()
        if p.endswith(".xlsx") or p.endswith(".xls"):
            df = pd.read_excel(path, dtype=None)
        else:
            df = pd.read_csv(path, encoding="utf-8-sig", dtype=None)
        return normalise_dataframe_columns(df)

    def _resolve_columns(
        self,
        df: pd.DataFrame,
        col_map: Dict[str, List[str]],
        file_label: str,
        vl: VerificationLog,
    ) -> Dict[str, Optional[str]]:
        resolved: Dict[str, Optional[str]] = {}
        vl.section(f"COLUMN RESOLUTION — {file_label}")
        for logical, candidates in col_map.items():
            actual = find_col(df, candidates)
            resolved[logical] = actual
            if actual:
                vl.add(f"  ✓ {logical:<25} → [{actual}]")
            else:
                vl.add(f"  ✗ {logical:<25} → NOT FOUND  (tried: {candidates})")
        return resolved

    def _normalise_line_items(self):
        vl  = self.vlog
        res = self._resolve_columns(self.line_items, LINE_ITEMS_COL_MAP,
                                    "LINE ITEMS", vl)

        for req in ("Order Ref", "Product Name", "Quantity",
                    "Subtotal w/o Tax", "Sale Date"):
            if res[req] is None:
                raise ValueError(
                    f"Line items file: required column '{req}' not found.\n"
                    f"Tried: {LINE_ITEMS_COL_MAP[req]}\n"
                    f"Actual columns: {list(self.line_items.columns)}"
                )

        rename_map = {v: k for k, v in res.items() if v is not None and v != k}
        if rename_map:
            self.line_items.rename(columns=rename_map, inplace=True)

        self.line_items["Order Ref"] = (
            self.line_items["Order Ref"].apply(clean_order_ref)
        )

        self.line_items["Sale Date"] = pd.to_datetime(
            self.line_items["Sale Date"], errors="coerce"
        )

        if res.get("Store Name") is None:
            self.line_items["Store Name"] = self.line_items["Order Ref"].apply(
                lambda x: x.split("/")[0] if "/" in x else x
            )

        if "Barcode" in self.line_items.columns:
            self.line_items["Barcode"] = (
                self.line_items["Barcode"].apply(barcode_to_text)
            )

        self.line_items = self.line_items[
            self.line_items["Order Ref"] != ""
        ].reset_index(drop=True)

        self._inv_row_index = defaultdict(list)
        for pos, inv in enumerate(self.line_items["Order Ref"]):
            self._inv_row_index[inv].append(pos)

        vl.section("1d. LINE ITEMS — QUANTITY & AMOUNT DIAGNOSTIC")
        vl.add(f"  Quantity column dtype : {self.line_items['Quantity'].dtype}")
        vl.add(f"  Amount   column dtype : {self.line_items['Subtotal w/o Tax'].dtype}")
        vl.add("  Sample Quantity values (first 10):")
        for v in self.line_items["Quantity"].head(10).tolist():
            vl.add(f"    repr={repr(v)}  safe_float={safe_float(v)}")
        vl.add("  Sample Amount values (first 10):")
        for v in self.line_items["Subtotal w/o Tax"].head(10).tolist():
            vl.add(f"    repr={repr(v)}  safe_float={safe_float(v)}")

        for pos, row in self.line_items.iterrows():
            inv   = row["Order Ref"]
            store = safe_str(row.get("Store Name", ""))
            dt    = row["Sale Date"]
            if inv and inv not in self.invoice_store:
                self.invoice_store[inv] = store
                self.invoice_date[inv]  = dt

    def _normalise_payments(self):
        vl  = self.vlog
        res = self._resolve_columns(self.payments, PAYMENTS_COL_MAP,
                                    "PAYMENTS", vl)

        for req in ("Order Ref", "Payment Method", "Amount"):
            if res[req] is None:
                raise ValueError(
                    f"Payments file: required column '{req}' not found.\n"
                    f"Tried: {PAYMENTS_COL_MAP[req]}\n"
                    f"Actual columns: {list(self.payments.columns)}"
                )

        rename_map = {v: k for k, v in res.items() if v is not None and v != k}
        if rename_map:
            self.payments.rename(columns=rename_map, inplace=True)

        self.payments["Order Ref"] = self.payments["Order Ref"].apply(clean_order_ref)

        for _, row in self.payments.iterrows():
            inv    = row["Order Ref"]
            method = normalise_payment(safe_str(row.get("Payment Method", "Cash")))
            amount = safe_float(row.get("Amount", 0))
            if not inv or amount == 0:
                continue
            self.invoice_payments[inv][method] += amount

        for inv, methods in self.invoice_payments.items():
            if "TAMARA" in methods:
                self.invoice_ctype[inv] = "TAMARA"
            elif "TABBY" in methods:
                self.invoice_ctype[inv] = "TABBY"
            else:
                self.invoice_ctype[inv] = "NORMAL"

        for inv in self.invoice_store:
            if inv not in self.invoice_ctype:
                self.invoice_ctype[inv] = "NORMAL"

    # ──────────────────────────────────────────────────────────────────
    # AR INVOICE GENERATION
    # ──────────────────────────────────────────────────────────────────

    def generate_ar_invoices(self) -> pd.DataFrame:
        vl = self.vlog

        self.segment_seq_1    = self.start_legacy_seq_1
        self.segment_seq_2    = self.start_legacy_seq_2
        self.invoice_ar_total = defaultdict(float)

        records              = []
        meta_exact           = 0
        meta_partial         = 0
        meta_typeonly        = 0
        meta_none            = 0
        meta_issues:         List[str] = []
        total_product_lines  = 0
        total_discount_lines = 0
        total_zero_qty_lines = 0
        total_zero_amt_lines = 0

        store_stats: Dict[str, Dict] = defaultdict(lambda: {
            "invoices": set(), "lines": 0, "discount_lines": 0,
            "amount": 0.0, "ctype": set(),
        })
        txn_registry: Dict[str, Dict] = {}

        invoices = sorted(
            self.invoice_store.keys(),
            key=lambda i: (
                format_date(self.invoice_date.get(i, datetime.min)),
                self.invoice_store.get(i, ""),
            ),
        )

        for inv in invoices:
            store     = self.invoice_store[inv]
            ctype     = self.invoice_ctype.get(inv, "NORMAL")
            sale_date = self.invoice_date.get(inv, datetime.now())
            txn_num   = self.txn_gen.get(store, sale_date, ctype)
            self.invoice_to_ar_txn[inv] = txn_num

            meta, match_type = self.metadata_cache.get(store, ctype)
            bill_to_account  = meta["BILL_TO_ACCOUNT"]
            bill_to_site     = meta["SITE_NUMBER"]

            if   match_type == "exact":     meta_exact    += 1
            elif match_type == "partial":   meta_partial  += 1
            elif match_type == "type_only": meta_typeonly += 1
            else:                           meta_none     += 1

            if match_type != "exact":
                meta_issues.append(
                    f"    Invoice {inv:<30}  store='{store}'  type='{ctype}'"
                    f"  match='{match_type}'"
                    f"  → account='{bill_to_account}'  site='{bill_to_site}'"
                )

            if txn_num not in txn_registry:
                txn_registry[txn_num] = {
                    "store": store, "date": format_date(sale_date),
                    "ctype": ctype, "invoices": 0, "lines": 0, "amount": 0.0,
                }
            txn_registry[txn_num]["invoices"] += 1

            row_positions = self._inv_row_index.get(inv, [])

            for pos in row_positions:
                item = self.line_items.iloc[pos]

                product_name = safe_str(item.get("Product Name", ""))
                barcode      = safe_str(item.get("Barcode", ""))
                uom          = safe_str(item.get("Unit of Measure", ""))

                quantity = safe_float(item.get("Quantity", 0))
                amount   = safe_float(item.get("Subtotal w/o Tax", 0))

                # ── Sign alignment: amount and quantity must share the same sign ──
                # Case 1: amount negative, quantity positive → flip quantity
                if amount < 0 and quantity > 0:
                    quantity = -quantity
                # Case 2: quantity negative, amount positive → flip amount
                elif quantity < 0 and amount > 0:
                    amount = -amount

                # ── Unit Selling Price always positive ──
                unit_price = (abs(amount) / abs(quantity)) if quantity != 0 else 0.0

                is_disc = is_discount_line(product_name)

                if is_disc: total_discount_lines += 1
                else:       total_product_lines  += 1
                if quantity == 0: total_zero_qty_lines += 1
                if amount   == 0: total_zero_amt_lines += 1

                ss = store_stats[store]
                ss["invoices"].add(inv)
                ss["lines"]   += 1
                ss["amount"]  += amount
                ss["ctype"].add(ctype)
                if is_disc: ss["discount_lines"] += 1

                txn_registry[txn_num]["lines"]  += 1
                txn_registry[txn_num]["amount"] += amount

                self.invoice_ar_total[inv] += amount

                row: Dict = {col: "" for col in self.AR_COLUMNS}

                row["Transaction Batch Source Name"]          = AR_STATIC["Transaction Batch Source Name"]
                row["Transaction Type Name"]                  = AR_STATIC["Transaction Type Name"]
                row["Payment Terms"]                          = AR_STATIC["Payment Terms"]
                row["Transaction Date"]                       = format_datetime(sale_date)
                row["Accounting Date"]                        = format_datetime(sale_date)
                row["Transaction Number"]                     = txn_num
                row["Bill-to Customer Account Number"]        = bill_to_account
                row["Bill-to Customer Site Number"]           = bill_to_site
                row["Transaction Line Type"]                  = AR_STATIC["Transaction Line Type"]
                row["Transaction Line Description"]           = (
                    "Discount Item" if (is_disc or not barcode) else product_name[:240]
                )
                row["Currency Code"]                          = AR_STATIC["Currency Code"]
                row["Currency Conversion Type"]               = AR_STATIC["Currency Conversion Type"]
                row["Currency Conversion Date"]               = format_date(sale_date)
                row["Currency Conversion Rate"]               = AR_STATIC["Currency Conversion Rate"]
                row["Transaction Line Amount"]                = round(amount, 2)
                row["Transaction Line Quantity"]              = quantity
                row["Customer Ordered Quantity"]              = ""
                row["Unit Selling Price"]                     = round(unit_price, 2)
                row["Line Transactions Flexfield Context"]    = AR_STATIC["Line Transactions Flexfield Context"]
                row["Line Transactions Flexfield Segment 1"] = f"{self._seg1_prefix}{self.segment_seq_1:06d}"
                row["Line Transactions Flexfield Segment 2"] = f"{self._seg2_prefix}{self.segment_seq_2:06d}"
                self.segment_seq_1 += 1
                self.segment_seq_2 += 1

                row["Tax Classification Code"]                = DEFAULT_TAX_CODE
                row["Sales Order Number"]                     = inv
                row["Unit of Measure Code"]                   = ""
                row["Unit of Measure Name"]                   = uom
                row["Default Taxation Country"]               = AR_STATIC["Default Taxation Country"]
                row["Comments"]                               = AR_STATIC["Comments"]
                row["END"]                                    = AR_STATIC["END"]

                # ── Inventory Item Number & Memo Line ────────────────
                # Empty barcode OR discount line → treat as discount item
                if is_disc or not barcode:
                    row["Memo Line Name"]        = "Discount Item"
                    row["Inventory Item Number"] = ""
                else:
                    row["Inventory Item Number"] = barcode

                records.append(row)

        df = pd.DataFrame(records, columns=self.AR_COLUMNS)

        # Section 4
        vl.section("4. AR INVOICE — STORE BREAKDOWN")
        vl.table_row("Store", "Invoices", "Lines", "Discount Lines", "Amount (SAR)",
                     widths=(30, 10, 8, 16, 18))
        vl.divider()
        grand_inv = grand_lines = grand_disc = 0
        grand_amt = 0.0
        for store in sorted(store_stats.keys()):
            ss = store_stats[store]
            n_inv  = len(ss["invoices"])
            n_line = ss["lines"]
            n_disc = ss["discount_lines"]
            amt    = ss["amount"]
            grand_inv += n_inv; grand_lines += n_line
            grand_disc += n_disc; grand_amt += amt
            vl.table_row(store, n_inv, n_line, n_disc,
                         f"{amt:,.2f}", widths=(30, 10, 8, 16, 18))
        vl.divider()
        vl.table_row("GRAND TOTAL", grand_inv, grand_lines, grand_disc,
                     f"{grand_amt:,.2f}", widths=(30, 10, 8, 16, 18))

        # Section 5
        vl.section("5. TRANSACTION NUMBER REGISTER")
        vl.table_row("Transaction Number", "Store", "Date",
                     "Type", "Invoices", "Lines", "Amount (SAR)",
                     widths=(18, 25, 12, 8, 10, 7, 16))
        vl.divider(width=100)
        for txn in sorted(txn_registry.keys()):
            tr = txn_registry[txn]
            vl.table_row(
                txn, tr["store"], tr["date"], tr["ctype"],
                tr["invoices"], tr["lines"], f"{tr['amount']:,.2f}",
                widths=(18, 25, 12, 8, 10, 7, 16),
            )

        # Section 6
        vl.section("6. AR RECORD STATISTICS")
        vl.kv("Total AR rows generated",    f"{len(df):,}")
        vl.kv("  Product lines",            f"{total_product_lines:,}")
        vl.kv("  Discount lines",           f"{total_discount_lines:,}")
        vl.kv("  Lines with zero quantity", f"{total_zero_qty_lines:,}")
        vl.kv("  Lines with zero amount",   f"{total_zero_amt_lines:,}")
        vl.add()
        vl.kv("Segment 1 prefix (this run)",  self._seg1_prefix)
        vl.kv("Segment 1 range",
               f"{self._seg1_prefix}{self.start_legacy_seq_1:06d} → "
               f"{self._seg1_prefix}{self.segment_seq_1 - 1:06d}")
        vl.kv("Segment 2 prefix (this run)",  self._seg2_prefix)
        vl.kv("Segment 2 range",
               f"{self._seg2_prefix}{self.start_legacy_seq_2:06d} → "
               f"{self._seg2_prefix}{self.segment_seq_2 - 1:06d}")
        vl.add()
        vl.kv("Total Transaction Line Amount",
               f"{df['Transaction Line Amount'].sum():,.2f} SAR")
        vl.kv("Unique Transaction Numbers",
               f"{df['Transaction Number'].nunique():,}")
        vl.kv("Unique Invoices",
               f"{df['Sales Order Number'].nunique():,}")
        vl.add()
        all_txn_nums = [
            int(t.replace("BLKU-", ""))
            for t in df["Transaction Number"].unique()
            if t.startswith("BLKU-") and t.replace("BLKU-", "").isdigit()
        ]
        max_txn = max(all_txn_nums) if all_txn_nums else 0
        vl.kv("Max Transaction Number used",         f"BLKU-{max_txn:07d}")
        vl.kv(">>> Next run START_TXN_SEQUENCE =",   f"{max_txn + 1}  ← set this next run")
        
        # Update sequence manager if enabled
        if self.seq_manager:
            self.seq_manager.update(max_txn, self.segment_seq_1 - 1, self.segment_seq_2 - 1)
            vl.add()
            vl.kv("✓ Invoice sequence persisted", "Ready for next run")
        
        vl.add()
        vl.kv("Rows with EMPTY Bill-to Account",
               f"{(df['Bill-to Customer Account Number'] == '').sum():,}")
        vl.kv("Rows with EMPTY Bill-to Site",
               f"{(df['Bill-to Customer Site Number'] == '').sum():,}")

        # Section 7
        vl.section("7. METADATA LOOKUP QUALITY")
        total_lu = meta_exact + meta_partial + meta_typeonly + meta_none
        vl.kv("Total invoice lookups",     f"{total_lu:,}")
        vl.kv("  Exact matches",           f"{meta_exact:,}")
        vl.kv("  Partial matches (⚠)",     f"{meta_partial:,}")
        vl.kv("  Type-only fallback (⚠⚠)", f"{meta_typeonly:,}")
        vl.kv("  No match at all   (✗✗)",  f"{meta_none:,}")
        if meta_issues:
            vl.add()
            for line in meta_issues:
                vl.add(line)

        return df

    # ──────────────────────────────────────────────────────────────────
    # STANDARD RECEIPT GENERATION
    # ──────────────────────────────────────────────────────────────────

    def generate_standard_receipts(self) -> Dict[str, pd.DataFrame]:
        vl = self.vlog

        agg_amount:    Dict[Tuple[str, str, str], float] = defaultdict(float)
        agg_inv_count: Dict[Tuple[str, str, str], int]   = defaultdict(int)
        agg_ar_txn:    Dict[Tuple[str, str], str]        = {}

        bnpl_skipped           = 0
        unknown_method_skipped = 0

        for inv, methods in self.invoice_payments.items():
            ctype = self.invoice_ctype.get(inv, "NORMAL")
            if ctype in ("TABBY", "TAMARA"):
                bnpl_skipped += 1
                continue

            store     = self.invoice_store.get(inv, "UNKNOWN")
            sale_date = self.invoice_date.get(inv, datetime.now())
            date_str  = format_date(sale_date)
            ar_txn    = self.invoice_to_ar_txn.get(inv, "")

            sd_key = (store, date_str)
            if sd_key not in agg_ar_txn and ar_txn:
                agg_ar_txn[sd_key] = ar_txn

            for method, amount in methods.items():
                if method.upper() in NO_RECEIPT_PAYMENT_METHODS:
                    continue
                if method not in RECEIPT_PAYMENT_METHODS:
                    unknown_method_skipped += 1
                    continue
                key = (store, date_str, method)
                agg_amount[key]    += amount
                agg_inv_count[key] += 1

        receipt_files:       Dict[str, pd.DataFrame] = {}
        receipt_detail_rows: List[Dict]              = []

        for (store, date_str, method), total in sorted(agg_amount.items()):
            ar_txn           = agg_ar_txn.get((store, date_str), "")
            meta, _          = self.metadata_cache.get(store, "NORMAL")
            business_unit    = meta["BUSINESS_UNIT"]
            customer_account = meta["BILL_TO_ACCOUNT"]
            customer_site    = meta["SITE_NUMBER"]

            _, bank_acct_number = self.receipt_methods.get_bank_account(store, method)

            receipt_number = (f"{method}-{ar_txn}" if ar_txn
                              else f"{method}-RCPT-{date_str}")

            safe_store_part  = safe_filename(store)
            safe_method_part = safe_filename(method)
            date_compact     = date_str.replace("-", "")
            filename         = (f"Receipt_{safe_method_part}_"
                                f"{safe_store_part}_{date_compact}.csv")

            row = {
                "ReceiptNumber":               receipt_number,
                "ReceiptMethod":               method,
                "ReceiptDate":                 date_str,
                "BusinessUnit":                business_unit,
                "CustomerAccountNumber":       customer_account,
                "CustomerSite":                customer_site,
                "Amount":                      round(total, 2),
                "Currency":                    "SAR",
                "RemittanceBankAccountNumber": bank_acct_number,
                "AccountingDate":              date_str,
            }

            receipt_files[filename] = pd.DataFrame([row],
                                                    columns=STANDARD_RECEIPT_COLUMNS)
            receipt_detail_rows.append({
                "filename":       filename,
                "store":          store,
                "date":           date_str,
                "method":         method,
                "inv_count":      agg_inv_count.get((store, date_str, method), 0),
                "amount":         total,
                "receipt_number": receipt_number,
            })

        vl.section("8. STANDARD RECEIPT RECORDS — DETAIL")
        vl.kv("BNPL invoices skipped",       f"{bnpl_skipped:,}")
        vl.kv("Unknown method rows skipped", f"{unknown_method_skipped:,}")
        vl.kv("Receipt files to write",      f"{len(receipt_files):,}")
        vl.add()
        vl.table_row("File", "# Inv", "Amount (SAR)", "Receipt Number",
                     widths=(60, 7, 16, 35))
        vl.divider(width=120)
        receipt_grand = 0.0
        for r in receipt_detail_rows:
            vl.table_row(r["filename"], r["inv_count"],
                         f"{r['amount']:,.2f}", r["receipt_number"],
                         widths=(60, 7, 16, 35))
            receipt_grand += r["amount"]
        vl.divider(width=120)
        vl.table_row("GRAND TOTAL", "", f"{receipt_grand:,.2f}", "",
                     widths=(60, 7, 16, 35))

        vl.add()
        method_totals:      Dict[str, float] = defaultdict(float)
        method_file_counts: Dict[str, int]   = defaultdict(int)
        for r in receipt_detail_rows:
            method_totals[r["method"]]      += r["amount"]
            method_file_counts[r["method"]] += 1
        vl.add("  Per-method totals:")
        for m in sorted(method_totals.keys()):
            vl.add(f"    {m:<14}  {method_file_counts[m]:>3} file(s)  "
                   f"{method_totals[m]:>14,.2f} SAR")
        vl.add(f"    {'Grand Total':<28}  {receipt_grand:>14,.2f} SAR")

        return receipt_files

    # ──────────────────────────────────────────────────────────────────
    # MISCELLANEOUS RECEIPT GENERATION
    # ──────────────────────────────────────────────────────────────────

    def generate_misc_receipts(self) -> Dict[str, pd.DataFrame]:
        vl = self.vlog

        if not self.bank_charges or not self.bank_charges._loaded:
            vl.section("8b. MISCELLANEOUS RECEIPTS")
            vl.add("  No Bank_Charges.csv loaded — misc receipts skipped.")
            return {}

        agg_amount: Dict[Tuple[str, str, str], float] = defaultdict(float)
        agg_ar_txn: Dict[Tuple[str, str], str]        = {}

        for inv, methods in self.invoice_payments.items():
            ctype = self.invoice_ctype.get(inv, "NORMAL")
            if ctype in ("TABBY", "TAMARA"):
                continue
            store     = self.invoice_store.get(inv, "UNKNOWN")
            sale_date = self.invoice_date.get(inv, datetime.now())
            date_str  = format_date(sale_date)
            ar_txn    = self.invoice_to_ar_txn.get(inv, "")
            sd_key    = (store, date_str)
            if sd_key not in agg_ar_txn and ar_txn:
                agg_ar_txn[sd_key] = ar_txn
            for method, amount in methods.items():
                if method not in CARD_PAYMENT_METHODS or amount <= 0:
                    continue
                agg_amount[(store, date_str, method)] += amount

        misc_files:       Dict[str, pd.DataFrame] = {}
        misc_detail_rows: List[Dict]              = []
        seq = 1

        for (store, date_str, method), total_payment in sorted(agg_amount.items()):
            misc_amount = self.bank_charges.calc_misc_amount(total_payment, method, store)
            if misc_amount is None:
                continue

            cfg            = self.bank_charges.get(method, store)
            ar_txn         = agg_ar_txn.get((store, date_str), "")
            org_id         = cfg.get("org_id", "300000001421038") if cfg else "300000001421038"
            activity       = cfg.get("activity", "Misc Activity")  if cfg else "Misc Activity"
            method_id      = cfg.get("method_id", "")              if cfg else ""
            _, bank_num    = self.receipt_methods.get_bank_account(store, method)
            receipt_number = (f"MISC-{method}-{ar_txn}" if ar_txn
                              else f"MISC-{method}-{seq:08d}")

            safe_store_part  = safe_filename(store)
            safe_method_part = safe_filename(method)
            date_compact     = date_str.replace("-", "")
            filename         = (f"MiscReceipt_{safe_method_part}_"
                                f"{safe_store_part}_{date_compact}.csv")

            row = {
                "Amount":                 round(misc_amount, 4),
                "CurrencyCode":           "SAR",
                "DepositDate":            date_str,
                "ReceiptDate":            date_str,
                "GlDate":                 date_str,
                "OrgId":                  org_id,
                "ReceiptNumber":          receipt_number,
                "ReceiptMethodId":        method_id,
                "ReceiptMethodName":      method,
                "ReceivableActivityName": activity,
                "BankAccountNumber":      bank_num,
            }

            misc_files[filename] = pd.DataFrame([row], columns=MISC_RECEIPT_COLUMNS)
            misc_detail_rows.append({
                "filename":      filename,
                "store":         store,
                "date":          date_str,
                "method":        method,
                "payment_total": total_payment,
                "misc_amount":   misc_amount,
            })
            seq += 1

        vl.section("8b. MISCELLANEOUS RECEIPT RECORDS — DETAIL")
        vl.kv("Misc receipt files to write", f"{len(misc_files):,}")
        if misc_detail_rows:
            vl.table_row("File", "Payment Total", "Misc Amount",
                         widths=(65, 16, 16))
            vl.divider(width=100)
            misc_grand = 0.0
            for r in misc_detail_rows:
                vl.table_row(r["filename"],
                             f"{r['payment_total']:,.2f}",
                             f"{r['misc_amount']:,.4f}",
                             widths=(65, 16, 16))
                misc_grand += r["misc_amount"]
            vl.divider(width=100)
            vl.table_row("GRAND TOTAL", "", f"{misc_grand:,.4f}",
                         widths=(65, 16, 16))
        else:
            vl.add("  No misc receipts generated.")

        return misc_files

    # ──────────────────────────────────────────────────────────────────
    # SAVING
    # ──────────────────────────────────────────────────────────────────

    def save_ar(self, df: pd.DataFrame):
        vl     = self.vlog
        folder = self.output_dir / "AR_Invoices"
        folder.mkdir(parents=True, exist_ok=True)

        run_date  = datetime.now()
        date_part = run_date.strftime("%m_%d_%b%Y")
        org_name  = safe_filename(AR_STATIC.get("Comments", "ORG"))

        vl.section("9. OUTPUT FILES — AR INVOICES")
        
        # Build reverse lookup: BILL_TO_ACCOUNT → store (SUBINVENTORY)
        account_to_store: Dict[str, str] = {}
        if self.metadata_cache:
            for (subinv, _ctype), meta in self.metadata_cache.primary.items():
                acc = meta.get("BILL_TO_ACCOUNT", "")
                if acc and acc not in account_to_store:
                    account_to_store[acc] = subinv
        
        # Group by Bill-to Customer Account Number (store)
        unique_stores = df["Bill-to Customer Account Number"].unique()
        
        total_files = 0
        total_rows = 0
        total_amount = 0.0
        
        for store_account in sorted(unique_stores):
            store_df = df[df["Bill-to Customer Account Number"] == store_account]
            
            # Get store name from metadata, fallback to account number
            store_name = account_to_store.get(store_account, store_account)
            safe_store_name = safe_filename(store_name)
            
            # Create subfolder for each store
            store_folder = folder / safe_store_name
            store_folder.mkdir(parents=True, exist_ok=True)
            
            # Filename: AR_Invoice_{store_name}_{org_name}_{date}.csv
            fpath = store_folder / f"AR_Invoice_{safe_store_name}_{org_name}_{date_part}.csv"
            
            store_df.to_csv(fpath, index=False, encoding="utf-8-sig", quoting=1)
            
            store_amt = store_df['Transaction Line Amount'].sum()
            total_files += 1
            total_rows += len(store_df)
            total_amount += store_amt
            
            print(f"  ✓ {safe_store_name:<30}  {len(store_df):>6,} rows  {store_amt:>14,.2f} SAR")
        
        vl.kv("Total files",  f"{total_files:,}")
        vl.kv("Total rows",   f"{total_rows:,}")
        vl.kv("Total amount", f"{total_amount:,.2f} SAR")
        print(f"\n  Summary: {total_files} file(s), {total_rows:,} rows, {total_amount:,.2f} SAR")

    def save_standard_receipts(self, receipt_files: Dict[str, pd.DataFrame]):
        vl   = self.vlog
        base = self.output_dir / "Receipts"
        vl.section("10. OUTPUT FILES — STANDARD RECEIPTS")

        method_totals: Dict[str, float] = defaultdict(float)
        method_counts: Dict[str, int]   = defaultdict(int)

        for fname, df in sorted(receipt_files.items()):
            parts  = fname.replace(".csv", "").split("_")
            method = parts[1] if len(parts) > 1 else "Other"
            folder = base / method
            folder.mkdir(parents=True, exist_ok=True)
            fpath  = folder / fname
            df.to_csv(fpath, index=False, encoding="utf-8-sig", quoting=1)
            amt = df["Amount"].sum()
            method_totals[method] += amt
            method_counts[method] += 1
            print(f"  ✓ {fname:<65}  {amt:,.2f} SAR")

        total_all = sum(method_totals.values())
        vl.kv("Grand Total", f"{total_all:,.2f} SAR")
        print(f"\n  Standard receipt grand total : {total_all:,.2f} SAR")

    def save_misc_receipts(self, misc_files: Dict[str, pd.DataFrame]):
        if not misc_files:
            return
        vl     = self.vlog
        folder = self.output_dir / "Receipts" / "Misc"
        folder.mkdir(parents=True, exist_ok=True)
        vl.section("10b. OUTPUT FILES — MISCELLANEOUS RECEIPTS")
        total_misc = 0.0
        for fname, df in sorted(misc_files.items()):
            fpath = folder / fname
            df.to_csv(fpath, index=False, encoding="utf-8-sig", quoting=1)
            amt = df["Amount"].sum()
            total_misc += amt
            print(f"  ✓ {fname:<65}  {amt:,.4f} SAR")
        print(f"\n  Misc receipt grand total : {total_misc:,.4f} SAR")

    # ──────────────────────────────────────────────────────────────────
    # FINAL CROSS-CHECK
    # ──────────────────────────────────────────────────────────────────

    def _write_final_crosscheck(
        self,
        ar_df:         pd.DataFrame,
        receipt_files: Dict[str, pd.DataFrame],
    ):
        vl = self.vlog
        vl.section("FINAL CROSS-CHECK — MAJOR VERIFICATION POINTS")

        input_lines  = len(self.line_items)
        output_lines = len(ar_df)
        lines_match  = output_lines == input_lines
        match_flag   = "✓ OK" if lines_match else "⚠ MISMATCH"
        
        ar_total       = ar_df["Transaction Line Amount"].sum()
        rcpt_total     = sum(df["Amount"].sum() for df in receipt_files.values())
        pay_norm_total = sum(
            amt
            for inv, methods in self.invoice_payments.items()
            for m, amt in methods.items()
            if self.invoice_ctype.get(inv, "NORMAL") not in ("TABBY", "TAMARA")
            and m in RECEIPT_PAYMENT_METHODS
        )

        diff = abs(rcpt_total - pay_norm_total)
        amounts_match = diff < 0.01
        
        seg1_unique = ar_df["Line Transactions Flexfield Segment 1"].nunique()
        seg2_unique = ar_df["Line Transactions Flexfield Segment 2"].nunique()
        seg1_ok = len(ar_df) == seg1_unique
        seg2_ok = len(ar_df) == seg2_unique
        
        # Add to summary
        vl.add_summary("Line Count Verification", 
                      f"{output_lines:,} rows", 
                      "PASS" if lines_match else "FAIL")
        vl.add_summary("Amount Reconciliation", 
                      f"{rcpt_total:,.2f} SAR", 
                      "PASS" if amounts_match else "FAIL")
        vl.add_summary("Segment 1 Uniqueness", 
                      f"{seg1_unique:,} unique", 
                      "PASS" if seg1_ok else "FAIL")
        vl.add_summary("Segment 2 Uniqueness", 
                      f"{seg2_unique:,} unique", 
                      "PASS" if seg2_ok else "FAIL")
        vl.add_summary("Total Invoices Processed", 
                      f"{len(self.invoice_payments):,}", 
                      "INFO")
        
        # Detailed verification in highlighted box
        vl.highlight_box("CRITICAL VERIFICATION CHECKS", [
            ("Input line item rows", f"{input_lines:,}"),
            ("Output AR rows", f"{output_lines:,}"),
            ("Line count match", match_flag),
            ("", ""),
            ("AR total amount", f"{ar_total:,.2f} SAR"),
            ("Payment file total", f"{pay_norm_total:,.2f} SAR"),
            ("Receipt total", f"{rcpt_total:,.2f} SAR"),
            ("Receipt vs payment diff", f"{diff:,.2f} SAR " + ("✓ MATCH" if amounts_match else "⚠ CHECK")),
            ("", ""),
            ("Segment 1 unique values", f"{seg1_unique:,} " + ("✓ OK" if seg1_ok else "⚠ duplicates")),
            ("Segment 2 unique values", f"{seg2_unique:,} " + ("✓ OK" if seg2_ok else "⚠ duplicates")),
        ])
        
        # Additional details
        vl.kv("Input line item rows", f"{input_lines:,}")
        vl.kv("Output AR rows",       f"{output_lines:,}")
        vl.kv("Difference",           f"{output_lines - input_lines:+,}  {match_flag}")

        vl.add()
        vl.kv("AR total",                    f"{ar_total:,.2f} SAR")
        vl.kv("Payment file total (NORMAL)", f"{pay_norm_total:,.2f} SAR")
        vl.kv("Receipt total",               f"{rcpt_total:,.2f} SAR")
        vl.kv("Receipt vs payment diff",
               f"{diff:,.2f} SAR  " + ("✓ MATCH" if amounts_match else "⚠ CHECK"))

        vl.add()
        vl.kv("Segment 1 unique",
               f"{seg1_unique:,}  "
               + ("✓" if seg1_ok else "⚠ duplicates"))
        vl.kv("Segment 2 unique",
               f"{seg2_unique:,}  "
               + ("✓" if seg2_ok else "⚠ duplicates"))

        vl.add()
        vl.add("  ══════════════════════════════════════════════════════════════════════")
        
        # Conditional completion message based on all checks
        all_checks_passed = lines_match and amounts_match and seg1_ok and seg2_ok
        if all_checks_passed:
            vl.add("  ✓  VERIFICATION COMPLETE")
            vl.add("  ✓  All major verification points passed successfully")
        else:
            vl.add("  ⚠  VERIFICATION COMPLETE WITH WARNINGS")
            vl.add("  ⚠  Please review the verification points above")
        
        vl.add(f"  ✓  Finished : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        vl.add("  ══════════════════════════════════════════════════════════════════════")
        
        # Add date-wise comparison if available
        if hasattr(self, '_date_comparison') and self._date_comparison:
            vl.add()
            vl.add(self._date_comparison)

    # ──────────────────────────────────────────────────────────────────
    # AR INVOICE MODE — load from pre-generated AR Invoice CSV
    # ──────────────────────────────────────────────────────────────────

    # ──────────────────────────────────────────────────────────────────
    # PAYMENT FILE LOADER (AR INVOICE MODE)
    # ──────────────────────────────────────────────────────────────────

    def _load_payment_file(
        self,
        payment_file_path: str,
        inv_ref_set: set,
    ) -> Optional[Dict[str, Dict[str, float]]]:
        """Load an optional payment CSV and return {inv_ref: {method: amount}}.

        Recognises a wide range of column names for Sales Order / Order Ref,
        Payment Method, and Amount so that common export formats work without
        manual column renaming.  Returns None on failure (file not found or
        required columns missing).
        """
        try:
            pf = self._read_file(payment_file_path)
        except Exception as exc:
            print(f"  ⚠ Payment file load error: {exc}")
            return None

        # Tolerant column discovery
        so_col = find_col(pf, [
            "Sales Order Number", "Sales Order", "Order Number",
            "Order Ref", "Payments/Order Ref", "SO Number",
            "Invoice Number", "Invoice Ref", "Reference",
        ])
        method_col = find_col(pf, [
            "Payments/Payment Method", "Payment Method",
            "Payment Type", "Method", "Pay Method",
        ])
        amount_col = find_col(pf, [
            "Payments/Amount", "Amount", "Paid Amount",
            "Payment Amount", "Total Amount",
        ])

        missing = [n for n, c in [
            ("Sales Order / Order Ref", so_col),
            ("Payment Method",          method_col),
            ("Amount",                  amount_col),
        ] if not c]
        if missing:
            print(f"  ⚠ Payment file missing required columns: {missing} — skipped")
            return None

        result: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        unmatched = 0
        for _, row in pf.iterrows():
            inv    = clean_order_ref(safe_str(row.get(so_col, "")).strip())
            method = normalise_payment(safe_str(row.get(method_col, "Cash")))
            amount = safe_float(row.get(amount_col, 0))
            if not inv or amount == 0:
                continue
            if inv in inv_ref_set:
                result[inv][method] += amount
            else:
                unmatched += 1

        if unmatched:
            print(f"  ⚠ {unmatched:,} payment file row(s) did not match any "
                  f"AR Invoice Sales Order reference")
        print(f"  ✓ Payment file loaded: {len(result):,} matched invoice references")
        return result

    def load_from_ar_invoice(
        self,
        ar_invoice_path:      str,
        metadata_path:        str,
        receipt_methods_path: str = "",
        bank_charges_path:    str = "",
        payment_file_path:    str = "",
    ):
        """Populate invoice dictionaries from an already-generated AR Invoice CSV.

        An optional *payment_file_path* (CSV/XLSX) can be supplied to provide
        actual payment-method breakdowns per Sales Order.  Expected columns:
          • Sales Order Number (or Order Ref / Invoice Number / …)
          • Payment Method  (e.g. Cash, Mada, Visa, MasterCard)
          • Amount

        When matched by Sales Order Number the payment methods replace the
        default Cash allocation, enabling correct Misc Receipt generation for
        card-payment bank charges.  Invoices absent from the payment file fall
        back to Cash.
        """
        vl = self.vlog
        vl.section("1. INPUT FILES (AR INVOICE MODE)")
        vl.kv("AR Invoice file",  Path(ar_invoice_path).name)
        vl.kv("Metadata file",    Path(metadata_path).name)
        vl.kv("Receipt Methods",  Path(receipt_methods_path).name if receipt_methods_path else "—")
        vl.kv("Bank Charges",     Path(bank_charges_path).name    if bank_charges_path    else "—")
        vl.kv("Payment File",     Path(payment_file_path).name    if payment_file_path    else "—")
        vl.kv("Segment 1 prefix", self._seg1_prefix)
        vl.kv("Segment 2 prefix", self._seg2_prefix)
        vl.add()

        self.metadata_cache  = MetadataCache(metadata_path)
        self.receipt_methods = ReceiptMethodsCache(receipt_methods_path)
        self.bank_charges    = BankChargesCache(bank_charges_path)

        # Build reverse lookup: BILL_TO_ACCOUNT → store (SUBINVENTORY)
        account_to_store: Dict[str, str] = {}
        for (subinv, _ctype), meta in self.metadata_cache.primary.items():
            acc = meta["BILL_TO_ACCOUNT"]
            if acc and acc not in account_to_store:
                account_to_store[acc] = subinv

        # Read AR Invoice CSV
        ar_df = self._read_file(ar_invoice_path)
        vl.kv("AR rows read", len(ar_df))

        # Needed columns (resolve tolerantly)
        COL_TXN   = find_col(ar_df, ["Transaction Number"])
        COL_DATE  = find_col(ar_df, ["Transaction Date", "Accounting Date"])
        COL_ACCT  = find_col(ar_df, ["Bill-to Customer Account Number"])
        COL_SITE  = find_col(ar_df, ["Bill-to Customer Site Number"])
        COL_AMT   = find_col(ar_df, ["Transaction Line Amount"])
        COL_SO    = find_col(ar_df, ["Sales Order Number"])

        if not COL_TXN or not COL_DATE or not COL_AMT:
            raise ValueError(
                "AR Invoice CSV is missing required columns: "
                "Transaction Number / Transaction Date / Transaction Line Amount"
            )

        for _, row in ar_df.iterrows():
            txn_num = safe_str(row.get(COL_TXN, "")).strip()
            inv_ref = safe_str(row.get(COL_SO,  "")).strip() if COL_SO else ""
            amount  = safe_float(row.get(COL_AMT, 0))

            if not txn_num:
                continue
            # Fall back to txn_num as the invoice reference if SO is blank
            if not inv_ref:
                inv_ref = txn_num

            # Date
            try:
                date_parsed = pd.to_datetime(row.get(COL_DATE), errors="coerce")
                if pd.isna(date_parsed):
                    date_parsed = datetime.now()
            except Exception:
                date_parsed = datetime.now()

            # Resolve store: prefer account-number lookup, then SO prefix
            account = safe_str(row.get(COL_ACCT, "")).strip() if COL_ACCT else ""
            if account and account in account_to_store:
                store = account_to_store[account]
            elif "/" in inv_ref:
                store = inv_ref.split("/")[0].upper().strip()
            else:
                store = txn_num

            # Register this invoice
            if inv_ref not in self.invoice_store:
                self.invoice_store[inv_ref]     = store
                self.invoice_date[inv_ref]      = date_parsed
                self.invoice_ctype[inv_ref]     = "NORMAL"
                self.invoice_to_ar_txn[inv_ref] = txn_num

            # Accumulate amount as Cash (default — no payment method data in AR Invoice)
            self.invoice_payments[inv_ref]["Cash"] += amount

        # Compute AR totals per invoice (from the Cash-based pass, before any override)
        for inv_ref, methods in self.invoice_payments.items():
            self.invoice_ar_total[inv_ref] = sum(methods.values())

        vl.kv("Unique invoices loaded",    len(self.invoice_store))
        vl.kv("Unique transactions (BLK)", len({v for v in self.invoice_to_ar_txn.values()}))
        total_amount = sum(self.invoice_ar_total.values())
        vl.kv("Total AR amount", f"{total_amount:,.2f} SAR")
        vl.add()

        # ── Optional payment file: replace Cash defaults with real methods ──
        if payment_file_path and Path(payment_file_path).exists():
            vl.section("1b. PAYMENT FILE (AR INVOICE MODE)")
            payment_data = self._load_payment_file(
                payment_file_path, set(self.invoice_store.keys())
            )
            if payment_data is not None:
                # Override payments only for invoices present in the payment file;
                # all other invoices retain their existing Cash allocation.
                for inv_ref, methods in payment_data.items():
                    if inv_ref in self.invoice_payments:
                        self.invoice_payments[inv_ref].clear()
                    for method, amount in methods.items():
                        self.invoice_payments[inv_ref][method] += amount

                # Refresh invoice types from the real payment methods
                for inv, methods in self.invoice_payments.items():
                    if "TAMARA" in methods:
                        self.invoice_ctype[inv] = "TAMARA"
                    elif "TABBY" in methods:
                        self.invoice_ctype[inv] = "TABBY"
                    else:
                        self.invoice_ctype[inv] = "NORMAL"

                # Log payment method breakdown from file
                method_totals: Dict[str, float] = defaultdict(float)
                method_counts: Dict[str, int]   = defaultdict(int)
                for inv_methods in self.invoice_payments.values():
                    for m, amt in inv_methods.items():
                        method_totals[m] += amt
                        method_counts[m] += 1
                vl.table_row("Payment Method", "Invoices", "Total Amount (SAR)",
                             widths=(25, 12, 22))
                vl.divider()
                for m in sorted(method_totals):
                    vl.table_row(m, method_counts[m],
                                 f"{method_totals[m]:,.2f}", widths=(25, 12, 22))
                vl.divider()
                vl.table_row("TOTAL",
                             sum(method_counts.values()),
                             f"{sum(method_totals.values()):,.2f}",
                             widths=(25, 12, 22))
                vl.add()
                vl.add("  Payment methods sourced from the uploaded payment file.")
                vl.add("  Misc Receipts will be generated for card-payment methods")
                vl.add("  matched against BANK_CHARGES.csv.")
            else:
                vl.add("  Payment file could not be loaded — falling back to Cash.")
                vl.add("  NOTE: All amounts attributed to Cash.")
                vl.add("        Misc Receipts are generated only when BANK_CHARGES.csv has")
                vl.add("        a non-zero charge rate for a given method.")
        else:
            vl.add("  NOTE: All amounts attributed to Cash (no payment file supplied).")
            vl.add("        Misc Receipts are generated only when BANK_CHARGES.csv has")
            vl.add("        a non-zero charge rate for a given method.")

        vl.section("2. STORE BREAKDOWN (AR INVOICE MODE)")
        store_totals: Dict[str, float] = defaultdict(float)
        store_counts: Dict[str, int]   = defaultdict(int)
        for inv, methods in self.invoice_payments.items():
            st = self.invoice_store.get(inv, "?")
            store_totals[st] += sum(methods.values())
            store_counts[st] += 1
        vl.table_row("Store", "Invoices", "Amount (SAR)", widths=(30, 10, 20))
        vl.divider()
        for st in sorted(store_totals.keys()):
            vl.table_row(st, store_counts[st], f"{store_totals[st]:,.2f}", widths=(30, 10, 20))

    def _write_ar_invoice_crosscheck(
        self,
        receipt_files: Dict[str, pd.DataFrame],
    ):
        vl = self.vlog
        vl.section("FINAL CROSS-CHECK — MAJOR VERIFICATION POINTS (AR INVOICE MODE)")

        ar_total   = sum(self.invoice_ar_total.values())
        rcpt_total = sum(df["Amount"].sum() for df in receipt_files.values())
        diff = abs(rcpt_total - ar_total)
        amounts_match = diff < 0.01

        # Add to summary
        vl.add_summary("AR Invoice Total", 
                      f"{ar_total:,.2f} SAR", 
                      "INFO")
        vl.add_summary("Standard Receipt Total", 
                      f"{rcpt_total:,.2f} SAR", 
                      "INFO")
        vl.add_summary("Amount Reconciliation", 
                      f"Diff: {diff:,.2f} SAR", 
                      "PASS" if amounts_match else "FAIL")
        vl.add_summary("Total Invoices", 
                      f"{len(self.invoice_ar_total):,}", 
                      "INFO")
        vl.add_summary("Receipt Files Generated", 
                      f"{len(receipt_files):,}", 
                      "INFO")
        
        # Detailed verification in highlighted box
        vl.highlight_box("CRITICAL VERIFICATION CHECKS", [
            ("Total AR Invoice amount", f"{ar_total:,.2f} SAR"),
            ("Total Standard Receipt amt", f"{rcpt_total:,.2f} SAR"),
            ("Difference", f"{diff:,.2f} SAR " + ("✓ MATCH" if amounts_match else "⚠ CHECK")),
            ("", ""),
            ("Status", "✓ VERIFIED" if amounts_match else "⚠ REVIEW REQUIRED"),
        ])

        vl.kv("Total AR Invoice amount",    f"{ar_total:,.2f} SAR")
        vl.kv("Total Standard Receipt amt", f"{rcpt_total:,.2f} SAR")
        vl.kv("Difference",
               f"{diff:,.2f} SAR  " + ("✓ MATCH" if amounts_match else "⚠ CHECK"))
        vl.add()
        vl.add("  ══════════════════════════════════════════════════════════════════════")
        
        # Conditional completion message based on verification result
        if amounts_match:
            vl.add("  ✓  VERIFICATION COMPLETE")
            vl.add("  ✓  All major verification points passed successfully")
        else:
            vl.add("  ⚠  VERIFICATION COMPLETE WITH WARNINGS")
            vl.add("  ⚠  Please review the amount discrepancies above")
        
        vl.add(f"  ✓  Finished : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        vl.add("  ══════════════════════════════════════════════════════════════════════")

    def run_from_ar_invoice(
        self,
        ar_invoice_path:      str,
        metadata_path:        str,
        receipt_methods_path: str = "",
        bank_charges_path:    str = "",
        payment_file_path:    str = "",
    ):
        """Full pipeline: AR Invoice CSV → Standard Receipts + Misc Receipts."""
        self.load_from_ar_invoice(
            ar_invoice_path, metadata_path,
            receipt_methods_path, bank_charges_path,
            payment_file_path=payment_file_path,
        )
        std_rcp  = self.generate_standard_receipts()
        self.save_standard_receipts(std_rcp)
        misc_rcp = self.generate_misc_receipts()
        self.save_misc_receipts(misc_rcp)
        self._write_ar_invoice_crosscheck(std_rcp)

        self.vlog.close()
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = self.output_dir / f"Verification_Report_{ts}.txt"
        self.vlog.write(log_path)
        self.vlog.print_summary()

        print("\n" + "=" * 72)
        print("✅  ORACLE FUSION INTEGRATION (AR INVOICE MODE) COMPLETE")
        print("=" * 72)

    # ──────────────────────────────────────────────────────────────────
    # PIPELINE
    # ──────────────────────────────────────────────────────────────────

    def run(
        self,
        line_items_path:      str,
        payments_path:        str,
        metadata_path:        str,
        registers_path:       str,
        receipt_methods_path: str = "",
        bank_charges_path:    str = "",
    ):
        self.load_data(
            line_items_path, payments_path,
            metadata_path,   registers_path,
            receipt_methods_path, bank_charges_path,
        )
        ar_df    = self.generate_ar_invoices()
        self.save_ar(ar_df)
        std_rcp  = self.generate_standard_receipts()
        self.save_standard_receipts(std_rcp)
        misc_rcp = self.generate_misc_receipts()
        self.save_misc_receipts(misc_rcp)
        self._write_final_crosscheck(ar_df, std_rcp)

        self.vlog.close()
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = self.output_dir / f"Verification_Report_{ts}.txt"
        self.vlog.write(log_path)
        self.vlog.print_summary()

        print("\n" + "=" * 72)
        print("✅  ORACLE FUSION INTEGRATION COMPLETE")
        print("=" * 72)


# ============================================================================
# MAIN
# ============================================================================

def main():
    import glob

    xlsx_files = sorted(glob.glob("*.xlsx"))

    line_items_path = ""
    payments_path   = ""

    for f in xlsx_files:
        try:
            df_peek = pd.read_excel(f, nrows=1)
            cols    = [str(c).strip() for c in df_peek.columns]
            col_str = " ".join(cols).lower()
            if "payment method" in col_str or "payments/payment" in col_str:
                payments_path = f
            elif any(k in col_str for k in
                     ("product", "barcode", "qty", "quantity", "subtotal", "base uom")):
                line_items_path = f
        except Exception:
            pass

    if not line_items_path:
        line_items_path = "Point of Sale Orders (pos.order) - 2026-04-12T162041.258.xlsx"
    if not payments_path:
        payments_path   = "Point of Sale Orders (pos.order) - 2026-04-12T162030.266.xlsx"

    print(f"  Line items file : {line_items_path}")
    print(f"  Payments file   : {payments_path}")

    INPUT = {
        "line_items":      "ARABMALL Sales line 5 to 31 March.xlsx",
        "payments":        "ARABMALL Payment line 5 to 31 March.xlsx",
        "metadata":        "FUSION_SALES_METADATA_202604121703.csv",
        "registers":       "VENDHQ_REGISTERS_202604121654.csv",
        "receipt_methods": "Receipt_Methods.csv",
        "bank_charges":    "Bank_Charges.csv",
    }

    START_TXN_SEQUENCE  = 587   # ← update from report "Next run START_TXN_SEQUENCE ="
    START_LEGACY_SEQ_1  = 1   # ← counter only; prefix is auto-randomised each run
    START_LEGACY_SEQ_2  = 1   # ← counter only; prefix is auto-randomised each run

    integration = OracleFusionIntegration(
        output_dir         = "ORACLE_FUSION_OUTPUT",
        start_seq          = START_TXN_SEQUENCE,
        start_legacy_seq_1 = START_LEGACY_SEQ_1,
        start_legacy_seq_2 = START_LEGACY_SEQ_2,
    )
    try:
        integration.run(
            INPUT["line_items"],
            INPUT["payments"],
            INPUT["metadata"],
            INPUT["registers"],
            receipt_methods_path = INPUT["receipt_methods"],
            bank_charges_path    = INPUT["bank_charges"],
        )
    except FileNotFoundError as e:
        print(f"\n❌  File not found: {e}")
    except Exception as e:
        import traceback
        print(f"\n❌  Error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()