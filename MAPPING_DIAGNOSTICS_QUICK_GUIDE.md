# Quick Reference: How to Read the New Diagnostic Logs

## What Changed

Added **comprehensive payment method tracking** at 3 key stages:
1. Payment normalization (input → standardized names)
2. Standard receipt generation (which methods create receipts)
3. Misc receipt generation (which card methods have charges)

---

## Where to Find the Information

### Location: Verification Report
File: `ORACLE_FUSION_OUTPUT/Verification_Report_YYYYMMDD_HHMMSS.txt`

### New Sections to Review

#### Section 1e: PAYMENT METHOD NORMALIZATION DIAGNOSTIC
**What it shows:** How raw payment methods from your input file are normalized

**Example:**
```
Raw payment methods found in input:
  'CASH' (count: 150) → normalized to → 'Cash'
  'mada' (count: 75) → normalized to → 'Mada'
  'AMEX' (count: 25) → normalized to → 'Amex'

Payment method totals after normalization:
  Cash                 125,450.00 SAR  [✓ STANDARD RECEIPT]
  Amex                  12,800.00 SAR  [⚠ NOT IN ANY CATEGORY]
```

**What to look for:**
- ⚠ Any method marked `[⚠ NOT IN ANY CATEGORY]` = **NOT generating receipts**
- This is your **first indicator** of the problem

---

#### Section 8: STANDARD RECEIPT RECORDS

**What it shows:** Which payment methods generate standard receipts

**Example:**
```
⚠ PAYMENT METHOD PROCESSING BREAKDOWN:

✓ ACCEPTED for Standard Receipts (in RECEIPT_PAYMENT_METHODS):
  Cash                 125,450.00 SAR
  Mada                  45,230.00 SAR

⚠ SKIPPED - Not in RECEIPT_PAYMENT_METHODS:
  Amex                  12,800.00 SAR  ← NOT GENERATING RECEIPTS!
  Apple Pay              8,450.00 SAR  ← NOT GENERATING RECEIPTS!
  TOTAL SKIPPED         21,250.00 SAR
```

**What to look for:**
- Methods in the **SKIPPED** section = money not generating receipts
- Add these methods to `RECEIPT_PAYMENT_METHODS` constant

---

#### Section 8b: MISCELLANEOUS RECEIPT RECORDS

**What it shows:** Which card payment methods generate misc receipts (for bank charges)

**Example:**
```
⚠ CARD PAYMENT METHOD PROCESSING BREAKDOWN:

✓ ACCEPTED for Misc Receipts (in CARD_PAYMENT_METHODS):
  Mada                  45,230.00 SAR
  Visa                  32,100.00 SAR

⚠ SKIPPED - Not in CARD_PAYMENT_METHODS:
  Amex                  12,800.00 SAR  ← NOT GENERATING MISC RECEIPTS!
  TOTAL SKIPPED         12,800.00 SAR
```

**What to look for:**
- Card methods in **SKIPPED** section = bank charges not being tracked
- Add these to `CARD_PAYMENT_METHODS` constant

---

## How to Fix Issues

### Problem: "Only Cash receipts are generating"

**Diagnostic Steps:**

1. Open verification report
2. Go to Section 1e
3. Look at normalized payment methods
4. Check which ones are marked `[⚠ NOT IN ANY CATEGORY]`

**Fix:**
Edit `Odoo-export-FBDA-template.py` line 48:

```python
# BEFORE (only 4 methods):
RECEIPT_PAYMENT_METHODS = {"Cash", "Mada", "Visa", "MasterCard"}

# AFTER (add your missing methods):
RECEIPT_PAYMENT_METHODS = {"Cash", "Mada", "Visa", "MasterCard", "Amex", "Apple Pay", "STC Pay"}
```

---

### Problem: "0 Misc Receipts Generated"

**Diagnostic Steps:**

1. Open verification report
2. Go to Section 8b
3. Check the "SKIPPED" section
4. See which card methods are missing

**Fix:**
Edit `Odoo-export-FBDA-template.py` line 50:

```python
# BEFORE (only 3 card methods):
CARD_PAYMENT_METHODS = {"Mada", "Visa", "MasterCard"}

# AFTER (add your card methods):
CARD_PAYMENT_METHODS = {"Mada", "Visa", "MasterCard", "Amex"}
```

---

### Problem: "Payment method names are weird"

**Example:** Your input has "APPLE_PAY" but logs show it as "Cash"

**Diagnostic Steps:**

1. Check Section 1e: Raw payment methods
2. Look at the normalization mapping
3. If mapping is wrong, update the normalizer

**Fix:**
Edit the `normalise_payment()` function around line 589:

```python
def normalise_payment(raw: str) -> str:
    key = raw.upper().strip()
    if key in PAYMENT_METHOD_NORM:
        return PAYMENT_METHOD_NORM[key]

    # Add your custom mappings here:
    if "APPLE" in key or "APPLE_PAY" in key:
        return "Apple Pay"
    if "STC" in key:
        return "STC Pay"

    # ... rest of function
```

---

## Symbols Used in Logs

| Symbol | Meaning |
|--------|---------|
| ✓ | Accepted - will generate receipts |
| ⚠ | Warning - skipped/not in category |
| ⊗ | Excluded by design (BNPL) |
| ← | Attention - this is a problem |

---

## Common Scenarios

### Scenario 1: All Payment Methods Show as Cash

**Symptoms:**
- Section 1e shows only "Cash" method
- Section 8 shows only Cash receipts

**Cause:** Payment file might not be loaded or column mapping is wrong

**Fix:**
1. Check that payment file was uploaded
2. Check column names match expected format
3. Review Section 1b/1c for column mapping results

---

### Scenario 2: Some Methods Generate Receipts, Others Don't

**Symptoms:**
- Section 1e shows multiple methods
- Section 8 shows some in ACCEPTED, others in SKIPPED

**Cause:** Missing methods from `RECEIPT_PAYMENT_METHODS` constant

**Fix:**
Add missing methods to the constant (see fix examples above)

---

### Scenario 3: Card Methods Don't Generate Misc Receipts

**Symptoms:**
- Section 8b shows "0 files" for misc receipts
- Section 8b SKIPPED shows card methods

**Cause:**
1. Missing methods from `CARD_PAYMENT_METHODS`, OR
2. `BANK_CHARGES.csv` file not loaded

**Fix:**
1. Check if BANK_CHARGES.csv exists in repo root
2. Add missing card methods to `CARD_PAYMENT_METHODS`

---

## Before/After Example

### BEFORE (Current Issue):
```
Section 8: STANDARD RECEIPT RECORDS
Receipt files to write: 433

⚠ PAYMENT METHOD PROCESSING BREAKDOWN:
✓ ACCEPTED:
  Cash                 280,000.00 SAR

⚠ SKIPPED:
  Mada                  45,230.00 SAR  ← NOT GENERATING RECEIPTS!
  Visa                  32,100.00 SAR  ← NOT GENERATING RECEIPTS!
  Amex                  12,800.00 SAR  ← NOT GENERATING RECEIPTS!
  TOTAL SKIPPED         90,130.00 SAR
```

### AFTER (Fixed):
```
Section 8: STANDARD RECEIPT RECORDS
Receipt files to write: 550

⚠ PAYMENT METHOD PROCESSING BREAKDOWN:
✓ ACCEPTED:
  Cash                 280,000.00 SAR
  Mada                  45,230.00 SAR
  Visa                  32,100.00 SAR
  Amex                  12,800.00 SAR

⚠ SKIPPED:
  (none)
```

---

## Summary Checklist

When reviewing your verification report:

- [ ] Section 1e: All payment methods normalized correctly?
- [ ] Section 1e: Any methods marked `[⚠ NOT IN ANY CATEGORY]`?
- [ ] Section 8: Check SKIPPED section - is it empty?
- [ ] Section 8: SKIPPED total should be 0.00 SAR
- [ ] Section 8b: Check SKIPPED section for card methods
- [ ] All expected payment methods generating receipts?

**If any checkbox fails → Update the payment method constants as shown above**

---

## Need More Help?

1. **Review the full report:** `MAPPING_DIAGNOSTICS_REPORT.md`
2. **Check the constants:** Lines 48-50 in `Odoo-export-FBDA-template.py`
3. **Review normalization:** Line 589 `normalise_payment()` function
4. **Verification report:** Always in `ORACLE_FUSION_OUTPUT/` directory

The new logs give you **complete transparency** - you'll see exactly what's happening at every step!
