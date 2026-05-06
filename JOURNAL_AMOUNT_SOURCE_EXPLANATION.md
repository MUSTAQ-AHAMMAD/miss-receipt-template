# Journal Entry Amount Source - Detailed Explanation

## Question: "From where is the amount being picked?"

### Answer: The amount comes from `Transaction Line Amount` column, but it's used ONLY for calculating charges, NOT included directly in journal entries.

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Payment/Invoice File Input                             │
│                                                                 │
│  Transaction Number | Payment Method | Transaction Line Amount │
│  ─────────────────────────────────────────────────────────────  │
│  INV-001           | TABBY          | 1,000.00 SAR   ←──┐     │
│  INV-002           | TAMARA         | 500.00 SAR     ←──┤     │
│                                                          │     │
│  This is the FULL INVOICE AMOUNT ────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │ Read & Group Data
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Code Extraction (Line 4425)                            │
│                                                                 │
│  amount = float(row["Transaction Line Amount"])                │
│                                                                 │
│  TABBY:  amount = 1,000.00 SAR                                 │
│  TAMARA: amount = 500.00 SAR                                   │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │ Use for calculation
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Charge Calculation (Lines 4449-4456)                   │
│                                                                 │
│  total_charge = fixed_charge + (abs_amount × rate)             │
│                                                                 │
│  TABBY Calculation:                                             │
│    = 1 SAR + (1,000 × 0.05)                                    │
│    = 1 + 50                                                     │
│    = 51 SAR  ←── This is what goes into journal                │
│                                                                 │
│  TAMARA Calculation:                                            │
│    = 1.5 SAR + (500 × 0.0425)                                  │
│    = 1.5 + 21.25                                                │
│    = 22.75 SAR  ←── This is what goes into journal             │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │ Generate journal entries
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Journal Entry Decision (Lines 4576-4583)               │
│                                                                 │
│  ❌ PAYMENT ENTRIES (Lines 4582-4583): COMMENTED OUT           │
│     # journal_entries.append(credit_account_entry)  ← 1,000 SAR│
│     # journal_entries.append(debit_account_entry)   ← 1,000 SAR│
│                                                                 │
│  ✅ CHARGE ENTRIES (Lines 4629-4630): ACTIVE                   │
│     journal_entries.append(charge_credit_entry)     ← 51 SAR   │
│     journal_entries.append(charge_debit_entry)      ← 51 SAR   │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │ Output to file
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: Final Journal Entries (What's Actually Written)        │
│                                                                 │
│  For TABBY (1,000 SAR invoice):                                │
│    Entry 1: Account 3020044, Credit: 51 SAR                    │
│    Entry 2: Account 5000104, Debit:  51 SAR                    │
│                                                                 │
│  For TAMARA (500 SAR invoice):                                 │
│    Entry 1: Account 3020044, Credit: 22.75 SAR                 │
│    Entry 2: Account 5000104, Debit:  22.75 SAR                 │
│                                                                 │
│  ❌ Invoice amounts (1,000 SAR, 500 SAR) are NOT in journal    │
│  ✅ Only charge amounts (51 SAR, 22.75 SAR) are in journal     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Code References

### 1. Where Amount is Picked (Line 4425)
```python
amount = float(row["Transaction Line Amount"])
```
**Location:** `Odoo-export-FBDA-template.py:4425`

This reads the full invoice amount from the payment file.

---

### 2. How Amount is Used (Lines 4449-4456)
```python
# Calculate charges based on charges_lookup if available
total_charge = 0.0
charge_key = (payment_method, str(is_cash).strip())
if charge_key in charges_lookup:
    fixed_charge, rate = charges_lookup[charge_key]
    # Formula: Total Charge = Fixed Charge + (Amount × Rate)
    total_charge = fixed_charge + (abs_amount * rate)
```
**Location:** `Odoo-export-FBDA-template.py:4449-4456`

The invoice amount is used ONLY to calculate the percentage-based charge component.

---

### 3. Payment Entries are SKIPPED (Lines 4576-4583)
```python
# ── JOURNAL TEMPLATE CHANGE: Only generate charge entries, not payment entries ──
# The payment amounts are already recorded elsewhere in the system.
# Journal template should ONLY show the service provider charges (TABBY/TAMARA fees).
# Therefore, we skip appending the payment amount entries and only generate charge entries.
#
# NOTE: If you need to restore payment entries, uncomment the lines below:
# journal_entries.append(credit_account_entry)  ← Would contain invoice amount
# journal_entries.append(debit_account_entry)   ← Would contain invoice amount
```
**Location:** `Odoo-export-FBDA-template.py:4576-4583`

These lines are **COMMENTED OUT**, so payment amounts are NOT added to journal.

---

### 4. Charge Entries are ADDED (Lines 4629-4630)
```python
# Append charge entries
journal_entries.append(charge_credit_entry)  ← Contains ONLY charge amount
journal_entries.append(charge_debit_entry)   ← Contains ONLY charge amount
```
**Location:** `Odoo-export-FBDA-template.py:4629-4630`

Only the calculated charge amounts go into the journal, not the invoice amounts.

---

## Summary Table

| Item | Source | Used For | Included in Journal? |
|------|--------|----------|---------------------|
| **Invoice Amount** | `Transaction Line Amount` column | Calculate charge percentage | ❌ NO |
| **Fixed Charge** | `FIXED_FREIGHT_CHARGE` in CSV | Part of total charge | ✅ YES (as part of charge) |
| **Rate Charge** | `Invoice × BANK_CHARGE_RATE` | Part of total charge | ✅ YES (as part of charge) |
| **Total Charge** | `Fixed + (Invoice × Rate)` | Journal entry amount | ✅ YES |

---

## Example with Real Numbers

### TABBY Transaction
- **Invoice Amount:** 1,000 SAR (from `Transaction Line Amount`)
- **Fixed Charge:** 1 SAR (from `FIXED_FREIGHT_CHARGE`)
- **Rate:** 5% = 0.05 (from `BANK_CHARGE_RATE`)
- **Calculation:** 1 + (1,000 × 0.05) = 1 + 50 = **51 SAR**
- **Journal Entry:** 51 SAR (NOT 1,000 SAR)

### TAMARA Transaction
- **Invoice Amount:** 500 SAR (from `Transaction Line Amount`)
- **Fixed Charge:** 1.5 SAR (from `FIXED_FREIGHT_CHARGE`)
- **Rate:** 4.25% = 0.0425 (from `BANK_CHARGE_RATE`)
- **Calculation:** 1.5 + (500 × 0.0425) = 1.5 + 21.25 = **22.75 SAR**
- **Journal Entry:** 22.75 SAR (NOT 500 SAR)

---

## Troubleshooting: If You See Full Invoice Amount in Journal

If you're seeing the full invoice amount (1,000 SAR instead of 51 SAR) in the journal entries, one of these scenarios applies:

### Scenario 1: Payment Entries Were Uncommented
Someone modified lines 4582-4583 and uncommented them:
```python
# Before (correct - charges only):
# journal_entries.append(credit_account_entry)
# journal_entries.append(debit_account_entry)

# After (wrong - includes payment amounts):
journal_entries.append(credit_account_entry)
journal_entries.append(debit_account_entry)
```
**Solution:** Comment out these lines again.

---

### Scenario 2: Wrong Charge Rates
The charge rates in `SERVICE_PROVIDER_JOURNAL_META_Charges.csv` are too high:
- If TABBY rate is 0.95 (95%) instead of 0.05 (5%), a 1,000 SAR invoice would generate a 951 SAR charge
- If rates are 1.0 (100%), charges would equal invoice amounts

**Solution:** Verify rates in the CSV file:
- TABBY: Should be 0.05 (5%), not 0.5 or 0.95
- TAMARA: Should be 0.0425 (4.25%), not 0.425 or 0.999

---

### Scenario 3: Looking at Old Output
You're viewing journal output generated before the fix was applied.

**Solution:** Regenerate the journal template with the current code.

---

## Configuration File Reference

The charge rates come from `SERVICE_PROVIDER_JOURNAL_META_Charges.csv`:

```csv
SERVICE_PROVIDER,IS_CASH,FIXED_FREIGHT_CHARGE,BANK_CHARGE_RATE
TABBY,0,1,0.05
TAMARA,0,1.5,0.0425
```

- **TABBY:** 1 SAR fixed + 5% of invoice
- **TAMARA:** 1.5 SAR fixed + 4.25% of invoice

---

## Verification Command

To verify the charge calculation logic is correct, run:

```bash
python3 trace_journal_amounts.py
```

This will show the complete data flow from source to journal entries.
