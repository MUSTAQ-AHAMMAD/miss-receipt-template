# Bank Account Number Issue Analysis

## Problem Statement

The variables `RemittanceBankAccountNumber` (Standard Receipt) and `BankAccountNumber` (Miscellaneous Receipt) are not getting the full bank account numbers from the `BANK_ACCOUNT_NUMBER` column in `Receipt_Methods.csv`.

### Expected Behavior

For ABHATIMSQR store, the expected values are:

| Payment Method | Expected Bank Account Number      |
|----------------|-----------------------------------|
| AMEX           | 157-95017321-ABHATIMSQR          |
| Cash           | Cash ABHATIMSQR                  |
| Mada           | 157-95017321-ABHATIMSQR          |
| Master         | 157-95017321-ABHATIMSQR          |
| Visa           | 157-95017321-ABHATIMSQR          |

## Root Cause Analysis

### 1. Data Sources Priority

The code uses two sources for bank account information, in this order:

1. **PRIMARY SOURCE**: `VENDHQ_REGISTERS_*.csv` (vend registers file)
2. **FALLBACK SOURCE**: `Receipt_Methods.csv`

#### Code Flow in `get_bank_account()`:

```python
def get_bank_account(self, store_name: str, method: str) -> Tuple[str, str, str]:
    # Primary source: vend register file
    if self._register_cache is not None:
        override = self._register_cache.get_account(store_name, method)
        if override is not None:
            return (method, override[0], override[1])  # ← RETURNS HERE IF FOUND

    # Fallback: Receipt_Methods.csv
    # ... (only reached if vend registers don't have the data)
```

### 2. Current Data in Vend Registers File

`VENDHQ_REGISTERS_202604121654.csv` contains:

```csv
REGISTER_NAME,CASH_ACCOUNT,BANK_ACCOUNT
ABHATIMSQR,Cash ABHATIMSQR,AL Jazeerah Bank ABHATIMSQR
```

**Problem**: The `BANK_ACCOUNT` column in the vend registers file does NOT contain the full account number like `157-95017321-ABHATIMSQR`. It only has the bank name `AL Jazeerah Bank ABHATIMSQR`.

### 3. Account Number Extraction

The code tries to extract account numbers using `_extract_acc_number()`:

```python
_ACC_NUM_RE = re.compile(r"(?:ACC|Acc|A/C)\s*#?\s*([0-9A-Za-z][0-9A-Za-z\-]*)")

def _extract_acc_number(raw: str) -> str:
    """Extract account number from strings like:
    'AL Jazeerah Bank WADILABAN ACC # 015795017321049'
    """
    if not raw:
        return ""
    m = _ACC_NUM_RE.search(raw)
    if not m:
        return ""
    return m.group(1)
```

When processing "AL Jazeerah Bank ABHATIMSQR":
- The regex looks for "ACC #" or similar patterns
- **NO MATCH FOUND** because there's no "ACC #" in the string
- Falls back to using the full string "AL Jazeerah Bank ABHATIMSQR"
- Returns: `(raw, raw)` = `("AL Jazeerah Bank ABHATIMSQR", "AL Jazeerah Bank ABHATIMSQR")`

### 4. Why Receipt_Methods.csv is Not Being Used

The code never reaches the Receipt_Methods.csv lookup because:

1. Vend registers file IS loaded (`self._register_cache is not None`)
2. ABHATIMSQR IS found in vend registers
3. The `get_account()` method returns the data from vend registers
4. The fallback to Receipt_Methods.csv never executes

## Solution Options

### Option 1: Update Vend Registers File (RECOMMENDED)

Update `VENDHQ_REGISTERS_202604121654.csv` to include complete account numbers:

```csv
REGISTER_NAME,CASH_ACCOUNT,BANK_ACCOUNT
ABHATIMSQR,Cash ABHATIMSQR,AL Jazeerah Bank ABHATIMSQR ACC # 157-95017321-ABHATIMSQR
```

**Pros:**
- Keeps the existing priority logic intact
- Vend registers remain the authoritative source
- No code changes needed
- Works for all stores

**Cons:**
- Requires updating and maintaining the vend registers file

### Option 2: Remove Register from Vend File

If a store should use Receipt_Methods.csv instead, remove it from the vend registers file or leave the BANK_ACCOUNT field empty.

**Pros:**
- Quick fix for specific stores
- No code changes needed

**Cons:**
- Loses other benefits of vend registers tracking

### Option 3: Change Priority Logic (NOT RECOMMENDED)

Modify the code to prefer Receipt_Methods.csv over vend registers.

**Pros:**
- Would immediately use Receipt_Methods.csv data

**Cons:**
- **BREAKS EXISTING DESIGN**: Vend registers are intended to be the primary source
- Could cause issues for stores that rely on vend registers
- More complex to maintain
- Not aligned with the system architecture

### Option 4: Use SUBINVENTORY_BANK_ACCOUNT_MAPPING.csv

The system also has `SUBINVENTORY_BANK_ACCOUNT_MAPPING.csv` which contains:

```csv
SUBINVENTORY,MISC_RECEIPT_BANK_ACCOUNT_NUMBER
ABHATIMSQR,015795017321049
```

However, this shows account number `015795017321049`, not `157-95017321-ABHATIMSQR`.

**This suggests there might be a data consistency issue between different data sources.**

## Verification Steps

### 1. Check Current Vend Registers Content

```bash
grep ABHATIMSQR VENDHQ_REGISTERS_202604121654.csv
```

Expected current output:
```
476,335,ABHATIMSQR,Cash ABHATIMSQR,3E+14,AL Jazeerah Bank ABHATIMSQR,3E+14,,,SA,,
```

### 2. Check Receipt_Methods.csv

```bash
grep ABHATIMSQR Receipt_Methods.csv | head -5
```

Expected output:
```
300000052613062,AlQurashi-KSA,AMEX,AL Jazeerah Bank ABHATIMSQR,157-95017321-ABHATIMSQR
300000052613062,AlQurashi-KSA,Cash,Cash ABHATIMSQR,Cash ABHATIMSQR
300000052613062,AlQurashi-KSA,Mada,AL Jazeerah Bank ABHATIMSQR,157-95017321-ABHATIMSQR
300000052613062,AlQurashi-KSA,Master,AL Jazeerah Bank ABHATIMSQR,157-95017321-ABHATIMSQR
300000052613062,AlQurashi-KSA,Visa,AL Jazeerah Bank ABHATIMSQR,157-95017321-ABHATIMSQR
```

### 3. Run Verification Test

```bash
python3 test_bank_account_verification.py
```

This will verify if the generated receipt files contain the correct bank account numbers.

## Recommended Action Plan

1. **Update the vend registers file** to include full account numbers in the BANK_ACCOUNT column using the "ACC #" format that the extractor expects:

```csv
REGISTER_NAME,CASH_ACCOUNT,BANK_ACCOUNT
ABHATIMSQR,Cash ABHATIMSQR,AL Jazeerah Bank ABHATIMSQR ACC # 157-95017321-ABHATIMSQR
```

2. **Alternatively**, if the account number format should be different, update all affected stores in the vend registers file to match the format in Receipt_Methods.csv.

3. **Verify** the changes by running the test script and generating sample receipts.

## Additional Notes

### Code Preservation of Bank Account Numbers

The code in both `Odoo-export-FBDA-template.py` and `100%-Working-code-Odoo-to-Oracle-FBDA.py` correctly preserves bank account numbers from Receipt_Methods.csv **without trimming**:

```python
# Lines 1523-1525 in Odoo-export-FBDA-template.py
# Preserve full bank account number text without trimming
acct_number_raw = row.get("BANK_ACCOUNT_NUMBER")
acct_number = str(acct_number_raw) if acct_number_raw is not None and not (isinstance(acct_number_raw, float) and np.isnan(acct_number_raw)) else ""
```

**This code is correct and does not need to be changed.**

### Where Values Are Used

- **Standard Receipts** (Line 2622): `RemittanceBankAccountNumber` column
- **Miscellaneous Receipts** (Line 2926): `BankAccountNumber` column

Both read from the same `get_bank_account()` method which returns the third element of the tuple (the bank account number).

## Conclusion

The issue is **NOT** with the code trimming bank account numbers from Receipt_Methods.csv.

The issue is that **the vend registers file takes precedence** and contains incomplete bank account information (just the bank name without the account number).

**Solution**: Update the vend registers file to include complete account numbers in the proper format.
