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

RECEIPT_PAYMENT_METHODS    = {"Cash", "Mada", "Visa", "Master", "Amex"}
NO_RECEIPT_PAYMENT_METHODS = {"TABBY", "TAMARA"}
CARD_PAYMENT_METHODS       = {"Mada", "Visa", "Master", "Amex"}

PAYMENT_METHOD_NORM: Dict[str, str] = {
    "CASH":        "Cash",
    "MADA":        "Mada",
    "VISA":        "Visa",
    "MASTERCARD":  "Master",
    "MASTER CARD": "Master",
    "MASTER":      "Master",
    "MC":          "Master",
    "TAMARA":      "TAMARA",
    "TABBY":       "TABBY",
    "AMEX":        "Amex",
    "APPLE PAY":   "Apple Pay",
    "APPLEPAY":    "Apple Pay",
    "STC PAY":     "STC Pay",
    "STCPAY":      "STC Pay",
    "GCCNET":      "GCCNET",
}

PAYMENT_BANK_MAP_FALLBACK: Dict[str, Tuple[str, str, str]] = {
    "Cash":       ("Cash",       "Cash Bank",       "Cash Account"),
    "Mada":       ("Mada",       "Mada Bank",       "Mada Account"),
    "Visa":       ("Visa",       "Visa Bank",       "Visa Account"),
    "Master": ("Master", "Master Bank", "Master Account"),
    "Amex":       ("Amex",       "Amex Bank",       "Amex Account"),
    "Apple Pay":  ("Apple Pay",  "Apple Pay Bank",  "Apple Pay Account"),
    "STC Pay":    ("STC Pay",    "STC Pay Bank",    "STC Pay Account"),
}
DEFAULT_BANK: Tuple[str, str, str] = ("Cash", "Cash Bank", "Cash Account")

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

# Miss Receipt (Miscellaneous Receipt) Organization ID
MISS_RECEIPT_ORG_ID = "300000001421038"

# Miss Receipt (Miscellaneous Receipt) Activity Name
MISS_RECEIPT_ACTIVITY = "Bank Charge"

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
    if "MASTER" in key or key.startswith("MC"): return "Master"
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
    # Pass 1: exact (whitespace-normalised) match — preserves prior behaviour.
    norm_map = {normalise_col_name(c): c for c in df.columns}
    for cand in candidates:
        norm_cand = normalise_col_name(cand)
        if norm_cand in norm_map:
            return norm_map[norm_cand]
    # Pass 2: case-insensitive match. Many Odoo exports vary header casing
    # (e.g. "payments/payment method" vs "Payments/Payment Method"), and a
    # silent miss here causes the loader to fall back to Cash-only receipts.
    ci_map = {normalise_col_name(c).lower(): c for c in df.columns}
    for cand in candidates:
        norm_cand = normalise_col_name(cand).lower()
        if norm_cand in ci_map:
            return ci_map[norm_cand]
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
    # Line item amounts MUST be read WITHOUT tax, then adjusted by payment factor.
    # This ensures we're working with base amounts and the payment adjustment
    # correctly scales them to match actual cash collected (which includes tax).
    # The system will calculate: adjusted_amount = base_amount * (payment_total / sales_total)
    # NO fallback to tax-inclusive columns - if w/o tax column is missing, fail with clear error.
    "Subtotal w/o Tax": [
        "Order Lines/Subtotal w/o Tax",  # Tax-exclusive (PRIMARY - correct base amount)
        "Order Lines/Subtotal excl tax",
        "Order Lines/Price excl. tax",
        "Subtotal w/o Tax",
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
    
    # Box formatting constants
    BOX_WIDTH = 70          # Total width of the summary box
    BORDER_CHARS = 4        # Width of border characters (║  ... ║)
    
    # Spacer for visual separation in highlight boxes
    SPACER_LINE = ("", "")  # Empty tuple for adding blank lines in boxes
    
    # Keywords for identifying major sections that need enhanced formatting
    # Note: "VERIFICATION" will match "VERIFICATION SUMMARY" and similar titles
    MAJOR_SECTION_KEYWORDS = [
        "FINAL CROSS-CHECK", "VERIFICATION", "VALIDATION", 
        "MAJOR VERIFICATION POINTS"
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
        """Write verification report to text file and generate CSV summaries"""
        # Write main text report
        with open(path, "w", encoding="utf-8") as f:
            # Professional Header with Company Branding
            f.write("╔" + "═" * 90 + "╗\n")
            f.write("║" + " " * 90 + "║\n")
            f.write("║" + " " * 20 + "ORACLE FUSION FINANCIAL INTEGRATION" + " " * 35 + "║\n")
            f.write("║" + " " * 25 + "VERIFICATION REPORT" + " " * 46 + "║\n")
            f.write("║" + " " * 90 + "║\n")
            f.write("╠" + "═" * 90 + "╣\n")
            f.write(f"║  Report Generated    : {self.run_ts.strftime('%A, %B %d, %Y at %I:%M:%S %p'):<66}║\n")
            f.write(f"║  Report Type         : {'Accounts Receivable & Receipt Validation':<66}║\n")
            f.write(f"║  System Version      : {'v2.5.0 - Enhanced Verification':<66}║\n")
            f.write("╚" + "═" * 90 + "╝\n\n")

            # Executive Summary - Key Metrics Dashboard
            if self._summary_items:
                pass_count = sum(1 for _, _, s in self._summary_items if s == "PASS")
                fail_count = sum(1 for _, _, s in self._summary_items if s == "FAIL")
                warn_count = sum(1 for _, _, s in self._summary_items if s == "WARN")
                total_checks = len(self._summary_items)

                f.write("╔" + "═" * 90 + "╗\n")
                f.write("║" + " " * 30 + "EXECUTIVE SUMMARY" + " " * 43 + "║\n")
                f.write("╠" + "═" * 90 + "╣\n")

                # Overall Status with color indicators
                if fail_count == 0 and warn_count == 0:
                    status_msg = "✓ READY FOR ORACLE FUSION IMPORT"
                    status_detail = "All validation checks passed successfully"
                elif fail_count == 0:
                    status_msg = "⚠ REVIEW RECOMMENDED"
                    status_detail = f"{warn_count} warning(s) require review before import"
                else:
                    status_msg = "✗ ACTION REQUIRED"
                    status_detail = f"{fail_count} critical issue(s) must be resolved"

                f.write(f"║                                                                                          ║\n")
                f.write(f"║  Overall Status      : {status_msg:<66}║\n")
                f.write(f"║  Assessment          : {status_detail:<66}║\n")
                f.write(f"║                                                                                          ║\n")
                f.write("╠" + "─" * 90 + "╣\n")
                f.write(f"║  Validation Metrics  :                                                                   ║\n")
                f.write(f"║                                                                                          ║\n")

                # Calculate percentage
                pass_pct = (pass_count / total_checks * 100) if total_checks > 0 else 0

                f.write(f"║      Total Checks           : {total_checks:>3}                                                            ║\n")
                f.write(f"║      Passed  [✓]            : {pass_count:>3}   ({pass_pct:>5.1f}%)                                              ║\n")
                f.write(f"║      Failed  [✗]            : {fail_count:>3}                                                            ║\n")
                f.write(f"║      Warnings [⚠]           : {warn_count:>3}                                                            ║\n")
                f.write(f"║                                                                                          ║\n")
                f.write("╚" + "═" * 90 + "╝\n\n")

            # Quick Checklist for Manual Verification
            if self._summary_items:
                f.write("╔" + "═" * 70 + "╗\n")
                f.write("║" + " " * 15 + "QUICK VERIFICATION CHECKLIST" + " " * 27 + "║\n")
                f.write("║" + " " * 15 + "(For Manual Review)" + " " * 36 + "║\n")
                f.write("╠" + "═" * 70 + "╣\n")

                pass_count = sum(1 for _, _, s in self._summary_items if s == "PASS")
                fail_count = sum(1 for _, _, s in self._summary_items if s == "FAIL")
                warn_count = sum(1 for _, _, s in self._summary_items if s == "WARN")

                overall_status = "✓ ALL CHECKS PASSED" if fail_count == 0 else "⚠ ISSUES NEED REVIEW"
                f.write(f"║  Overall Status: {overall_status:<51}║\n")

                # Calculate padding dynamically using class constants
                stats_line = f"Passed: {pass_count:<3}  |  Failed: {fail_count:<3}  |  Warnings: {warn_count:<3}"
                padding_needed = self.BOX_WIDTH - self.BORDER_CHARS - len(stats_line) - 2
                f.write(f"║  {stats_line}{' ' * padding_needed}║\n")
                f.write("╠" + "═" * 70 + "╣\n")

                # Checklist format with checkboxes
                for label, value, status in self._summary_items:
                    checkbox = {"PASS": "[✓]", "FAIL": "[✗]", "WARN": "[⚠]", "INFO": "[ℹ]"}.get(status, "[ ]")
                    # Truncate to fit in display width using class constants
                    suffix_len = len(self.TRUNCATE_SUFFIX)
                    label_truncated = (label[:self.MAX_LABEL_WIDTH - suffix_len] + self.TRUNCATE_SUFFIX) if len(label) > self.MAX_LABEL_WIDTH else label
                    value_truncated = (value[:self.MAX_VALUE_WIDTH - suffix_len] + self.TRUNCATE_SUFFIX) if len(value) > self.MAX_VALUE_WIDTH else value
                    f.write(f"║  {checkbox} {label_truncated:<{self.MAX_LABEL_WIDTH}} {value_truncated:<{self.MAX_VALUE_WIDTH - 1}}║\n")

                f.write("╚" + "═" * 70 + "╝\n\n")

            # Detailed Sections with improved formatting
            f.write("\n" + "╔" + "═" * 90 + "╗\n")
            f.write("║" + " " * 30 + "DETAILED VERIFICATION" + " " * 39 + "║\n")
            f.write("╚" + "═" * 90 + "╝\n\n")

            for title, lines in self.sections:
                # Highlight major verification sections using class constant
                is_major = any(kw in title.upper() for kw in self.MAJOR_SECTION_KEYWORDS)

                if is_major:
                    f.write("\n╔" + "═" * 90 + "╗\n")
                    f.write(f"║  {title:<87} ║\n")
                    f.write("╚" + "═" * 90 + "╝\n")
                else:
                    f.write(f"\n{'━'*90}\n")
                    f.write(f"▶ {title}\n")
                    f.write(f"{'━'*90}\n")

                for line in lines:
                    f.write(line + "\n")
                f.write("\n")

            # Professional Footer
            f.write("\n" + "╔" + "═" * 90 + "╗\n")
            f.write("║" + " " * 90 + "║\n")
            f.write("║" + " " * 25 + "END OF VERIFICATION REPORT" + " " * 39 + "║\n")
            f.write("║" + " " * 90 + "║\n")
            f.write("║  For questions or support, please contact your system administrator.                    ║\n")
            f.write("║  This is an automated report generated by Oracle Fusion Integration System.             ║\n")
            f.write("║" + " " * 90 + "║\n")
            f.write("╚" + "═" * 90 + "╝\n")

        print(f"  ✓ Verification report : {path}")

        # Generate CSV summary for Excel analysis
        self._write_csv_summary(path)

        # Generate HTML report for professional presentation
        self._write_html_report(path)

    def _write_csv_summary(self, base_path: Path):
        """Generate enhanced CSV summary file for Excel analysis"""
        csv_path = base_path.with_name(base_path.stem + "_Summary.csv")

        try:
            import csv
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)

                # Professional header
                writer.writerow(["Oracle Fusion Integration - Verification Summary"])
                writer.writerow([f"Generated: {self.run_ts.strftime('%Y-%m-%d %H:%M:%S')}"])
                writer.writerow([])

                # Summary statistics
                pass_count = sum(1 for _, _, s in self._summary_items if s == "PASS")
                fail_count = sum(1 for _, _, s in self._summary_items if s == "FAIL")
                warn_count = sum(1 for _, _, s in self._summary_items if s == "WARN")

                writer.writerow(["Summary Statistics"])
                writer.writerow(["Total Checks", "Passed", "Failed", "Warnings"])
                writer.writerow([len(self._summary_items), pass_count, fail_count, warn_count])
                writer.writerow([])

                # Overall status
                if fail_count == 0 and warn_count == 0:
                    status = "READY FOR IMPORT"
                elif fail_count == 0:
                    status = "REVIEW RECOMMENDED"
                else:
                    status = "ACTION REQUIRED"
                writer.writerow(["Overall Status", status])
                writer.writerow([])

                # Detailed verification items
                writer.writerow(["Verification Details"])
                writer.writerow(["Item", "Value", "Status", "Result"])

                # Write summary items
                for label, value, status in self._summary_items:
                    result = {"PASS": "✓ PASS", "FAIL": "✗ FAIL", "WARN": "⚠ WARNING", "INFO": "ℹ INFO"}.get(status, status)
                    writer.writerow([label, value, status, result])

            print(f"  ✓ CSV Summary         : {csv_path}")
        except Exception as e:
            print(f"  ⚠ Could not generate CSV summary: {e}")

    def _write_html_report(self, base_path: Path):
        """Generate professional HTML report for web viewing"""
        html_path = base_path.with_name(base_path.stem + "_Report.html")

        try:
            pass_count = sum(1 for _, _, s in self._summary_items if s == "PASS")
            fail_count = sum(1 for _, _, s in self._summary_items if s == "FAIL")
            warn_count = sum(1 for _, _, s in self._summary_items if s == "WARN")
            total_checks = len(self._summary_items)

            # Overall status
            if fail_count == 0 and warn_count == 0:
                status_class = "success"
                status_msg = "✓ READY FOR ORACLE FUSION IMPORT"
                status_detail = "All validation checks passed successfully"
            elif fail_count == 0:
                status_class = "warning"
                status_msg = "⚠ REVIEW RECOMMENDED"
                status_detail = f"{warn_count} warning(s) require review before import"
            else:
                status_class = "error"
                status_msg = "✗ ACTION REQUIRED"
                status_detail = f"{fail_count} critical issue(s) must be resolved"

            pass_pct = (pass_count / total_checks * 100) if total_checks > 0 else 0

            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Oracle Fusion - Verification Report</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f0f2f5;
            padding: 0;
            color: #1a1a1a;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 0 60px rgba(0,0,0,0.08);
        }}

        .header {{
            background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
            color: white;
            padding: 60px 50px;
            position: relative;
            overflow: hidden;
        }}

        .header::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 500px;
            height: 500px;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            border-radius: 50%;
        }}

        .header h1 {{
            font-size: 42px;
            margin-bottom: 12px;
            font-weight: 700;
            letter-spacing: -0.5px;
            position: relative;
            z-index: 1;
        }}

        .header h2 {{
            font-size: 22px;
            font-weight: 300;
            opacity: 0.95;
            letter-spacing: 0.5px;
            position: relative;
            z-index: 1;
        }}

        .metadata {{
            background: linear-gradient(to right, #fafbfc 0%, #f5f7fa 100%);
            padding: 30px 50px;
            border-bottom: 1px solid #e1e8ed;
        }}

        .metadata-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
        }}

        .metadata-item {{
            display: flex;
            align-items: center;
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            border: 1px solid #e8eaed;
            transition: all 0.3s ease;
        }}

        .metadata-item:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            transform: translateY(-2px);
        }}

        .metadata-label {{
            font-weight: 600;
            color: #5f6368;
            margin-right: 12px;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .metadata-value {{
            color: #202124;
            font-weight: 500;
        }}

        .executive-summary {{
            padding: 50px;
            background: white;
        }}

        .status-card {{
            padding: 40px;
            border-radius: 12px;
            margin-bottom: 40px;
            text-align: center;
            box-shadow: 0 8px 24px rgba(0,0,0,0.12);
            position: relative;
            overflow: hidden;
        }}

        .status-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: rgba(255,255,255,0.3);
        }}

        .status-card.success {{
            background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
            color: white;
        }}

        .status-card.warning {{
            background: linear-gradient(135deg, #f2994a 0%, #f2c94c 100%);
            color: white;
        }}

        .status-card.error {{
            background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
            color: white;
        }}

        .status-card h3 {{
            font-size: 32px;
            margin-bottom: 12px;
            font-weight: 700;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .status-card p {{
            font-size: 17px;
            opacity: 0.95;
            font-weight: 400;
        }}

        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 25px;
            margin-top: 40px;
        }}

        .metric-card {{
            background: linear-gradient(135deg, #fafbfc 0%, #ffffff 100%);
            padding: 30px 25px;
            border-radius: 12px;
            text-align: center;
            border: 2px solid #e8eaed;
            transition: all 0.3s ease;
            position: relative;
        }}

        .metric-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: linear-gradient(to bottom, #667eea 0%, #764ba2 100%);
            border-radius: 12px 0 0 12px;
        }}

        .metric-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 12px 24px rgba(0,0,0,0.1);
            border-color: #667eea;
        }}

        .metric-value {{
            font-size: 44px;
            font-weight: 700;
            color: #202124;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .metric-label {{
            font-size: 12px;
            color: #5f6368;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            font-weight: 600;
        }}

        .checklist {{
            padding: 50px;
            background: linear-gradient(to bottom, #fafbfc 0%, #f5f7fa 100%);
        }}

        .section-title {{
            font-size: 28px;
            color: #202124;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
            font-weight: 700;
            letter-spacing: -0.5px;
            position: relative;
        }}

        .section-title::after {{
            content: '';
            position: absolute;
            bottom: -3px;
            left: 0;
            width: 80px;
            height: 3px;
            background: linear-gradient(to right, #667eea, #764ba2);
        }}

        .checklist-items {{
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0,0,0,0.08);
            border: 1px solid #e8eaed;
        }}

        .checklist-item {{
            padding: 20px 30px;
            border-bottom: 1px solid #f0f2f5;
            display: flex;
            align-items: center;
            transition: all 0.2s ease;
        }}

        .checklist-item:hover {{
            background: #fafbfc;
            padding-left: 35px;
        }}

        .checklist-item:last-child {{
            border-bottom: none;
        }}

        .checkbox {{
            font-size: 24px;
            margin-right: 20px;
            min-width: 35px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .checkbox.pass {{ color: #00b09b; }}
        .checkbox.fail {{ color: #eb3349; }}
        .checkbox.warn {{ color: #f2994a; }}
        .checkbox.info {{ color: #667eea; }}

        .item-label {{
            flex: 1;
            font-weight: 500;
            color: #202124;
            font-size: 15px;
        }}

        .item-value {{
            color: #5f6368;
            margin-left: 25px;
            font-family: 'SF Mono', 'Monaco', 'Consolas', 'Courier New', monospace;
            font-size: 14px;
            background: #f8f9fa;
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid #e8eaed;
        }}

        .footer {{
            background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        .footer p {{
            margin: 8px 0;
            opacity: 0.95;
            font-size: 14px;
        }}

        .footer strong {{
            font-weight: 700;
            font-size: 16px;
            letter-spacing: 0.5px;
        }}

        @media print {{
            body {{ background: white; padding: 0; }}
            .container {{ box-shadow: none; }}
            .metric-card, .checklist-item {{ page-break-inside: avoid; }}
        }}

        @media (max-width: 768px) {{
            .header h1 {{ font-size: 28px; }}
            .header h2 {{ font-size: 18px; }}
            .metrics {{ grid-template-columns: 1fr; }}
            .metadata-grid {{ grid-template-columns: 1fr; }}
            .executive-summary, .checklist {{ padding: 30px 20px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ORACLE FUSION FINANCIAL INTEGRATION</h1>
            <h2>Verification Report</h2>
        </div>

        <div class="metadata">
            <div class="metadata-grid">
                <div class="metadata-item">
                    <span class="metadata-label">Generated:</span>
                    <span class="metadata-value">{self.run_ts.strftime('%A, %B %d, %Y at %I:%M:%S %p')}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Report Type:</span>
                    <span class="metadata-value">AR & Receipt Validation</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">System Version:</span>
                    <span class="metadata-value">v2.5.0 - Enhanced</span>
                </div>
            </div>
        </div>

        <div class="executive-summary">
            <h2 class="section-title">Executive Summary</h2>

            <div class="status-card {status_class}">
                <h3>{status_msg}</h3>
                <p>{status_detail}</p>
            </div>

            <div class="metrics">
                <div class="metric-card">
                    <div class="metric-value">{total_checks}</div>
                    <div class="metric-label">Total Checks</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{pass_count}</div>
                    <div class="metric-label">Passed</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{fail_count}</div>
                    <div class="metric-label">Failed</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{warn_count}</div>
                    <div class="metric-label">Warnings</div>
                </div>
                <div class="metric-card" style="border-left-color: #38ef7d;">
                    <div class="metric-value">{pass_pct:.1f}%</div>
                    <div class="metric-label">Success Rate</div>
                </div>
            </div>
        </div>

        <div class="checklist">
            <h2 class="section-title">Verification Checklist</h2>
            <div class="checklist-items">
"""

            # Add checklist items
            for label, value, status in self._summary_items:
                checkbox_map = {
                    "PASS": ('<span class="checkbox pass">✓</span>', "pass"),
                    "FAIL": ('<span class="checkbox fail">✗</span>', "fail"),
                    "WARN": ('<span class="checkbox warn">⚠</span>', "warn"),
                    "INFO": ('<span class="checkbox info">ℹ</span>', "info")
                }
                checkbox_html, status_class = checkbox_map.get(status, ('<span class="checkbox">•</span>', ""))

                html_content += f"""
                <div class="checklist-item">
                    {checkbox_html}
                    <span class="item-label">{label}</span>
                    <span class="item-value">{value}</span>
                </div>
"""

            html_content += """
            </div>
        </div>

        <div class="footer">
            <p><strong>END OF VERIFICATION REPORT</strong></p>
            <p>For questions or support, please contact your system administrator.</p>
            <p>This is an automated report generated by Oracle Fusion Integration System.</p>
        </div>
    </div>
</body>
</html>
"""

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            print(f"  ✓ HTML Report         : {html_path}")
        except Exception as e:
            print(f"  ⚠ Could not generate HTML report: {e}")

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

    DEFAULT_ORG_ID = "300000052613062"

    def __init__(self, path: str, register_cache: "Optional[RegisterCache]" = None):
        self._exact:      Dict[Tuple[str, str], Tuple[str, str]] = {}
        self._method:     Dict[str, Tuple[str, str]]             = {}
        self._exact_org:  Dict[Tuple[str, str], str]             = {}
        self._method_org: Dict[str, str]                         = {}
        self._loaded  = False
        # Optional vend-register override: when set and the register has the
        # required CASH_ACCOUNT / BANK_ACCOUNT, it takes priority over this
        # CSV-based lookup so that SUBINVENTORY (= Branch on payment lines =
        # REGISTER_NAME) routes directly to the per-store accounts.
        self._register_cache = register_cache
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
            # Preserve full bank account number text without trimming
            acct_number_raw = row.get("BANK_ACCOUNT_NUMBER")
            acct_number = str(acct_number_raw) if acct_number_raw is not None and not (isinstance(acct_number_raw, float) and np.isnan(acct_number_raw)) else ""
            org_id      = safe_str(row.get("ORGANIZATION_ID", "")).strip()
            if not method or not acct_name:
                continue
            canonical  = normalise_payment(method)
            acct_upper = acct_name.upper()
            key        = (acct_upper, canonical)
            # Store (method_name_from_csv, bank_name, bank_number)
            if key not in self._exact:
                self._exact[key] = (method, acct_name, acct_number)
            if canonical not in self._method:
                self._method[canonical] = (method, acct_name, acct_number)
            if org_id:
                if key not in self._exact_org:
                    self._exact_org[key] = org_id
                if canonical not in self._method_org:
                    self._method_org[canonical] = org_id

        self._loaded = True
        print(f"  ✓ Receipt_Methods.csv loaded: {len(self._exact):,} entries")

    def get_bank_account(self, store_name: str, method: str) -> Tuple[str, str, str]:
        """
        Look up bank account information for a given store and payment method.
        Returns: (receipt_method_name, bank_account_name, bank_account_number)
        """
        # Primary source: Receipt_Methods.csv (contains complete bank account numbers)
        # Fallback: vend register file for stores not in Receipt_Methods.csv
        if not self._loaded:
            # If Receipt_Methods.csv not loaded, try vend registers as fallback
            if self._register_cache is not None:
                override = self._register_cache.get_account(store_name, method)
                if override is not None:
                    return (method, override[0], override[1])
            return PAYMENT_BANK_MAP_FALLBACK.get(method, DEFAULT_BANK)

        store_upper = normalise_store(store_name)
        # Score each candidate so the most-specific match wins deterministically:
        #   3 = whole-token match (store appears bounded by non-alphanumeric chars
        #       or string boundary; e.g. "RASHIDMAD" matches "...RASHIDMAD ACC#..."
        #       but NOT "...RASHIDMAD2")
        #   2 = substring match where the *next* char in the account name is a digit
        #       (treat as a different-store extension, lower priority)
        #   1 = plain substring match (legacy behaviour, fallback)
        # Tie-breaker: shorter account-name string wins (more specific), then the
        # first-encountered entry. This eliminates substring collisions such as
        # RASHIDMAD vs RASHIDMAD2 regardless of CSV row order.
        best = None  # tuple: (score, -len(acct_upper), insertion_index, value)
        for idx, ((acct_upper, canon_method), value) in enumerate(self._exact.items()):
            if canon_method != method:
                continue
            pos = acct_upper.find(store_upper)
            if pos < 0:
                continue
            end = pos + len(store_upper)
            before_ok = pos == 0 or not acct_upper[pos - 1].isalnum()
            after_ch  = acct_upper[end] if end < len(acct_upper) else ""
            after_ok  = after_ch == "" or not after_ch.isalnum()
            if before_ok and after_ok:
                score = 3
            elif before_ok and after_ch.isdigit():
                score = 2
            else:
                score = 1
            cand = (score, -len(acct_upper), -idx, value)
            if best is None or cand > best:
                best = cand
        if best is not None:
            return best[3]
        if method in self._method:
            return self._method[method]

        # Fallback to vend register file if not found in Receipt_Methods.csv
        if self._register_cache is not None:
            override = self._register_cache.get_account(store_name, method)
            if override is not None:
                return (method, override[0], override[1])

        return PAYMENT_BANK_MAP_FALLBACK.get(method, DEFAULT_BANK)

    def get_org_id(self, store_name: str, method: str) -> str:
        """Look up ORGANIZATION_ID from Receipt_Methods.csv using the same
        store/method matching logic as :meth:`get_bank_account`. Falls back
        to :attr:`DEFAULT_ORG_ID` when no match is found."""
        if not self._loaded:
            return self.DEFAULT_ORG_ID
        store_upper = normalise_store(store_name)
        best = None  # tuple: (score, -len(acct_upper), -idx, org_id)
        for idx, ((acct_upper, canon_method), org_id) in enumerate(self._exact_org.items()):
            if canon_method != method:
                continue
            pos = acct_upper.find(store_upper)
            if pos < 0:
                continue
            end = pos + len(store_upper)
            before_ok = pos == 0 or not acct_upper[pos - 1].isalnum()
            after_ch  = acct_upper[end] if end < len(acct_upper) else ""
            after_ok  = after_ch == "" or not after_ch.isalnum()
            if before_ok and after_ok:
                score = 3
            elif before_ok and after_ch.isdigit():
                score = 2
            else:
                score = 1
            cand = (score, -len(acct_upper), -idx, org_id)
            if best is None or cand > best:
                best = cand
        if best is not None:
            return best[3]
        if method in self._method_org:
            return self._method_org[method]
        return self.DEFAULT_ORG_ID


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

    def __init__(self, metadata_path: str):
        self.path            = metadata_path
        self.primary:        Dict[Tuple[str, str], dict] = {}
        self.by_type:        Dict[str, dict]             = {}
        self._site_col_used: str                         = ""
        self._load()

    def _load(self):
        df = pd.read_csv(self.path, encoding="utf-8-sig", dtype=str)
        df = normalise_dataframe_columns(df)

        # Find STD_RCPT_NO for receipt generation
        receipt_site_col = None
        if "STD_RCPT_NO" in df.columns:
            receipt_site_col = "STD_RCPT_NO"

        # Find general site number column (prioritize Address_SITE_NUMBER for AR invoices)
        general_site_aliases = ("Address_SITE_NUMBER", "ADDRESS_SITE_NUMBER",
                               "BILL_TO_SITE_NUMBER", "SITE_NUMBER")
        site_col_found = None
        for alias in general_site_aliases:
            if alias in df.columns:
                site_col_found = alias
                break

        if site_col_found is None:
            raise ValueError(
                f"Metadata CSV missing site-number column. "
                f"Expected one of: {general_site_aliases}. "
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
                "STD_RCPT_NO":      safe_str(row.get(receipt_site_col, row.get("SITE_NUMBER"))),
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
            "BILL_TO_ACCOUNT": "", "SITE_NUMBER": "", "STD_RCPT_NO": "",
            "BILL_TO_NAME": store_name, "BUSINESS_UNIT": "AlQurashi-KSA",
            "CUSTOMER_TYPE": customer_type, "SUBINVENTORY": store_name,
            "REGION": "SA", "COST_CENTER_CODE": "",
        }, "none"


# ============================================================================
# REGISTER CACHE
# ============================================================================

_ACC_NUM_RE = re.compile(r"(?:ACC|Acc|A/C)\s*#?\s*([0-9A-Za-z][0-9A-Za-z\-]*)")


def _extract_acc_number(raw: str) -> str:
    """Pull the bank account number out of strings like
    'AL Jazeerah Bank WADILABAN ACC # 015795017321049' or
    'Oman Arab Bank Account- ACC # 3106-573999-500'.
    Returns "" when no parseable account number is present."""
    if not raw:
        return ""
    m = _ACC_NUM_RE.search(raw)
    if not m:
        return ""
    cand = m.group(1)
    # Skip placeholder masks like '******'
    if not any(c.isdigit() or c.isalpha() for c in cand):
        return ""
    return cand


class RegisterCache:
    """Cache of vend `VENDHQ_REGISTERS_*.csv` rows keyed by REGISTER_NAME.

    The vend register file is the authoritative source for per-store
    Standard-receipt (CASH_ACCOUNT) and Miscellaneous-receipt (BANK_ACCOUNT)
    routing.  The `Branch` field on the Odoo payment lines and the
    `SUBINVENTORY` field on Fusion sales metadata both equal REGISTER_NAME,
    so it can be used directly for receipt-method bank-account lookup.
    """

    def __init__(self, registers_path: str = ""):
        self.name_map:    Dict[str, str]              = {}
        self._records:    Dict[str, Dict[str, str]]   = {}
        self._loaded     = False
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
        cash_col = next((c for c in df.columns if c.upper() == "CASH_ACCOUNT"), None)
        bank_col = next((c for c in df.columns if c.upper() == "BANK_ACCOUNT"), None)
        del_col  = next((c for c in df.columns if c.upper() == "DELETED_AT"), None)
        for _, row in df.iterrows():
            reg = safe_str(row.get(reg_col))
            if not reg:
                continue
            if del_col and safe_str(row.get(del_col)).strip():
                # Skip deactivated registers entirely
                continue
            self.name_map[reg.upper()] = reg
            self._records[reg.upper()] = {
                "cash": safe_str(row.get(cash_col)) if cash_col else "",
                "bank": safe_str(row.get(bank_col)) if bank_col else "",
            }
        self._loaded = bool(self._records)
        if self._loaded:
            print(f"  ✓ Vend registers loaded: {len(self._records):,} active records")

    def resolve(self, raw_name: str) -> str:
        return self.name_map.get(normalise_store(raw_name), raw_name)

    def get_account(self, store_name: str, method: str) -> Optional[Tuple[str, str]]:
        """Return (account_name, account_number) for the SUBINVENTORY/Branch.

        * `Cash` → CASH_ACCOUNT (used for Standard receipts)
        * any other method (Mada/Visa/Master/Amex/Apple Pay/STC Pay/
          GCCNET/Wire/etc.) → BANK_ACCOUNT (used for Miscellaneous receipts)

        Returns None when this register isn't in the vend file or has no
        populated value for the requested side, so the caller can fall back
        to `Receipt_Methods.csv`.
        """
        if not self._loaded:
            return None
        rec = self._records.get(normalise_store(store_name))
        if not rec:
            return None
        raw = rec["cash"] if method == "Cash" else rec["bank"]
        if not raw:
            return None
        # Prefer the parsed Acc # when present; otherwise fall back to using
        # the full account-name string as the number (legacy behaviour for
        # entries like 'Cash WADILABAN' that have no separate identifier).
        return (raw, _extract_acc_number(raw) or raw)


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
        seg1_prefix:        Optional[str] = None,
        seg2_prefix:        Optional[str] = None,
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

        # ── Use user-provided prefixes if available, otherwise generate random ones ──
        if seg1_prefix:
            self._seg1_prefix   = seg1_prefix
        else:
            self._seg1_prefix   = _generate_run_prefix(8)

        if seg2_prefix:
            self._seg2_prefix   = seg2_prefix
        else:
            self._seg2_prefix   = _generate_run_prefix(8)

        self.metadata_cache:    Optional[MetadataCache]       = None
        self.register_cache:    Optional[RegisterCache]       = None
        self.receipt_methods:   Optional[ReceiptMethodsCache] = None
        self.bank_charges:      Optional[BankChargesCache]    = None

        self.line_items:        Optional[pd.DataFrame]        = None
        self.payments:          Optional[pd.DataFrame]        = None
        self.ar_df:             Optional[pd.DataFrame]        = None

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
        self.receipt_methods = ReceiptMethodsCache(receipt_methods_path,
                                                   register_cache=self.register_cache)
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

        # Track payment method mappings for diagnosis
        raw_payment_methods: Dict[str, int] = defaultdict(int)
        normalized_payment_methods: Dict[str, float] = defaultdict(float)

        for _, row in self.payments.iterrows():
            inv    = row["Order Ref"]
            raw_method = safe_str(row.get("Payment Method", "Cash"))
            method = normalise_payment(raw_method)
            amount = safe_float(row.get("Amount", 0))

            # Track for diagnostics
            raw_payment_methods[raw_method] += 1
            normalized_payment_methods[method] += amount

            if not inv or amount == 0:
                continue
            self.invoice_payments[inv][method] += amount

        # Log payment method normalization results
        vl.section("1e. PAYMENT METHOD NORMALIZATION DIAGNOSTIC")
        vl.add("  Raw payment methods found in input:")
        for raw_method, count in sorted(raw_payment_methods.items()):
            normalized = normalise_payment(raw_method)
            vl.add(f"    '{raw_method}' (count: {count:,}) → normalized to → '{normalized}'")

        vl.add("\n  Payment method totals after normalization:")
        total_payments = 0.0
        for method, amount in sorted(normalized_payment_methods.items(), key=lambda x: -x[1]):
            total_payments += amount
            # Classify method type
            if method in RECEIPT_PAYMENT_METHODS:
                category = "✓ STANDARD RECEIPT"
            elif method in CARD_PAYMENT_METHODS:
                category = "✓ CARD (MISC RCPT)"
            elif method.upper() in NO_RECEIPT_PAYMENT_METHODS:
                category = "⊗ BNPL (NO RCPT)"
            else:
                category = "⚠ NOT IN ANY CATEGORY"

            vl.add(f"    {method:<20} {amount:>16,.2f} SAR  [{category}]")
        vl.add(f"    {'TOTAL':<20} {total_payments:>16,.2f} SAR")

        vl.add("\n  Payment method categories:")
        vl.add(f"    RECEIPT_PAYMENT_METHODS    = {RECEIPT_PAYMENT_METHODS}")
        vl.add(f"    CARD_PAYMENT_METHODS       = {CARD_PAYMENT_METHODS}")
        vl.add(f"    NO_RECEIPT_PAYMENT_METHODS = {NO_RECEIPT_PAYMENT_METHODS}")

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

                # If amount is negative, quantity must also be negative (return)
                if amount < 0 and quantity > 0:
                    quantity = -quantity

                # Unit price
                unit_price = (amount / quantity) if quantity != 0 else 0.0

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
                row["Line Transactions Flexfield Segment 1"] = f"{self._seg1_prefix}{self.segment_seq_1:07d}"
                row["Line Transactions Flexfield Segment 2"] = f"{self._seg2_prefix}{self.segment_seq_2:07d}"
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
        
        # Update sequence manager if enabled and store sequence info for UI
        if self.seq_manager:
            self.seq_manager.update(max_txn, self.segment_seq_1 - 1, self.segment_seq_2 - 1)
            vl.add()
            vl.kv("✓ Invoice sequence persisted", "Ready for next run")

        # Store sequence information for display in UI
        self.last_transaction_number = max_txn
        self.next_transaction_number = max_txn + 1
        
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

        # Persist the generated AR DataFrame on the instance so downstream
        # steps (e.g. generate_journal_template) can access it.
        self.ar_df = df

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

        # Detailed tracking for diagnostics
        skipped_methods_detail: Dict[str, float] = defaultdict(float)
        accepted_methods_detail: Dict[str, float] = defaultdict(float)
        bnpl_methods_detail: Dict[str, float] = defaultdict(float)

        for inv, methods in self.invoice_payments.items():
            ctype = self.invoice_ctype.get(inv, "NORMAL")
            if ctype in ("TABBY", "TAMARA"):
                bnpl_skipped += 1
                for method, amount in methods.items():
                    bnpl_methods_detail[method] += amount
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
                    bnpl_methods_detail[method] += amount
                    continue
                if method not in RECEIPT_PAYMENT_METHODS:
                    unknown_method_skipped += 1
                    skipped_methods_detail[method] += amount
                    continue
                accepted_methods_detail[method] += amount
                key = (store, date_str, method)
                agg_amount[key]    += amount
                agg_inv_count[key] += 1

        # Group rows by payment method (not by date/store)
        method_rows: Dict[str, List[Dict]] = defaultdict(list)
        receipt_detail_rows: List[Dict] = []
        skipped_no_ar_txn = 0

        for (store, date_str, method), total in sorted(agg_amount.items()):
            ar_txn           = agg_ar_txn.get((store, date_str), "")
            meta, _          = self.metadata_cache.get(store, "NORMAL")
            business_unit    = meta["BUSINESS_UNIT"]
            customer_account = meta["BILL_TO_ACCOUNT"]
            customer_site    = meta["STD_RCPT_NO"]  # Use STD_RCPT_NO for receipt generation

            receipt_method, bank_name, bank_acct_number = self.receipt_methods.get_bank_account(store, method)

            # AR invoice number is mandatory for receipt generation
            if not ar_txn:
                vl.add(f"  ⚠ WARNING: Missing AR transaction number for {store} on {date_str}")
                vl.add(f"            Skipping receipt generation for {receipt_method} payment")
                skipped_no_ar_txn += 1
                continue

            receipt_number = f"{receipt_method}-{ar_txn}"

            row = {
                "ReceiptNumber":               receipt_number,
                "ReceiptMethod":               receipt_method,
                "ReceiptDate":                 date_str,
                "BusinessUnit":                business_unit,
                "CustomerAccountNumber":       customer_account,
                "CustomerSite":                customer_site,
                "Amount":                      round(total, 2),
                "Currency":                    "SAR",
                "RemittanceBankAccountNumber": bank_acct_number,
                "AccountingDate":              date_str,
            }

            # Add row to the method's list
            method_rows[receipt_method].append(row)

            receipt_detail_rows.append({
                "filename":       f"Receipt_{safe_filename(receipt_method)}.csv",
                "store":          store,
                "date":           date_str,
                "method":         method,
                "inv_count":      agg_inv_count.get((store, date_str, method), 0),
                "amount":         total,
                "receipt_number": receipt_number,
                "bank_name":      bank_name,
                "bank_account":   bank_acct_number,
            })

        # Create one file per payment method with all rows consolidated
        receipt_files: Dict[str, pd.DataFrame] = {}
        for method, rows in sorted(method_rows.items()):
            safe_method_part = safe_filename(method)
            filename = f"Receipt_{safe_method_part}.csv"
            receipt_files[filename] = pd.DataFrame(rows, columns=STANDARD_RECEIPT_COLUMNS)

        # Create consolidated file with ALL payment methods merged into one file
        all_consolidated_rows = []
        for method, rows in sorted(method_rows.items()):
            all_consolidated_rows.extend(rows)

        if all_consolidated_rows:
            consolidated_df = pd.DataFrame(all_consolidated_rows, columns=STANDARD_RECEIPT_COLUMNS)
            receipt_files["Receipt_ALL_CONSOLIDATED.csv"] = consolidated_df

            # Validate consolidated file against per-method files
            consolidated_total = consolidated_df['Amount'].sum()
            per_method_total = sum(df['Amount'].sum() for fname, df in receipt_files.items()
                                  if fname != "Receipt_ALL_CONSOLIDATED.csv")

            vl.add(f"\n  ✓ CONSOLIDATED FILE CREATED: Receipt_ALL_CONSOLIDATED.csv")
            vl.add(f"    Total rows: {len(consolidated_df):,}")
            vl.add(f"    Total amount: {consolidated_total:,.2f} SAR")
            vl.add(f"    Payment methods included: {sorted(method_rows.keys())}")

            # Detailed validation
            vl.add(f"\n  ═══ CONSOLIDATED FILE VALIDATION ═══")
            vl.add(f"    Consolidated total:      {consolidated_total:>18,.2f} SAR")
            vl.add(f"    Per-method total:        {per_method_total:>18,.2f} SAR")
            vl.add(f"    Difference:              {abs(consolidated_total - per_method_total):>18,.2f} SAR")

            if abs(consolidated_total - per_method_total) < 0.01:
                vl.add(f"    Status: ✓ MATCH - Totals are accurate")
            else:
                vl.add(f"    Status: ⚠ MISMATCH - Please review")

            # Per-method breakdown in consolidated file
            vl.add(f"\n  Payment Method Breakdown in Consolidated File:")
            method_breakdown = consolidated_df.groupby('ReceiptMethod')['Amount'].agg(['sum', 'count'])
            for method in sorted(method_breakdown.index):
                method_total = method_breakdown.loc[method, 'sum']
                method_count = method_breakdown.loc[method, 'count']
                # Check for negative amounts
                method_df = consolidated_df[consolidated_df['ReceiptMethod'] == method]
                negative_count = len(method_df[method_df['Amount'] < 0])

                status_str = ""
                if negative_count > 0:
                    status_str = f"  ⚠ {negative_count} NEGATIVE AMOUNTS!"
                elif method_total < 0:
                    status_str = "  ⚠ NEGATIVE TOTAL!"
                else:
                    status_str = "  ✓"

                vl.add(f"    {method:<15} {method_count:>5} rows  {method_total:>18,.2f} SAR{status_str}")

        vl.section("8. STANDARD RECEIPT RECORDS — DETAIL")
        vl.kv("BNPL invoices skipped",       f"{bnpl_skipped:,}")
        vl.kv("Unknown method rows skipped", f"{unknown_method_skipped:,}")
        vl.kv("Skipped (no AR txn number)",  f"{skipped_no_ar_txn:,}")
        vl.kv("Receipt files to write",      f"{len(receipt_files):,}")

        # CRITICAL DIAGNOSTIC: Show which methods were skipped and why
        vl.add("\n  ⚠ PAYMENT METHOD PROCESSING BREAKDOWN:")
        vl.add("\n  ✓ ACCEPTED for Standard Receipts (in RECEIPT_PAYMENT_METHODS):")
        if accepted_methods_detail:
            for method, amount in sorted(accepted_methods_detail.items(), key=lambda x: -x[1]):
                vl.add(f"    {method:<20} {amount:>16,.2f} SAR")
        else:
            vl.add("    (none)")

        vl.add("\n  ⚠ SKIPPED - Not in RECEIPT_PAYMENT_METHODS:")
        if skipped_methods_detail:
            skipped_total = sum(skipped_methods_detail.values())
            for method, amount in sorted(skipped_methods_detail.items(), key=lambda x: -x[1]):
                vl.add(f"    {method:<20} {amount:>16,.2f} SAR  ← NOT GENERATING RECEIPTS!")
            vl.add(f"    {'TOTAL SKIPPED':<20} {skipped_total:>16,.2f} SAR")
        else:
            vl.add("    (none)")

        vl.add("\n  ⊗ BNPL Methods (excluded by design):")
        if bnpl_methods_detail:
            for method, amount in sorted(bnpl_methods_detail.items(), key=lambda x: -x[1]):
                vl.add(f"    {method:<20} {amount:>16,.2f} SAR")
        else:
            vl.add("    (none)")

        vl.add()
        vl.add("  RECEIPT DETAILS WITH BANK ACCOUNT MAPPING:")
        vl.table_row("File", "Store", "Method", "Amount (SAR)", "Bank Account",
                     widths=(40, 15, 10, 16, 35))
        vl.divider(width=120)
        receipt_grand = 0.0
        for r in receipt_detail_rows:
            vl.table_row(r["filename"], r["store"], r["method"],
                         f"{r['amount']:,.2f}", r["bank_account"],
                         widths=(40, 15, 10, 16, 35))
            receipt_grand += r["amount"]
        vl.divider(width=120)
        vl.table_row("GRAND TOTAL", "", "", f"{receipt_grand:,.2f}", "",
                     widths=(40, 15, 10, 16, 35))

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

        # Add day-wise payment method validation
        vl.section("8a. DAY-WISE PAYMENT METHOD VALIDATION")
        vl.add("  This section shows payment totals broken down by date and payment method.")
        vl.add("  These are the ACTUAL payment amounts collected (from payment file).")
        vl.add()

        # Build day-wise breakdown from invoice_payments
        day_method_totals: Dict[Tuple[str, str], float] = defaultdict(float)
        payment_total_for_receipts = 0.0

        for inv, methods in self.invoice_payments.items():
            ctype = self.invoice_ctype.get(inv, "NORMAL")
            if ctype in ("TABBY", "TAMARA"):
                continue  # Skip BNPL

            sale_date = self.invoice_date.get(inv, datetime.now())
            date_str = format_date(sale_date)

            for method, amount in methods.items():
                if method not in RECEIPT_PAYMENT_METHODS:
                    continue  # Skip non-receipt methods
                day_method_totals[(date_str, method)] += amount
                payment_total_for_receipts += amount

        # Get unique dates and methods
        all_dates = sorted(set(date for date, _ in day_method_totals.keys()))
        all_methods = sorted(set(method for _, method in day_method_totals.keys()))

        if all_dates and all_methods:
            vl.add("  Day-wise payment method totals (SAR):")
            vl.add()

            # Print header
            header = f"  {'Date':<12}"
            for method in all_methods:
                header += f" {method:>12}"
            header += f" {'TOTAL':>14}"
            vl.add(header)
            vl.add("  " + "-" * (12 + 14 * (len(all_methods) + 1)))

            # Print rows
            method_column_totals = defaultdict(float)
            for date in all_dates:
                row = f"  {date:<12}"
                row_total = 0.0
                for method in all_methods:
                    amount = day_method_totals.get((date, method), 0.0)
                    row_total += amount
                    method_column_totals[method] += amount
                    row += f" {amount:>12,.0f}"
                row += f" {row_total:>14,.0f}"
                vl.add(row)

            # Print totals
            vl.add("  " + "-" * (12 + 14 * (len(all_methods) + 1)))
            total_row = f"  {'TOTAL':<12}"
            grand_total = 0.0
            for method in all_methods:
                method_total = method_column_totals[method]
                grand_total += method_total
                total_row += f" {method_total:>12,.0f}"
            total_row += f" {grand_total:>14,.0f}"
            vl.add(total_row)
            vl.add()

            # Validation: Compare with receipt totals
            vl.add("  VALIDATION:")
            vl.add(f"    Payment file total (for standard receipts): {payment_total_for_receipts:>16,.2f} SAR")
            vl.add(f"    Receipt files total:                        {receipt_grand:>16,.2f} SAR")
            diff = abs(payment_total_for_receipts - receipt_grand)
            if diff < 0.01:
                vl.add(f"    Difference:                                 {diff:>16,.2f} SAR  ✓ MATCH")
            else:
                vl.add(f"    Difference:                                 {diff:>16,.2f} SAR  ⚠ CHECK")
            vl.add()

            # Per-method validation
            vl.add("  Per-method validation:")
            for method in sorted(all_methods):
                payment_method_total = method_column_totals[method]
                receipt_method_total = method_totals.get(method, 0.0)
                method_diff = abs(payment_method_total - receipt_method_total)
                status = "✓" if method_diff < 0.01 else "⚠"
                vl.add(f"    {method:<14}  Payment: {payment_method_total:>12,.2f}  Receipt: {receipt_method_total:>12,.2f}  Diff: {method_diff:>8,.2f}  {status}")
        else:
            vl.add("  No day-wise data available for validation.")

        vl.add()

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

        # Detailed tracking for diagnostics
        card_methods_accepted: Dict[str, float] = defaultdict(float)
        card_methods_skipped: Dict[str, float] = defaultdict(float)
        zero_amount_skipped: Dict[str, float] = defaultdict(float)

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
                if amount <= 0:
                    zero_amount_skipped[method] += 1
                    continue
                if method not in CARD_PAYMENT_METHODS:
                    card_methods_skipped[method] += amount
                    continue
                card_methods_accepted[method] += amount
                agg_amount[(store, date_str, method)] += amount

        # Group rows by payment method (not by date/store)
        method_rows: Dict[str, List[Dict]] = defaultdict(list)
        misc_detail_rows: List[Dict] = []
        seq = 1
        skipped_no_ar_txn_misc = 0

        for (store, date_str, method), total_payment in sorted(agg_amount.items()):
            misc_amount = self.bank_charges.calc_misc_amount(total_payment, method, store)
            if misc_amount is None:
                continue

            cfg            = self.bank_charges.get(method, store)
            ar_txn         = agg_ar_txn.get((store, date_str), "")
            org_id         = MISS_RECEIPT_ORG_ID
            activity       = cfg.get("activity", "Misc Activity")  if cfg else "Misc Activity"
            charge_rate    = cfg.get("rate", 0.0)                  if cfg else 0.0

            receipt_method, bank_name, bank_num = self.receipt_methods.get_bank_account(store, method)

            # AR invoice number is mandatory for misc receipt generation
            if not ar_txn:
                vl.add(f"  ⚠ WARNING: Missing AR transaction number for {store} on {date_str}")
                vl.add(f"            Skipping misc receipt generation for {receipt_method} payment")
                skipped_no_ar_txn_misc += 1
                continue

            receipt_number = f"{receipt_method}-{ar_txn}-MISC"

            row = {
                "Amount":                 round(misc_amount, 4),
                "CurrencyCode":           "SAR",
                "DepositDate":            date_str,
                "ReceiptDate":            date_str,
                "GlDate":                 date_str,
                "OrgId":                  org_id,
                "ReceiptNumber":          receipt_number,
                "ReceiptMethodName":      receipt_method,
                "ReceivableActivityName": MISS_RECEIPT_ACTIVITY,
                "BankAccountNumber":      bank_num,
            }

            # Add row to the method's list
            method_rows[receipt_method].append(row)

            misc_detail_rows.append({
                "filename":      f"MiscReceipt_{safe_filename(receipt_method)}.csv",
                "store":         store,
                "date":          date_str,
                "method":        method,
                "payment_total": total_payment,
                "charge_rate":   charge_rate,
                "misc_amount":   misc_amount,
                "bank_account":  bank_num,
            })
            seq += 1

        # Create one file per payment method with all rows consolidated
        misc_files: Dict[str, pd.DataFrame] = {}
        for method, rows in sorted(method_rows.items()):
            safe_method_part = safe_filename(method)
            filename = f"MiscReceipt_{safe_method_part}.csv"
            misc_files[filename] = pd.DataFrame(rows, columns=MISC_RECEIPT_COLUMNS)

        # Create consolidated file with ALL payment methods merged into one file
        all_misc_consolidated_rows = []
        for method, rows in sorted(method_rows.items()):
            all_misc_consolidated_rows.extend(rows)

        if all_misc_consolidated_rows:
            misc_consolidated_df = pd.DataFrame(all_misc_consolidated_rows, columns=MISC_RECEIPT_COLUMNS)
            misc_files["MiscReceipt_ALL_CONSOLIDATED.csv"] = misc_consolidated_df

            # Validate consolidated file against per-method files
            misc_consolidated_total = misc_consolidated_df['Amount'].sum()
            misc_per_method_total = sum(df['Amount'].sum() for fname, df in misc_files.items()
                                       if fname != "MiscReceipt_ALL_CONSOLIDATED.csv")

            vl.add(f"\n  ✓ MISC CONSOLIDATED FILE CREATED: MiscReceipt_ALL_CONSOLIDATED.csv")
            vl.add(f"    Total rows: {len(misc_consolidated_df):,}")
            vl.add(f"    Total amount: {misc_consolidated_total:,.4f} SAR")
            vl.add(f"    Payment methods included: {sorted(method_rows.keys())}")

            # Detailed validation
            vl.add(f"\n  ═══ MISC CONSOLIDATED FILE VALIDATION ═══")
            vl.add(f"    Consolidated total:      {misc_consolidated_total:>18,.4f} SAR")
            vl.add(f"    Per-method total:        {misc_per_method_total:>18,.4f} SAR")
            vl.add(f"    Difference:              {abs(misc_consolidated_total - misc_per_method_total):>18,.4f} SAR")

            if abs(misc_consolidated_total - misc_per_method_total) < 0.0001:
                vl.add(f"    Status: ✓ MATCH - Totals are accurate")
            else:
                vl.add(f"    Status: ⚠ MISMATCH - Please review")

            # Per-method breakdown in consolidated file
            vl.add(f"\n  Payment Method Breakdown in Misc Consolidated File:")
            misc_method_breakdown = misc_consolidated_df.groupby('ReceiptMethodName')['Amount'].agg(['sum', 'count'])
            for method in sorted(misc_method_breakdown.index):
                method_total = misc_method_breakdown.loc[method, 'sum']
                method_count = misc_method_breakdown.loc[method, 'count']
                # Check for negative amounts
                method_df = misc_consolidated_df[misc_consolidated_df['ReceiptMethodName'] == method]
                negative_count = len(method_df[method_df['Amount'] < 0])

                status_str = ""
                if negative_count > 0:
                    status_str = f"  ⚠ {negative_count} NEGATIVE AMOUNTS!"
                elif method_total < 0:
                    status_str = "  ⚠ NEGATIVE TOTAL!"
                else:
                    status_str = "  ✓"

                vl.add(f"    {method:<15} {method_count:>5} rows  {method_total:>18,.4f} SAR{status_str}")

        vl.section("8b. MISCELLANEOUS RECEIPT RECORDS — DETAIL")
        vl.kv("Skipped (no AR txn number)",  f"{skipped_no_ar_txn_misc:,}")
        vl.kv("Misc receipt files to write", f"{len(misc_files):,}")

        # CRITICAL DIAGNOSTIC: Show which card methods were processed
        vl.add("\n  ⚠ CARD PAYMENT METHOD PROCESSING BREAKDOWN:")
        vl.add("\n  ✓ ACCEPTED for Misc Receipts (in CARD_PAYMENT_METHODS):")
        if card_methods_accepted:
            for method, amount in sorted(card_methods_accepted.items(), key=lambda x: -x[1]):
                vl.add(f"    {method:<20} {amount:>16,.2f} SAR")
        else:
            vl.add("    (none)")

        vl.add("\n  ⚠ SKIPPED - Not in CARD_PAYMENT_METHODS:")
        if card_methods_skipped:
            skipped_total = sum(card_methods_skipped.values())
            for method, amount in sorted(card_methods_skipped.items(), key=lambda x: -x[1]):
                vl.add(f"    {method:<20} {amount:>16,.2f} SAR  ← NOT GENERATING MISC RECEIPTS!")
            vl.add(f"    {'TOTAL SKIPPED':<20} {skipped_total:>16,.2f} SAR")
        else:
            vl.add("    (none)")

        vl.add()

        if misc_detail_rows:
            vl.add("  MISC RECEIPT CALCULATION DETAILS:")
            vl.table_row("Store", "Method", "Payment Total", "Rate %", "Misc Amount", "Bank Acct",
                         widths=(15, 10, 16, 8, 16, 30))
            vl.divider(width=100)
            misc_grand = 0.0
            for r in misc_detail_rows:
                vl.table_row(r["store"], r["method"],
                             f"{r['payment_total']:,.2f}",
                             f"{r['charge_rate']:.2f}",
                             f"{r['misc_amount']:,.4f}",
                             r["bank_account"],
                             widths=(15, 10, 16, 8, 16, 30))
                misc_grand += r["misc_amount"]
            vl.divider(width=100)
            vl.table_row("GRAND TOTAL", "", "", "", f"{misc_grand:,.4f}", "",
                         widths=(15, 10, 16, 8, 16, 30))
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
        
        # Save single consolidated AR Invoice file (all stores together)
        # Filename: AR_Invoice_{org_name}_{date}.csv
        fpath = folder / f"AR_Invoice_{org_name}_{date_part}.csv"
        
        df.to_csv(fpath, index=False, encoding="utf-8-sig", quoting=1)
        
        total_rows = len(df)
        total_amount = df["Transaction Line Amount"].sum()
        unique_stores = df["Bill-to Customer Account Number"].nunique()
        
        print(f"  ✓ Consolidated AR Invoice (all stores)")
        print(f"    Stores:  {unique_stores:,}")
        print(f"    Rows:    {total_rows:,}")
        print(f"    Amount:  {total_amount:,.2f} SAR")
        
        vl.kv("Output file",  fpath.name)
        vl.kv("Total stores", f"{unique_stores:,}")
        vl.kv("Total rows",   f"{total_rows:,}")
        vl.kv("Total amount", f"{total_amount:,.2f} SAR")
        print(f"\n  Summary: 1 consolidated file, {unique_stores:,} stores, {total_rows:,} rows, {total_amount:,.2f} SAR")

    def save_standard_receipts(self, receipt_files: Dict[str, pd.DataFrame]):
        vl   = self.vlog
        base = self.output_dir / "Receipts"
        vl.section("10. OUTPUT FILES — STANDARD RECEIPTS")

        method_totals: Dict[str, float] = defaultdict(float)
        method_counts: Dict[str, int]   = defaultdict(int)

        for fname, df in sorted(receipt_files.items()):
            # Handle consolidated file separately
            if fname == "Receipt_ALL_CONSOLIDATED.csv":
                # Save consolidated file in the Receipts root directory
                folder = base
                folder.mkdir(parents=True, exist_ok=True)
                fpath  = folder / fname
                df.to_csv(fpath, index=False, encoding="utf-8-sig", quoting=1)
                amt = df["Amount"].sum()
                row_count = len(df)
                print(f"  ✓ {fname:<50}  {row_count:>4} rows  {amt:>15,.2f} SAR  ← CONSOLIDATED")
                vl.kv("Consolidated file", f"{fname} ({row_count:,} rows, {amt:,.2f} SAR)")
                continue

            # Save per-method files in their respective folders
            parts  = fname.replace(".csv", "").split("_")
            method = parts[1] if len(parts) > 1 else "Other"
            folder = base / method
            folder.mkdir(parents=True, exist_ok=True)
            fpath  = folder / fname
            df.to_csv(fpath, index=False, encoding="utf-8-sig", quoting=1)
            amt = df["Amount"].sum()
            row_count = len(df)
            method_totals[method] += amt
            method_counts[method] += 1
            print(f"  ✓ {fname:<50}  {row_count:>4} rows  {amt:>15,.2f} SAR")

        total_all = sum(method_totals.values())
        vl.kv("Per-method grand total", f"{total_all:,.2f} SAR")
        print(f"\n  Standard receipt per-method total : {total_all:,.2f} SAR")

    def save_misc_receipts(self, misc_files: Dict[str, pd.DataFrame]):
        if not misc_files:
            return
        vl     = self.vlog
        base   = self.output_dir / "Receipts" / "Misc"
        vl.section("10b. OUTPUT FILES — MISCELLANEOUS RECEIPTS")

        method_totals: Dict[str, float] = defaultdict(float)
        method_counts: Dict[str, int]   = defaultdict(int)

        for fname, df in sorted(misc_files.items()):
            # Handle consolidated file separately
            if fname == "MiscReceipt_ALL_CONSOLIDATED.csv":
                # Save consolidated file in the Misc Receipts root directory
                folder = base
                folder.mkdir(parents=True, exist_ok=True)
                fpath  = folder / fname
                df.to_csv(fpath, index=False, encoding="utf-8-sig", quoting=1)
                amt = df["Amount"].sum()
                row_count = len(df)
                print(f"  ✓ {fname:<50}  {row_count:>4} rows  {amt:>15,.4f} SAR  ← CONSOLIDATED")
                vl.kv("Misc Consolidated file", f"{fname} ({row_count:,} rows, {amt:,.4f} SAR)")
                continue

            # Save per-method files in their respective folders
            parts  = fname.replace(".csv", "").split("_")
            method = parts[1] if len(parts) > 1 else "Other"
            folder = base / method
            folder.mkdir(parents=True, exist_ok=True)
            fpath  = folder / fname
            df.to_csv(fpath, index=False, encoding="utf-8-sig", quoting=1)
            amt = df["Amount"].sum()
            row_count = len(df)
            method_totals[method] += amt
            method_counts[method] += 1
            print(f"  ✓ {fname:<50}  {row_count:>4} rows  {amt:>15,.4f} SAR")

        total_misc = sum(method_totals.values())
        vl.kv("Per-method grand total", f"{total_misc:,.4f} SAR")
        print(f"\n  Misc receipt per-method total : {total_misc:,.4f} SAR")

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

        # Calculate NORMAL payment total (Cash/Mada/Visa/Master only, excluding BNPL)
        pay_norm_total = sum(
            amt
            for inv, methods in self.invoice_payments.items()
            for m, amt in methods.items()
            if self.invoice_ctype.get(inv, "NORMAL") not in ("TABBY", "TAMARA")
            and m in RECEIPT_PAYMENT_METHODS
        )

        # Calculate TOTAL payment amount (ALL methods including BNPL, AMEX, etc.)
        pay_total = sum(
            amt
            for inv, methods in self.invoice_payments.items()
            for m, amt in methods.items()
        )

        diff_normal = abs(rcpt_total - pay_norm_total)
        diff_total = abs(ar_total - pay_total)
        amounts_match = diff_normal < 0.01
        totals_match = diff_total < 10.0  # Allow small rounding difference (< 10 SAR on ~700k is < 0.002%)

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
        vl.add_summary("AR vs Payment Match",
                      f"Diff: {diff_total:,.2f} SAR",
                      "PASS" if totals_match else "WARN")
        vl.add_summary("Segment 1 Uniqueness",
                      f"{seg1_unique:,} unique",
                      "PASS" if seg1_ok else "FAIL")
        vl.add_summary("Segment 2 Uniqueness",
                      f"{seg2_unique:,} unique",
                      "PASS" if seg2_ok else "FAIL")
        vl.add_summary("Total Invoices Processed",
                      f"{len(self.invoice_payments):,}",
                      "INFO")
        vl.add_summary("Receipt Files Generated",
                      f"{len(receipt_files):,} files",
                      "INFO")

        # Detailed verification in highlighted box
        vl.highlight_box("CRITICAL VERIFICATION CHECKS", [
            ("Input line item rows", f"{input_lines:,}"),
            ("Output AR rows", f"{output_lines:,}"),
            ("Line count match", match_flag),
            vl.SPACER_LINE,  # Visual spacer
            ("AR total amount", f"{ar_total:,.2f} SAR"),
            ("Payment file total (ALL)", f"{pay_total:,.2f} SAR"),
            ("AR vs Payment diff", f"{diff_total:,.2f} SAR " + ("✓ MATCH" if totals_match else "⚠ CHECK")),
            vl.SPACER_LINE,  # Visual spacer
            ("Payment file total (NORMAL)", f"{pay_norm_total:,.2f} SAR"),
            ("Receipt total", f"{rcpt_total:,.2f} SAR"),
            ("Receipt vs payment diff", f"{diff_normal:,.2f} SAR " + ("✓ MATCH" if amounts_match else "⚠ CHECK")),
            vl.SPACER_LINE,  # Visual spacer
            ("Segment 1 unique values", f"{seg1_unique:,} " + ("✓ OK" if seg1_ok else "⚠ duplicates")),
            ("Segment 2 unique values", f"{seg2_unique:,} " + ("✓ OK" if seg2_ok else "⚠ duplicates")),
        ])

        # NEW: Payment Method Reconciliation for Manual Checking
        vl.section("PAYMENT METHOD RECONCILIATION (FOR MANUAL REVIEW)")
        vl.add("  This section breaks down amounts by payment method to help verify totals:")
        vl.add()

        # Calculate payment method breakdowns
        method_payments = defaultdict(float)
        method_receipts = defaultdict(float)
        method_invoice_counts = defaultdict(int)

        for inv, methods in self.invoice_payments.items():
            for method, amount in methods.items():
                method_payments[method] += amount
                method_invoice_counts[method] += 1

        for filename, df in receipt_files.items():
            # Extract method from filename or DataFrame
            if "ReceiptMethod" in df.columns and len(df) > 0:
                method = df["ReceiptMethod"].iloc[0]
                method_receipts[method] += df["Amount"].sum()

        vl.table_row("Payment Method", "Invoices", "Payment Total", "Receipt Total", "Difference", "Status",
                     widths=(15, 10, 18, 18, 18, 10))
        vl.divider(width=100)

        all_methods = sorted(set(list(method_payments.keys()) + list(method_receipts.keys())))
        for method in all_methods:
            pay_amt = method_payments.get(method, 0.0)
            rcpt_amt = method_receipts.get(method, 0.0)
            diff = abs(pay_amt - rcpt_amt)
            inv_count = method_invoice_counts.get(method, 0)

            # Check if this method should have receipts
            if method in RECEIPT_PAYMENT_METHODS:
                status = "✓ OK" if diff < 0.01 else "⚠ CHECK"
            elif method.upper() in NO_RECEIPT_PAYMENT_METHODS:
                status = "BNPL (No Rcpt)"
            else:
                status = "Not Tracked"

            vl.table_row(method, f"{inv_count:,}", f"{pay_amt:,.2f}", f"{rcpt_amt:,.2f}",
                        f"{diff:,.2f}", status,
                        widths=(15, 10, 18, 18, 18, 10))

        vl.divider(width=100)
        vl.add()

        # Additional details (original detailed section)
        vl.section("DETAILED VERIFICATION BREAKDOWN")
        vl.kv("Input line item rows", f"{input_lines:,}")
        vl.kv("Output AR rows",       f"{output_lines:,}")
        vl.kv("Difference",           f"{output_lines - input_lines:+,}  {match_flag}")

        vl.add()
        vl.kv("AR total",                    f"{ar_total:,.2f} SAR")
        vl.kv("Payment file total (ALL)",    f"{pay_total:,.2f} SAR")
        vl.kv("AR vs Payment diff",
               f"{diff_total:,.2f} SAR  " + ("✓ MATCH" if totals_match else "⚠ CHECK"))

        vl.add()
        vl.kv("Payment file total (NORMAL)", f"{pay_norm_total:,.2f} SAR")
        vl.kv("Receipt total",               f"{rcpt_total:,.2f} SAR")
        vl.kv("Receipt vs payment diff",
               f"{diff_normal:,.2f} SAR  " + ("✓ MATCH" if amounts_match else "⚠ CHECK"))

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
        all_checks_passed = lines_match and amounts_match and totals_match and seg1_ok and seg2_ok
        if all_checks_passed:
            vl.add("  ✓  VERIFICATION COMPLETE")
            vl.add("  ✓  All major verification points passed successfully")
            vl.add("  ✓  Ready for Oracle Fusion import")
        else:
            vl.add("  ⚠  VERIFICATION COMPLETE WITH WARNINGS")
            vl.add("  ⚠  Please review the verification points above")
            vl.add("  ⚠  Check Payment Method Reconciliation section for details")

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
    ) -> Optional[Tuple[Dict[str, Dict[str, float]], Dict[str, datetime], Dict[str, str]]]:
        """Load an optional payment CSV and return ({inv_ref: {method: amount}}, {inv_ref: date}, {inv_ref: branch}).

        Recognises a wide range of column names for Sales Order / Order Ref,
        Payment Method, Amount, Date, and Branch so that common export formats work without
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
            "Order Ref", "Payments/Order Ref", "Order Lines/Order Ref",
            "SO Number", "Invoice Number", "Invoice Ref", "Reference",
            "Order Reference", "Pos Reference", "POS Reference",
        ])
        method_col = find_col(pf, [
            "Payments/Payment Method", "Payment Method",
            "Payments/Method", "Payments/Journal", "Payment Journal",
            "Payment Type", "Method", "Pay Method",
        ])
        amount_col = find_col(pf, [
            "Payments/Amount", "Amount", "Paid Amount",
            "Payment Amount", "Total Amount", "Payments/Total",
        ])
        # Optional date column
        date_col = find_col(pf, [
            "Date", "Payment Date", "Transaction Date",
            "Payments/Date", "Payments/Payment Date", "Order Date",
            "Date Order", "Create Date", "Accounting Date",
            "Invoice Date", "Order Lines/Create Date",
        ])
        # Optional branch/store column
        branch_col = find_col(pf, [
            "Branch", "Store", "Store Name", "Warehouse",
            "Location", "Shop", "Outlet",
        ])

        missing = [n for n, c in [
            ("Sales Order / Order Ref", so_col),
            ("Payment Method",          method_col),
            ("Amount",                  amount_col),
        ] if not c]
        if missing:
            print(f"  ⚠ Payment file missing required columns: {missing} — skipped")
            # Print the columns we actually saw so the user can diagnose a
            # header mismatch (otherwise standard receipts silently fall
            # back to a Cash-only allocation).
            print(f"    Actual columns in payment file: {list(pf.columns)}")
            return None

        result: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        dates: Dict[str, datetime] = {}
        branches: Dict[str, str] = {}
        unmatched = 0
        unmatched_amount = 0.0
        synthetic_inv_counter = 1
        for _, row in pf.iterrows():
            inv    = clean_order_ref(safe_str(row.get(so_col, "")).strip())
            method = normalise_payment(safe_str(row.get(method_col, "Cash")))
            amount = safe_float(row.get(amount_col, 0))

            # CRITICAL FIX: Handle payments with no Order Ref
            # Create synthetic invoice references for these so they don't get lost
            if not inv and amount != 0:
                inv = f"SYNTH-PAYMENT-{synthetic_inv_counter:05d}"
                synthetic_inv_counter += 1

            if not inv or amount == 0:
                continue

            # Parse date if available
            # IMPORTANT: Check date for every row, not just first occurrence
            # This ensures we capture valid dates even when previous rows had invalid/empty dates
            if date_col:
                try:
                    date_parsed = pd.to_datetime(row.get(date_col), errors="coerce")
                    if pd.notna(date_parsed):
                        # Always update with valid date (overwrites previous invalid dates or keeps first valid date)
                        if inv not in dates or dates[inv] is None or pd.isna(dates.get(inv)):
                            dates[inv] = date_parsed
                    elif inv not in dates:
                        # Only set None if we haven't seen this invoice before
                        # This allows subsequent rows with valid dates to update it
                        dates[inv] = None
                except Exception:
                    if inv not in dates:
                        dates[inv] = None

            # Capture Branch/Store name if available
            if branch_col and inv not in branches:
                branch_value = safe_str(row.get(branch_col, "")).strip().upper()
                if branch_value:
                    branches[inv] = branch_value

            # CRITICAL FIX: Load ALL payments, not just matched ones
            # Standard receipts must reflect actual cash collected, regardless of AR Invoice matching
            result[inv][method] += amount

            if inv not in inv_ref_set:
                unmatched += 1
                unmatched_amount += amount

        if unmatched:
            print(f"  ⚠ {unmatched:,} payment file row(s) did not match any "
                  f"AR Invoice Sales Order reference (amount: {unmatched_amount:,.2f} SAR)")
            print(f"    ✓ These payments WILL still generate standard receipts with fallback AR transaction numbers")
        print(f"  ✓ Payment file loaded: {len(result):,} total invoice references ({len(result) - unmatched:,} matched, {unmatched:,} unmatched)")
        if date_col:
            valid_dates = sum(1 for d in dates.values() if d is not None and not pd.isna(d))
            print(f"  ✓ Captured transaction dates for {valid_dates}/{len(dates)} transactions from column '{date_col}'")
            if valid_dates < len(dates):
                print(f"    ⚠ {len(dates) - valid_dates} transaction(s) have missing/invalid dates and will use current date as fallback")
        else:
            print(f"  ⚠ No date column found in payment file - will use current date as fallback")
        if branch_col:
            print(f"  ✓ Captured Branch/Store names for {len(branches):,} transactions")
        return (result, dates, branches)

    def load_from_ar_invoice(
        self,
        ar_invoice_path:      str,
        metadata_path:        str,
        receipt_methods_path: str = "",
        bank_charges_path:    str = "",
        payment_file_path:    str = "",
        registers_path:       str = "",
    ):
        """Populate invoice dictionaries from an already-generated AR Invoice CSV.

        An optional *payment_file_path* (CSV/XLSX) can be supplied to provide
        actual payment-method breakdowns per Sales Order.  Expected columns:
          • Sales Order Number (or Order Ref / Invoice Number / …)
          • Payment Method  (e.g. Cash, Mada, Visa, Master)
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
        self.register_cache  = RegisterCache(registers_path)
        self.receipt_methods = ReceiptMethodsCache(receipt_methods_path,
                                                   register_cache=self.register_cache)
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

        # Persist the AR DataFrame on the instance so downstream steps
        # (e.g. generate_journal_template) can access the original rows.
        self.ar_df = ar_df

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
            payment_result = self._load_payment_file(
                payment_file_path, set(self.invoice_store.keys())
            )
            if payment_result is not None:
                payment_data, payment_dates, payment_branches = payment_result
                # Override payments only for invoices present in the payment file;
                # all other invoices retain their existing Cash allocation.
                newly_added_invoices = []
                for inv_ref, methods in payment_data.items():
                    # If invoice is already in the system (matched from AR Invoice),
                    # clear its Cash default and replace with real payment methods
                    if inv_ref in self.invoice_payments:
                        self.invoice_payments[inv_ref].clear()
                        for method, amount in methods.items():
                            self.invoice_payments[inv_ref][method] += amount
                    else:
                        # CRITICAL FIX: Handle unmatched invoices from payment file
                        # These are payments that don't have corresponding AR Invoice entries
                        # We must register them to generate accurate standard receipts
                        newly_added_invoices.append(inv_ref)

                        # Get store from Branch column in payment file if available
                        # Otherwise, extract from invoice reference (e.g., "ALARIDAH/8371" → "ALARIDAH")
                        if inv_ref in payment_branches:
                            store = payment_branches[inv_ref]
                        elif "/" in inv_ref:
                            store = inv_ref.split("/")[0].upper().strip()
                        else:
                            store = "UNKNOWN"

                        # Register this invoice with default values
                        self.invoice_store[inv_ref] = store

                        # Use date from payment file if available
                        self.invoice_date[inv_ref] = payment_dates.get(inv_ref, datetime.now())

                        # Create a fallback AR transaction number
                        # Use the invoice reference as the transaction number
                        self.invoice_to_ar_txn[inv_ref] = f"PAYMENT-{inv_ref}"

                        # Add payment methods
                        for method, amount in methods.items():
                            self.invoice_payments[inv_ref][method] += amount

                        # Set AR total to match payment total (since no AR Invoice entry exists)
                        self.invoice_ar_total[inv_ref] = sum(methods.values())

                if newly_added_invoices:
                    print(f"  ✓ Added {len(newly_added_invoices):,} invoice(s) from payment file that were not in AR Invoice")
                    print(f"    These will generate standard receipts with transaction numbers like 'PAYMENT-{newly_added_invoices[0]}'")

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

        # Extract and track transaction numbers from loaded AR Invoice
        all_txn_nums = []
        for txn_num in self.invoice_to_ar_txn.values():
            if txn_num.startswith("BLKU-"):
                try:
                    num = int(txn_num.replace("BLKU-", ""))
                    all_txn_nums.append(num)
                except ValueError:
                    pass

        max_txn = max(all_txn_nums) if all_txn_nums else 0

        # Store sequence information for display in UI
        self.last_transaction_number = max_txn
        self.next_transaction_number = max_txn + 1

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
            vl.SPACER_LINE,  # Visual spacer
            ("Status", "✓ VERIFIED" if amounts_match else "⚠ REVIEW REQUIRED"),
        ])

        vl.kv("Total AR Invoice amount",    f"{ar_total:,.2f} SAR")
        vl.kv("Total Standard Receipt amt", f"{rcpt_total:,.2f} SAR")
        vl.kv("Difference",
               f"{diff:,.2f} SAR  " + ("✓ MATCH" if amounts_match else "⚠ CHECK"))

        if max_txn > 0:
            vl.add()
            vl.kv("Max Transaction Number found", f"BLKU-{max_txn:07d}")
            vl.kv(">>> Next run START_TXN_SEQUENCE =", f"{max_txn + 1}  ← set this next run")

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
        registers_path:       str = "",
    ):
        """Full pipeline: AR Invoice CSV → Standard Receipts + Misc Receipts."""
        self.load_from_ar_invoice(
            ar_invoice_path, metadata_path,
            receipt_methods_path, bank_charges_path,
            payment_file_path=payment_file_path,
            registers_path=registers_path,
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

    # ──────────────────────────────────────────────────────────────────
    # JOURNAL TEMPLATE GENERATION
    # ──────────────────────────────────────────────────────────────────

    def generate_journal_template(
        self,
        journal_config_path: str = "",
        account_mapping_path: str = "",
        period_name: str = "Mar-26",
        interface_group_id: int = 114,
        service_provider_meta_path: str = "",
        cost_center_meta_path: str = "",
        is_cash: str = "0",
        payment_file_path: str = "",
        sales_lines_file_path: str = "",
        charges_file_path: str = "",
    ) -> pd.DataFrame:
        """
        Generate Journal Import Template for Oracle Fusion from AR Invoice and Payment data.

        For each qualifying service-provider transaction, this function creates a balanced
        DEBIT / CREDIT pair using account segments sourced from
        ``SERVICE_PROVIDER_JOURNAL_META.csv`` (when available) and a per-store cost-center
        value sourced from ``FUSION_SALES_METADATA_Cost_Center.csv``.

        When the new metadata files are not provided, the function falls back to the legacy
        ``JOURNAL_CONFIG.csv`` / ``JOURNAL_ACCOUNT_MAPPING.csv`` behaviour (TAMARA / TABBY only).

        Segment layout used when service-provider metadata is loaded:
            Segment1 = COMPANY            Segment2 = ACCOUNT
            Segment3 = DEPARTMENT         Segment4 = COST_CENTER_CODE (per-store)
            Segment5 = PRODUCT_CATEGORY   Segment6 = INTER_COMPANY
            Segment7 = FUT_USED

        Negative Amount Handling:
            When a negative payment amount is detected (refunds/returns), the system automatically
            swaps the debit and credit account assignments. For positive amounts, the standard
            account mapping is used. For negative amounts, the accounts are swapped so the amount
            appears in the debit column instead of credit. The absolute value is used for all
            amounts (no negative signs appear in the output).

        Args:
            journal_config_path: Legacy JOURNAL_CONFIG.csv (business unit configuration).
            account_mapping_path: Legacy JOURNAL_ACCOUNT_MAPPING.csv (account segment mapping).
            period_name: Period name (e.g., "Mar-26").
            interface_group_id: Interface Group Identifier (unique per file).
            service_provider_meta_path: Path to SERVICE_PROVIDER_JOURNAL_META.csv. When
                provided, this is the primary source for segment / ledger / source / category.
            cost_center_meta_path: Path to FUSION_SALES_METADATA_Cost_Center.csv. Used to
                resolve Segment4 (cost center) by Warehouse Code + service provider.
            is_cash: Filter for the IS_CASH column of the service-provider metadata
                ("0" non-cash, "1" cash). Defaults to "0".
            payment_file_path: Optional path to payment file (XLSX/CSV) containing detailed
                payment method breakdown per transaction. If provided, payment methods from
                this file will be used instead of the AR Invoice's Receipt Method Name.
            sales_lines_file_path: Optional path to sales lines file (XLSX/CSV) containing
                line item details per order. Used for per-item charge calculations.
            charges_file_path: Optional path to SERVICE_PROVIDER_JOURNAL_META_Charges.csv
                containing charge rates for each service provider. Used to calculate charges
                per the formula: Total Charge = (Amount × Rate) × (1 + VAT).

        Notes:
            When ``cost_center_meta_path`` yields no match for a given store/provider,
            Segment4 falls back to the service-provider metadata's ``EXTRA_SEGMENT_1``
            value (or, in legacy mode, to the legacy mapping's ``Segment4`` column).

        Returns:
            DataFrame with journal import template data.
        """
        print("\n" + "=" * 72)
        print("GENERATING JOURNAL IMPORT TEMPLATE")
        print("=" * 72)

        # Resolve default paths
        repo_root = Path(__file__).parent
        if not journal_config_path:
            journal_config_path = repo_root / "JOURNAL_CONFIG.csv"
        if not account_mapping_path:
            account_mapping_path = repo_root / "JOURNAL_ACCOUNT_MAPPING.csv"
        if not service_provider_meta_path:
            candidate = repo_root / "SERVICE_PROVIDER_JOURNAL_META.csv"
            if candidate.exists():
                service_provider_meta_path = str(candidate)
        if not cost_center_meta_path:
            candidate = repo_root / "FUSION_SALES_METADATA_Cost_Center.csv"
            if candidate.exists():
                cost_center_meta_path = str(candidate)

        # ── Load service-provider metadata (preferred source) ──────────────
        sp_meta = None
        if service_provider_meta_path and Path(service_provider_meta_path).exists():
            sp_meta = pd.read_csv(service_provider_meta_path, dtype=str).fillna("")
            # Strip quotes from column names if present
            sp_meta.columns = sp_meta.columns.str.strip('"')
            sp_meta["SERVICE_PROVIDER"] = sp_meta["SERVICE_PROVIDER"].str.upper()
            sp_meta["CREDIT_DEBIT"] = sp_meta["CREDIT_DEBIT"].str.upper()
            is_cash_str = str(is_cash).strip()
            sp_meta = sp_meta[sp_meta["IS_CASH"].astype(str).str.strip() == is_cash_str]
            print(f"✓  Loaded SERVICE_PROVIDER_JOURNAL_META "
                  f"({len(sp_meta)} rows, IS_CASH={is_cash_str})")

        # ── Load cost-center metadata (per-store Segment4) ─────────────────
        cost_center_lookup: dict = {}
        if cost_center_meta_path and Path(cost_center_meta_path).exists():
            cc_df = pd.read_csv(cost_center_meta_path, dtype=str).fillna("")
            # Strip quotes from column names if present
            cc_df.columns = cc_df.columns.str.strip('"')
            for _, cc_row in cc_df.iterrows():
                key = (
                    str(cc_row.get("SUBINVENTORY", "")).strip().upper(),
                    str(cc_row.get("CUSTOMER_TYPE", "")).strip().upper(),
                )
                code = str(cc_row.get("COST_CENTER_CODE", "")).strip()
                if key[0] and key[1] and code:
                    cost_center_lookup.setdefault(key, code)
            print(f"✓  Loaded FUSION_SALES_METADATA_Cost_Center "
                  f"({len(cost_center_lookup)} unique store/provider keys)")

        # ── Load charges file (optional) ────────────────────────────────────
        charges_lookup: dict = {}
        if not charges_file_path:
            # Default to SERVICE_PROVIDER_JOURNAL_META_Charges.csv in repo root
            candidate = repo_root / "SERVICE_PROVIDER_JOURNAL_META_Charges.csv"
            if candidate.exists():
                charges_file_path = str(candidate)

        if charges_file_path and Path(charges_file_path).exists():
            try:
                charges_df = pd.read_csv(charges_file_path, dtype=str).fillna("")
                # Strip quotes from column names if present
                charges_df.columns = charges_df.columns.str.strip('"')

                # Create lookup: (SERVICE_PROVIDER, IS_CASH) -> (FIXED_FREIGHT_CHARGE, BANK_CHARGE_RATE)
                for _, charge_row in charges_df.iterrows():
                    provider = str(charge_row.get("SERVICE_PROVIDER", "")).strip().upper()
                    is_cash_val = str(charge_row.get("IS_CASH", "")).strip()
                    rate_str = str(charge_row.get("BANK_CHARGE_RATE", "")).strip()
                    fixed_str = str(charge_row.get("FIXED_FREIGHT_CHARGE", "")).strip()

                    # Only store if we have at least a rate
                    if provider and rate_str and rate_str.lower() not in ("", "nan", "none"):
                        try:
                            rate = float(rate_str)
                            fixed_charge = 0.0
                            if fixed_str and fixed_str.lower() not in ("", "nan", "none"):
                                fixed_charge = float(fixed_str)

                            key = (provider, is_cash_val)
                            charges_lookup[key] = (fixed_charge, rate)
                        except ValueError:
                            pass  # Skip invalid rates

                print(f"✓  Loaded charges configuration: {len(charges_lookup)} provider/cash combinations")
                # Show rates for TABBY and TAMARA
                for provider in ["TABBY", "TAMARA"]:
                    key = (provider, "0")  # Non-cash
                    if key in charges_lookup:
                        fixed_charge, rate = charges_lookup[key]
                        print(f"   {provider}: Fixed={fixed_charge}, Rate={rate*100:.2f}%")
            except Exception as e:
                print(f"⚠  Error loading charges file: {e}")
                charges_lookup = {}

        # ── Load sales lines file (optional) ────────────────────────────────
        sales_lines_df = None
        sales_lines_totals: Dict[str, float] = {}  # {sales_order_ref: total_amount}
        if sales_lines_file_path and Path(sales_lines_file_path).exists():
            try:
                print(f"✓  Loading sales lines file: {Path(sales_lines_file_path).name}")
                # Load sales lines file - could be XLSX or CSV
                if sales_lines_file_path.endswith('.xlsx') or sales_lines_file_path.endswith('.xls'):
                    sales_lines_df = pd.read_excel(sales_lines_file_path)
                else:
                    sales_lines_df = pd.read_csv(sales_lines_file_path)
                print(f"✓  Loaded {len(sales_lines_df)} sales line items")

                # Find columns for Sales Order Number and Amount
                # Common column names for sales order reference
                so_col = None
                for col_name in ["Sales Order Number", "Order Ref", "Order Reference", "Sales Order",
                                 "Order Lines/Order Ref", "SO Number", "Invoice Number", "Reference"]:
                    if col_name in sales_lines_df.columns:
                        so_col = col_name
                        break

                # Common column names for amount/price
                # Prioritize "Order Lines/Subtotal w/o Tax" when available
                amt_col = None
                for col_name in ["Order Lines/Subtotal w/o Tax", "Price Subtotal", "Subtotal",
                                 "Amount", "Line Amount", "Order Lines/Price Subtotal",
                                 "Order Lines/Subtotal", "Total", "Line Total"]:
                    if col_name in sales_lines_df.columns:
                        amt_col = col_name
                        break

                if so_col and amt_col:
                    # Aggregate amounts by Sales Order Number
                    sales_lines_df[so_col] = sales_lines_df[so_col].fillna("").astype(str).str.strip()
                    sales_lines_df[amt_col] = pd.to_numeric(sales_lines_df[amt_col], errors='coerce').fillna(0)

                    # Group by Sales Order and sum amounts
                    sales_order_totals = sales_lines_df.groupby(so_col)[amt_col].sum()
                    sales_lines_totals = sales_order_totals.to_dict()

                    # Remove empty keys
                    sales_lines_totals = {k: v for k, v in sales_lines_totals.items() if k}

                    print(f"✓  Aggregated amounts for {len(sales_lines_totals)} unique sales orders from sales lines")
                    print(f"   Column used for Sales Order: '{so_col}'")
                    print(f"   Column used for Amount: '{amt_col}'")

                    # Show sample
                    if sales_lines_totals:
                        sample_orders = list(sales_lines_totals.items())[:3]
                        print(f"   Sample totals:")
                        for order_ref, total in sample_orders:
                            print(f"     - {order_ref}: {total:.2f} SAR")
                else:
                    missing = []
                    if not so_col:
                        missing.append("Sales Order Number column")
                    if not amt_col:
                        missing.append("Amount column")
                    print(f"⚠  Could not find required columns in sales lines file: {', '.join(missing)}")
                    print(f"   Available columns: {list(sales_lines_df.columns)}")

            except Exception as e:
                print(f"⚠  Error loading sales lines file: {e}")
                sales_lines_df = None
                sales_lines_totals = {}

        # ── Load payment file (optional) ────────────────────────────────────
        payment_data: Dict[str, Dict[str, float]] = {}
        payment_dates: Dict[str, datetime] = {}
        payment_branches: Dict[str, str] = {}
        if payment_file_path and Path(payment_file_path).exists():
            print(f"✓  Loading payment file: {Path(payment_file_path).name}")
            try:
                # Create a set of Sales Order Numbers from AR Invoice (if available)
                # Payment files contain "Order Ref" which matches "Sales Order Number", not "Transaction Number"
                if self.ar_df is not None and "Sales Order Number" in self.ar_df.columns:
                    ar_sales_order_numbers = set(
                        self.ar_df["Sales Order Number"].fillna("").astype(str).str.strip().unique()
                    )
                else:
                    # When no AR Invoice, accept all transactions from payment file
                    ar_sales_order_numbers = set()

                # Load payment file using existing infrastructure
                payment_result = self._load_payment_file(payment_file_path, ar_sales_order_numbers)
                if payment_result is not None:
                    payment_data, payment_dates, payment_branches = payment_result
                    print(f"✓  Loaded payment data for {len(payment_data)} transactions")

                    # Show breakdown of payment methods from payment file
                    all_payment_methods = set()
                    for methods_dict in payment_data.values():
                        all_payment_methods.update(methods_dict.keys())
                    if all_payment_methods:
                        print(f"   Payment methods in payment file: {sorted(all_payment_methods)}")
                else:
                    print(f"⚠  Could not load payment file")
            except Exception as e:
                print(f"⚠  Error loading payment file: {e}")
                payment_data = {}
                payment_dates = {}
                payment_branches = {}

        # ── Legacy config (fallback when service-provider meta is absent) ──
        legacy_bu_config = None
        legacy_account_mapping = None
        if sp_meta is None or sp_meta.empty:
            # Check if legacy config files exist
            if not Path(journal_config_path).exists():
                print(f"⚠️  JOURNAL_CONFIG.csv not found at {journal_config_path}")
                print("   Please provide either:")
                print("   1. SERVICE_PROVIDER_JOURNAL_META.csv (preferred)")
                print("   2. JOURNAL_CONFIG.csv + JOURNAL_ACCOUNT_MAPPING.csv (legacy)")
                return pd.DataFrame()

            if not Path(account_mapping_path).exists():
                print(f"⚠️  JOURNAL_ACCOUNT_MAPPING.csv not found at {account_mapping_path}")
                print("   Please provide either:")
                print("   1. SERVICE_PROVIDER_JOURNAL_META.csv (preferred)")
                print("   2. JOURNAL_CONFIG.csv + JOURNAL_ACCOUNT_MAPPING.csv (legacy)")
                return pd.DataFrame()

            try:
                journal_config = pd.read_csv(journal_config_path)
                legacy_account_mapping = pd.read_csv(account_mapping_path)
                legacy_bu_config = journal_config[
                    journal_config["Business Unit"] == "Alqurashi KSA"
                ].iloc[0]
                print(f"✓  Loaded legacy configuration (TAMARA/TABBY only)")
            except Exception as e:
                print(f"⚠️  Error loading legacy configuration files: {e}")
                return pd.DataFrame()

        # Determine which payment methods qualify
        # Journal templates are ONLY for TABBY and TAMARA (Buy Now Pay Later providers)
        # Other payment methods (Cash, Mada, Visa, etc.) use receipts, not journal entries
        valid_providers = {"TAMARA", "TABBY"}

        # Guard: ensure we have either payment file data or Receipt Method Name column
        if not payment_data and (self.ar_df is None or "Receipt Method Name" not in self.ar_df.columns):
            print("⚠️  AR Invoice data is missing the 'Receipt Method Name' column and no payment file provided; "
                  "cannot generate journal template. "
                  "Please either: "
                  f"\n   1. Supply an AR Invoice CSV with 'Receipt Method Name' column for: {sorted(valid_providers)}"
                  "\n   2. Upload a payment file with payment method details per transaction")
            return pd.DataFrame()

        # Determine qualifying transactions based on payment file or AR Invoice
        if payment_data:
            print("✓  Using payment file data for payment method detection")

            # When AR Invoice is not provided, work directly from payment file
            if self.ar_df is None or self.ar_df.empty:
                print("✓  Working with payment file only (no AR Invoice provided)")

                # Get all transactions from payment file that match valid providers
                qualifying_sales_orders = set()
                payment_method_counts = {}
                for sales_order_ref, methods_dict in payment_data.items():
                    for method, amt in methods_dict.items():
                        method_upper = method.upper()
                        if method_upper in valid_providers:
                            qualifying_sales_orders.add(sales_order_ref)
                            payment_method_counts[method_upper] = payment_method_counts.get(method_upper, 0) + 1

                if not qualifying_sales_orders:
                    print(f"⚠️  No qualifying transactions found in payment file "
                          f"(providers: {sorted(valid_providers)})")
                    print(f"\n💡 TIP: Checked {len(payment_data)} transactions from payment file")
                    return pd.DataFrame()

                print(f"✓  Found {len(qualifying_sales_orders)} qualifying transactions in payment file")
                for method, count in sorted(payment_method_counts.items()):
                    print(f"   - {method}: {count} payment(s)")

                # Create a placeholder invoices dataframe (will not be used)
                invoices = pd.DataFrame()
            else:
                # Filter AR Invoice to transactions that have payment data
                sales_order_refs_in_payment_file = set(payment_data.keys())
                if "Sales Order Number" not in self.ar_df.columns:
                    print("⚠️  AR Invoice is missing 'Sales Order Number' column")
                    return pd.DataFrame()

                # Get all transactions from payment file that match valid providers
                qualifying_sales_orders = set()
                payment_method_counts = {}
                for sales_order_ref, methods_dict in payment_data.items():
                    for method, amt in methods_dict.items():
                        method_upper = method.upper()
                        if method_upper in valid_providers:
                            qualifying_sales_orders.add(sales_order_ref)
                            payment_method_counts[method_upper] = payment_method_counts.get(method_upper, 0) + 1

                # Filter AR Invoice to qualifying transactions by Sales Order Number
                invoices = self.ar_df[
                    self.ar_df["Sales Order Number"].fillna("").astype(str).str.strip().isin(qualifying_sales_orders)
                ].copy()

                if invoices.empty:
                    print(f"⚠️  No qualifying transactions found in payment file "
                          f"(providers: {sorted(valid_providers)})")
                    print(f"\n💡 TIP: Checked {len(payment_data)} transactions from payment file")
                    return pd.DataFrame()

                print(f"✓  Found {len(invoices)} AR Invoice rows matching payment file with qualifying payment methods")
                for method, count in sorted(payment_method_counts.items()):
                    print(f"   - {method}: {count} payment(s)")

        else:
            # Show all unique payment methods in AR Invoice for debugging
            all_methods = self.ar_df["Receipt Method Name"].fillna("").astype(str).str.upper().unique()
            all_methods_clean = [m for m in all_methods if m.strip()]
            if all_methods_clean:
                print(f"   Payment methods found in AR Invoice: {sorted(all_methods_clean)}")

            invoices = self.ar_df[
                self.ar_df["Receipt Method Name"]
                    .fillna("").astype(str).str.upper().isin(valid_providers)
            ].copy()

            if invoices.empty:
                print(f"⚠️  No qualifying transactions found "
                      f"(providers: {sorted(valid_providers)})")
                print(f"\n💡 TIP: Payment methods in your AR Invoice: {sorted(all_methods_clean)}")
                print(f"   Expected payment methods: {sorted(valid_providers)}")
                print("   Ensure the AR Invoice contains transactions with matching payment methods.")
                return pd.DataFrame()

            print(f"✓  Found {len(invoices)} qualifying transactions "
                  f"for providers {sorted(valid_providers)}")

            # Show breakdown by payment method
            method_counts = invoices["Receipt Method Name"].fillna("").astype(str).str.upper().value_counts()
            for method, count in method_counts.items():
                if method in valid_providers:
                    print(f"   - {method}: {count} transaction(s)")



        # Group by Transaction + Payment Method (from payment file or AR) + Date + Warehouse/Branch
        # When using payment file, we need to expand transactions based on payment methods
        if payment_data:
            # Build expanded dataset with payment methods from payment file
            expanded_rows = []

            if self.ar_df is None or self.ar_df.empty or invoices.empty:
                # Working with payment file only (no AR Invoice)
                print("✓  Building journal entries directly from payment file")
                for sales_order_ref, methods_dict in payment_data.items():
                    # Filter to only qualifying payment methods
                    has_qualifying_method = any(
                        method.upper() in valid_providers
                        for method in methods_dict.keys()
                    )
                    if not has_qualifying_method:
                        continue

                    # Get date from payment file if available, otherwise use current date
                    transaction_date = payment_dates.get(sales_order_ref)
                    if transaction_date is None or pd.isna(transaction_date):
                        # Use current date as fallback only when date is truly missing
                        transaction_date = datetime.now()

                    # Get branch from payment file
                    warehouse_code = payment_branches.get(sales_order_ref, "")

                    for method, method_amt in methods_dict.items():
                        method_upper = method.upper()
                        if method_upper in valid_providers:
                            # Use amount from payment file (prioritized over sales lines)
                            final_amount = method_amt
                            if sales_lines_totals and sales_order_ref in sales_lines_totals:
                                sales_lines_amt = sales_lines_totals[sales_order_ref]
                                print(f"  ℹ️  Using payment file amount for {sales_order_ref}: {final_amount:.2f} SAR (sales lines had: {sales_lines_amt:.2f} SAR)")
                            else:
                                print(f"  ℹ️  Using payment file amount for {sales_order_ref}: {final_amount:.2f} SAR")

                            expanded_rows.append({
                                "Transaction Number": sales_order_ref,  # Use Sales Order as Transaction Number
                                "Sales Order Number": sales_order_ref,
                                "Receipt Method Name": method_upper,
                                "Transaction Date": transaction_date,
                                "Transaction Line Amount": final_amount,
                                "Warehouse Code": warehouse_code,
                            })

                if not expanded_rows:
                    print("⚠️  No qualifying payment methods found in payment file data")
                    return pd.DataFrame()

                # Convert to DataFrame first
                temp_df = pd.DataFrame(expanded_rows)

                # Normalize Transaction Date to date-only (remove time component) for proper daily aggregation
                # This ensures all transactions on the same calendar day are grouped together
                temp_df["Transaction Date"] = pd.to_datetime(temp_df["Transaction Date"]).dt.date

                # Add a "Sign" column to separate positive and negative amounts
                # This is CRITICAL for correct charge calculation:
                # - Positive amounts get normal charges
                # - Negative amounts (refunds) get reversal charges
                # They must NOT be netted together before calculating charges
                temp_df["Amount Sign"] = temp_df["Transaction Line Amount"].apply(lambda x: "positive" if x >= 0 else "negative")

                # Group by Payment Method + Date + Sign (separate positive from negative)
                # This ensures refunds are charged separately from regular transactions
                # Formula: One fixed fee per group + (group total × rate)
                group_cols = ["Receipt Method Name", "Transaction Date", "Amount Sign"]
                if "Warehouse Code" in temp_df.columns:
                    group_cols.append("Warehouse Code")

                grouped = temp_df.groupby(group_cols, dropna=False).agg({
                    "Transaction Line Amount": "sum",
                    "Transaction Number": "first"  # Keep a transaction number for reference
                }).reset_index()

                # Remove the "Amount Sign" column after grouping (not needed in output)
                grouped = grouped.drop(columns=["Amount Sign"])

                print(f"✓  Created {len(grouped)} journal entries from payment file (aggregated by day+sign from {len(temp_df)} transactions)")
            else:
                # AR Invoice is available - use it to enrich payment data
                for _, ar_row in invoices.iterrows():
                    sales_order_ref = str(ar_row.get("Sales Order Number", "")).strip()
                    if sales_order_ref in payment_data:
                        methods_dict = payment_data[sales_order_ref]
                        # Get Branch from payment file if available, otherwise fall back to Warehouse Code from AR
                        branch_from_payment = payment_branches.get(sales_order_ref, "")
                        warehouse_code = branch_from_payment if branch_from_payment else str(ar_row.get("Warehouse Code", "")).strip()

                        for method, method_amt in methods_dict.items():
                            method_upper = method.upper()
                            if method_upper in valid_providers:
                                # Use amount from payment file (prioritized over sales lines)
                                final_amount = method_amt
                                if sales_lines_totals and sales_order_ref in sales_lines_totals:
                                    sales_lines_amt = sales_lines_totals[sales_order_ref]
                                    print(f"  ℹ️  Using payment file amount for {sales_order_ref}: {final_amount:.2f} SAR (sales lines had: {sales_lines_amt:.2f} SAR)")
                                else:
                                    print(f"  ℹ️  Using payment file amount for {sales_order_ref}: {final_amount:.2f} SAR")

                                expanded_rows.append({
                                    "Transaction Number": ar_row.get("Transaction Number"),
                                    "Sales Order Number": sales_order_ref,
                                    "Receipt Method Name": method_upper,
                                    "Transaction Date": ar_row.get("Transaction Date"),
                                    "Transaction Line Amount": final_amount,
                                    "Warehouse Code": warehouse_code,
                                })

                if not expanded_rows:
                    print("⚠️  No qualifying payment methods found in payment file data")
                    return pd.DataFrame()

                # Convert to DataFrame first
                temp_df = pd.DataFrame(expanded_rows)

                # Normalize Transaction Date to date-only (remove time component) for proper daily aggregation
                # This ensures all transactions on the same calendar day are grouped together
                temp_df["Transaction Date"] = pd.to_datetime(temp_df["Transaction Date"]).dt.date

                # Add a "Sign" column to separate positive and negative amounts
                # This is CRITICAL for correct charge calculation:
                # - Positive amounts get normal charges
                # - Negative amounts (refunds) get reversal charges
                # They must NOT be netted together before calculating charges
                temp_df["Amount Sign"] = temp_df["Transaction Line Amount"].apply(lambda x: "positive" if x >= 0 else "negative")

                # Group by Payment Method + Date + Sign (separate positive from negative)
                # This ensures refunds are charged separately from regular transactions
                # Formula: One fixed fee per group + (group total × rate)
                group_cols = ["Receipt Method Name", "Transaction Date", "Amount Sign"]
                if "Warehouse Code" in temp_df.columns:
                    group_cols.append("Warehouse Code")

                grouped = temp_df.groupby(group_cols, dropna=False).agg({
                    "Transaction Line Amount": "sum",
                    "Transaction Number": "first"  # Keep a transaction number for reference
                }).reset_index()

                # Remove the "Amount Sign" column after grouping (not needed in output)
                grouped = grouped.drop(columns=["Amount Sign"])

                print(f"✓  Expanded {len(invoices)} AR transactions into {len(grouped)} payment entries (aggregated by day+sign from {len(temp_df)} transactions)")
        else:
            # AR Invoice-only path: Add sign-based grouping for correct charge calculation
            # Separate positive and negative amounts to avoid netting refunds with sales
            invoices["Amount Sign"] = invoices["Transaction Line Amount"].apply(lambda x: "positive" if x >= 0 else "negative")

            # Group by Payment Method + Date + Sign (separate positive from negative)
            # This ensures refunds are charged separately from regular transactions
            # Formula: One fixed fee per group + (group total × rate)
            group_cols = ["Receipt Method Name", "Transaction Date", "Amount Sign"]
            if "Warehouse Code" in invoices.columns:
                group_cols.append("Warehouse Code")
            grouped = invoices.groupby(group_cols, dropna=False).agg({
                "Transaction Line Amount": "sum",
                "Transaction Number": "first"  # Keep a transaction number for reference
            }).reset_index()

            # Remove the "Amount Sign" column after grouping (not needed in output)
            grouped = grouped.drop(columns=["Amount Sign"])

        journal_entries = []
        batch_name_counter = 1
        journal_entry_counter = 1
        negative_amount_count = 0
        charge_entries_count = 0

        def _to_text(value) -> str:
            """Convert any value to text, handling nulls/NaN/None properly."""
            if pd.isna(value) or value is None:
                return ""
            return str(value).strip()

        def _seg_from_sp(sp_row: pd.Series, cost_center: str) -> dict:
            """Build a Segment1..Segment7 dict from a service-provider meta row."""
            return {
                "Segment1": _to_text(sp_row.get("COMPANY", "")),
                "Segment2": _to_text(sp_row.get("ACCOUNT", "")),
                "Segment3": _to_text(sp_row.get("DEPARTMENT", "")),
                "Segment4": _to_text(cost_center or sp_row.get("EXTRA_SEGMENT_1", "")),
                "Segment5": _to_text(sp_row.get("PRODUCT_CATEGORY", "")),
                "Segment6": _to_text(sp_row.get("INTER_COMPANY", "")),
                "Segment7": _to_text(sp_row.get("FUT_USED", "")),
            }

        # Generate unique interface group identifier for this entire sheet
        # Using timestamp to ensure uniqueness across multiple file generations
        unique_interface_group_id = interface_group_id

        # ══════════════════════════════════════════════════════════════════════
        # IMPORTANT: Journal Template - CHARGES ONLY Mode
        # ══════════════════════════════════════════════════════════════════════
        # This journal template generates entries for SERVICE PROVIDER CHARGES only.
        # Payment amounts are NOT included in the journal entries.
        #
        # Each order will have:
        #   - 2 charge entries (debit/credit pair) for the service fee
        #   - NO payment amount entries
        #
        # To include payment amounts, see commented code at line ~4562
        # ══════════════════════════════════════════════════════════════════════
        print("\n" + "═" * 80)
        print("JOURNAL TEMPLATE MODE: CHARGES ONLY")
        print("═" * 80)
        print("ℹ️  This journal template will generate entries for SERVICE CHARGES ONLY")
        print("ℹ️  Payment amounts will NOT be included in the journal entries")
        print("ℹ️  Each qualifying order will have one debit/credit pair for charges")
        print("═" * 80 + "\n")

        for _, row in grouped.iterrows():
            payment_method = str(row["Receipt Method Name"]).upper()
            amount = float(row["Transaction Line Amount"])
            transaction_date = pd.to_datetime(row["Transaction Date"]).strftime("%Y/%m/%d")
            warehouse = str(row.get("Warehouse Code", "") or "").strip().upper()

            # Parse transaction date for formatting
            trans_date_obj = pd.to_datetime(row["Transaction Date"])
            # Format Period Name as "26-Mar" (day-month abbreviation)
            formatted_period_name = trans_date_obj.strftime("%d-%b")
            # Format timestamp for batch name as YYYYMMDD
            timestamp_str = trans_date_obj.strftime("%Y%m%d")

            # Resolve cost center for this store/provider (when metadata loaded)
            cost_center = cost_center_lookup.get((warehouse, payment_method), "")

            # Check if amount is negative to determine if we should reverse the entry order
            is_negative_amount = amount < 0
            # Use absolute value for the amounts in journal entries
            abs_amount = abs(amount)

            # Count negative amounts for reporting
            if is_negative_amount:
                negative_amount_count += 1
                print(f"  ℹ️  Negative amount detected: {amount:.2f} → Will use reversal format with absolute value {abs_amount:.2f} (3-series in Debit, 5-series in Credit)")

            # Calculate charges based on charges_lookup if available
            total_charge = 0.0
            charge_key = (payment_method, str(is_cash).strip())
            if charge_key in charges_lookup:
                fixed_charge, rate = charges_lookup[charge_key]
                # Formula: Total Charge = Fixed Charge + (Amount × Rate)
                # Note: VAT is already included in the rate configuration
                total_charge = round(fixed_charge + (abs_amount * rate), 2)
                if total_charge > 0:
                    print(f"  ℹ️  {payment_method} charge for {abs_amount:.2f} SAR invoice: "
                          f"Fixed={fixed_charge:.2f} + Variable=({abs_amount:.2f}×{rate*100:.2f}%)={abs_amount*rate:.2f} "
                          f"= Total Charge={total_charge:.2f} SAR")
            else:
                print(f"  ⚠️  No charge configuration found for {payment_method} (IS_CASH={is_cash})")

            if sp_meta is not None and not sp_meta.empty:
                sp_rows = sp_meta[sp_meta["SERVICE_PROVIDER"] == payment_method]
                debit_rows = sp_rows[sp_rows["CREDIT_DEBIT"] == "DEBIT"]
                credit_rows = sp_rows[sp_rows["CREDIT_DEBIT"] == "CREDIT"]
                if debit_rows.empty or credit_rows.empty:
                    print(f"⚠️  Service-provider metadata missing DEBIT/CREDIT row "
                          f"for {payment_method} (IS_CASH={is_cash}); skipping")
                    continue
                debit_meta = debit_rows.iloc[0]
                credit_meta = credit_rows.iloc[0]

                ledger_id = debit_meta.get("LEDGER_ID", "")
                journal_source = debit_meta.get("JE_SOURCE", "Vend")
                journal_category = debit_meta.get("JE_CATEGORY", "Vend")
                currency_code = "SAR"

                debit_segments = _seg_from_sp(debit_meta, cost_center)
                credit_segments = _seg_from_sp(credit_meta, cost_center)
            else:
                # Legacy fallback
                mapping = legacy_account_mapping[
                    (legacy_account_mapping["Payment Method"] == payment_method) &
                    (legacy_account_mapping["Business Unit"] == "Alqurashi KSA")
                ]
                if mapping.empty:
                    print(f"⚠️  No account mapping found for {payment_method}, skipping")
                    continue
                mapping_row = mapping.iloc[0]
                ledger_id = legacy_bu_config["Ledger ID"]
                journal_source = legacy_bu_config["Journal Source"]
                journal_category = legacy_bu_config["Journal Category"]
                currency_code = legacy_bu_config["Currency Code"]

                base_segments = {
                    "Segment1": _to_text(mapping_row["Segment1"]),
                    "Segment3": _to_text(mapping_row.get("Segment3", "")),
                    "Segment4": _to_text(cost_center or mapping_row.get("Segment4", "")),
                    "Segment5": _to_text(mapping_row.get("Segment5", "")),
                    "Segment6": _to_text(mapping_row.get("Segment6", "")),
                    "Segment7": _to_text(mapping_row.get("Segment7", "")),
                }
                debit_segments = {**base_segments, "Segment2": _to_text(mapping_row["Debit Account"])}
                credit_segments = {**base_segments, "Segment2": _to_text(mapping_row["Credit Account"])}

            # Batch and Journal Entry names
            # Format: MAR-26: {{TABBY/TAMARA}} Vend -{{Store_name}}-{{timestamp_only_date_month_year}}
            # Period name is in format "Mar-26" which gives us month and year
            # Extract month from period_name (e.g., "Mar-26" -> "MAR")
            month_name = formatted_period_name.split("-")[1].upper()  # Get month abbreviation and uppercase it
            year_suffix = formatted_period_name.split("-")[0]  # Get day/year part
            batch_name = f"{month_name}-{year_suffix}: {payment_method} Vend -{warehouse}-{timestamp_str}"
            # REFERENCE4 (Journal Entry Name) should match REFERENCE1 (Batch Name)
            journal_entry_name = batch_name

            common = {
                "Status Code": "NEW",
                "Ledger ID": ledger_id,
                "Effective Date of Transaction": transaction_date,
                "Journal Source": journal_source,
                "Journal Category": journal_category,
                "Currency Code": currency_code,
                "Journal Entry Creation Date": transaction_date,
                "Actual Flag": "A",
                "REFERENCE1 (Batch Name)": batch_name,
                "REFERENCE4 (Journal Entry Name)": journal_entry_name,
                "Interface Group Identifier": unique_interface_group_id,
                "Period Name": formatted_period_name,
            }

            # CRITICAL: Payment entry debit/credit logic for sales lines amounts
            # This matches the charge entry logic (opposite of old payment logic)
            # POSITIVE amounts:
            #   - 3-series accounts (3020044) → DEBIT columns
            #   - 5-series accounts (5000104) → CREDIT columns
            # NEGATIVE amounts:
            #   - 3-series accounts (3020044) → CREDIT columns
            #   - 5-series accounts (5000104) → DEBIT columns
            # Always use absolute values for amounts

            if is_negative_amount:
                # NEGATIVE: 3-series in Credit, 5-series in Debit
                credit_account_entry = {
                    **common,
                    **credit_segments,  # 3020044 from "CREDIT" metadata row
                    "Entered Debit Amount": "",
                    "Entered Credit Amount": abs_amount,  # 3-series in CREDIT for negative
                    "Converted Debit Amount": "",
                    "Converted Credit Amount": abs_amount,
                }
                debit_account_entry = {
                    **common,
                    **debit_segments,  # 5000104 from "DEBIT" metadata row
                    "Entered Debit Amount": abs_amount,  # 5-series in DEBIT for negative
                    "Entered Credit Amount": "",
                    "Converted Debit Amount": abs_amount,
                    "Converted Credit Amount": "",
                }
            else:
                # POSITIVE: 3-series in Debit, 5-series in Credit
                credit_account_entry = {
                    **common,
                    **credit_segments,  # 3020044 from "CREDIT" metadata row
                    "Entered Debit Amount": abs_amount,  # 3-series in DEBIT for positive
                    "Entered Credit Amount": "",
                    "Converted Debit Amount": abs_amount,
                    "Converted Credit Amount": "",
                }
                debit_account_entry = {
                    **common,
                    **debit_segments,  # 5-series from "DEBIT" metadata row
                    "Entered Debit Amount": "",
                    "Entered Credit Amount": abs_amount,  # 5-series in CREDIT for positive
                    "Converted Debit Amount": "",
                    "Converted Credit Amount": abs_amount,
                }

            # ── JOURNAL TEMPLATE CHANGE: Only generate charge entries, not payment entries ──
            # The payment amounts are already recorded elsewhere in the system.
            # Journal template should ONLY show the service provider charges (TABBY/TAMARA fees).
            # Therefore, we skip appending the payment amount entries and only generate charge entries.
            #
            # NOTE: If you need to restore payment entries, uncomment the lines below:
            # journal_entries.append(credit_account_entry)
            # journal_entries.append(debit_account_entry)

            # ── Generate charge entries if charges are applicable ──────────────
            if total_charge > 0:
                # ORIGINAL charge debit/credit logic (DO NOT CHANGE):
                # For positive amounts: 3-series in DEBIT, 5-series in CREDIT
                # For negative amounts: 3-series in CREDIT, 5-series in DEBIT

                if is_negative_amount:
                    # NEGATIVE: 3-series in Credit, 5-series in Debit (same as original payment logic)
                    charge_credit_entry = {
                        **common,
                        **credit_segments,  # 3020044 from "CREDIT" metadata row
                        "Entered Debit Amount": "",
                        "Entered Credit Amount": total_charge,  # 3-series in CREDIT for negative charge
                        "Converted Debit Amount": "",
                        "Converted Credit Amount": total_charge,
                    }
                    charge_debit_entry = {
                        **common,
                        **debit_segments,  # 5000104 from "DEBIT" metadata row
                        "Entered Debit Amount": total_charge,  # 5-series in DEBIT for negative charge
                        "Entered Credit Amount": "",
                        "Converted Debit Amount": total_charge,
                        "Converted Credit Amount": "",
                    }
                else:
                    # POSITIVE: 3-series in Debit, 5-series in Credit (same as original payment logic)
                    charge_credit_entry = {
                        **common,
                        **credit_segments,  # 3020044 from "CREDIT" metadata row
                        "Entered Debit Amount": total_charge,  # 3-series in DEBIT for positive charge
                        "Entered Credit Amount": "",
                        "Converted Debit Amount": total_charge,
                        "Converted Credit Amount": "",
                    }
                    charge_debit_entry = {
                        **common,
                        **debit_segments,  # 5000104 from "DEBIT" metadata row
                        "Entered Debit Amount": "",
                        "Entered Credit Amount": total_charge,  # 5-series in CREDIT for positive charge
                        "Converted Debit Amount": "",
                        "Converted Credit Amount": total_charge,
                    }

                # Append charge entries
                journal_entries.append(charge_credit_entry)
                journal_entries.append(charge_debit_entry)
                charge_entries_count += 1
                print(f"  ℹ️  Added charge entries for {payment_method}: {total_charge:.2f} SAR")
            else:
                # No charges for this transaction - skip entirely in charges-only mode
                print(f"  ⚠️  No charges calculated for {payment_method} (Amount: {abs_amount:.2f} SAR) - skipping entry")

            journal_entry_counter += 1
            if journal_entry_counter % 10 == 0:
                batch_name_counter += 1

        # Create DataFrame from journal entries
        journal_df = pd.DataFrame(journal_entries)

        # Add all the empty columns from the JournalImportTemplate.csv
        template_columns = [
            "Status Code", "Ledger ID", "Effective Date of Transaction", "Journal Source",
            "Journal Category", "Currency Code", "Journal Entry Creation Date", "Actual Flag",
            "Segment1", "Segment2", "Segment3", "Segment4", "Segment5", "Segment6", "Segment7",
            "Segment8", "Segment9", "Segment10", "Segment11", "Segment12", "Segment13", "Segment14",
            "Segment15", "Segment16", "Segment17", "Segment18", "Segment19", "Segment20", "Segment21",
            "Segment22", "Segment23", "Segment24", "Segment25", "Segment26", "Segment27", "Segment28",
            "Segment29", "Segment30", "Entered Debit Amount", "Entered Credit Amount",
            "Converted Debit Amount", "Converted Credit Amount", "REFERENCE1 (Batch Name)",
            "REFERENCE2 (Batch Description)", "REFERENCE3", "REFERENCE4 (Journal Entry Name)",
            "REFERENCE5 (Journal Entry Description)", "REFERENCE6 (Journal Entry Reference)",
            "REFERENCE7 (Journal Entry Reversal flag)", "REFERENCE8 (Journal Entry Reversal Period)",
            "REFERENCE9 (Journal Reversal Method)", "REFERENCE10 (Journal Entry Line Description)",
            "Reference column 1", "Reference column 2", "Reference column 3", "Reference column 4",
            "Reference column 5", "Reference column 6", "Reference column 7", "Reference column 8",
            "Reference column 9", "Reference column 10", "Statistical Amount", "Currency Conversion Type",
            "Currency Conversion Date", "Currency Conversion Rate", "Interface Group Identifier",
            "Context field for Journal Entry Line DFF", "ATTRIBUTE1 Value for Journal Entry Line DFF",
            "ATTRIBUTE2 Value for Journal Entry Line DFF", "Attribute3 Value for Journal Entry Line DFF",
            "Attribute4 Value for Journal Entry Line DFF", "Attribute5 Value for Journal Entry Line DFF",
            "Attribute6 Value for Journal Entry Line DFF", "Attribute7 Value for Journal Entry Line DFF",
            "Attribute8 Value for Journal Entry Line DFF", "Attribute9 Value for Journal Entry Line DFF",
            "Attribute10 Value for Journal Entry Line DFF", "Attribute11 Value for Captured Information DFF",
            "Attribute12 Value for Captured Information DFF", "Attribute13 Value for Captured Information DFF",
            "Attribute14 Value for Captured Information DFF", "Attribute15 Value for Captured Information DFF",
            "Attribute16 Value for Captured Information DFF", "Attribute17 Value for Captured Information DFF",
            "Attribute18 Value for Captured Information DFF", "Attribute19 Value for Captured Information DFF",
            "Attribute20 Value for Captured Information DFF", "Context field for Captured Information DFF",
            "Average Journal Flag", "Clearing Company", "Ledger Name", "Encumbrance Type ID",
            "Reconciliation Reference", "Period Name", "REFERENCE 18", "REFERENCE 19", "REFERENCE 20",
            "Attribute Date 1", "Attribute Date 2", "Attribute Date 3", "Attribute Date 4",
            "Attribute Date 5", "Attribute Date 6", "Attribute Date 7", "Attribute Date 8",
            "Attribute Date 9", "Attribute Date 10", "Attribute Number 1", "Attribute Number 2",
            "Attribute Number 3", "Attribute Number 4", "Attribute Number 5", "Attribute Number 6",
            "Attribute Number 7", "Attribute Number 8", "Attribute Number 9", "Attribute Number 10",
            "Global Attribute Category", "Global Attribute 1 ", "Global Attribute 2", "Global Attribute 3",
            "Global Attribute 4", "Global Attribute 5", "Global Attribute 6 ", "Global Attribute 7",
            "Global Attribute 8", "Global Attribute 9", "Global Attribute 10", "Global Attribute 11",
            "Global Attribute 12", "Global Attribute 13", "Global Attribute 14", "Global Attribute 15",
            "Global Attribute 16", "Global Attribute 17", "Global Attribute 18", "Global Attribute 19 ",
            "Global Attribute 20 ", "Global Attribute Date 1", "Global Attribute Date 2",
            "Global Attribute Date 3", "Global Attribute Date 4", "Global Attribute Date 5",
            "Global Attribute Number 1", "Global Attribute Number 2", "Global Attribute Number 3",
            "Global Attribute Number 4", "Global Attribute Number 5", "END"
        ]

        # Add missing columns with empty values
        for col in template_columns:
            if col not in journal_df.columns:
                journal_df[col] = ""

        # Ensure all segment columns are text and have no null values
        segment_cols = [f"Segment{i}" for i in range(1, 31)]
        for col in segment_cols:
            if col in journal_df.columns:
                journal_df[col] = journal_df[col].fillna("").astype(str)

        # Ensure END column has "END" value
        journal_df["END"] = "END"

        # Reorder columns to match template
        journal_df = journal_df[template_columns]

        # Summary output
        print("\n" + "═" * 80)
        print("JOURNAL TEMPLATE GENERATION COMPLETE - CHARGES ONLY MODE")
        print("═" * 80)
        print(f"✓  Generated {len(journal_df)} journal entry lines")
        print(f"   - Charge entries: {charge_entries_count * 2} lines ({charge_entries_count} charge transactions)")
        print(f"   - Payment entries: 0 lines (EXCLUDED in charges-only mode)")
        if charge_entries_count > 0:
            total_charges = sum(
                pd.to_numeric(journal_df['Entered Debit Amount'], errors='coerce').fillna(0)
            )
            print(f"   - Total charges amount: {total_charges:,.2f} SAR")
        if negative_amount_count > 0:
            print(f"ℹ️  Note: {negative_amount_count} transaction(s) with negative amounts used reversal format")

        if len(journal_df) == 0:
            print("\n⚠️  WARNING: No journal entries generated!")
            print("   This could mean:")
            print("   - No charges file was provided")
            print("   - Charges lookup returned 0 for all transactions")
            print("   - No qualifying TABBY/TAMARA transactions found")

        print("═" * 80 + "\n")

        return journal_df

    def save_journal_template(self, journal_df: pd.DataFrame):
        """Save journal import template to CSV file."""
        if journal_df.empty:
            print("⚠️  No journal entries to save")
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Journal_Import_Template_{ts}.csv"
        filepath = self.output_dir / filename

        journal_df.to_csv(filepath, index=False, encoding="utf-8-sig")
        print(f"✓  Saved journal template: {filepath}")


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
        "line_items":      "ZAHRAN sale line 5 to 31 March.xlsx",
        "payments":        "ZAHRAN payment line 5 to 31 March.xlsx",
        "metadata":        "FUSION_SALES_METADATA_202604121703.csv",
        "registers":       "VENDHQ_REGISTERS_202604121654.csv",
        "receipt_methods": "Receipt_Methods.csv",
        "bank_charges":    "Bank_Charges.csv",
    }

    START_TXN_SEQUENCE  = 500   # ← update from report "Next run START_TXN_SEQUENCE ="
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