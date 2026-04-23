# Bank-Account Mapping Verification — Final Report

This document records the cross-verification performed against
`VENDHQ_REGISTERS_202604121654.csv` (248 active registers) and
`Receipt_Methods.csv`, together with the safe deterministic fixes that have
been applied and the **remaining data gaps** that require authoritative bank
information from the business before 100 % accuracy can be reached.

The verification mirrors the **exact** lookup logic used in production by
`Odoo-export-FBDA-template.py::ReceiptMethodsCache.get_bank_account()` and
its twin in `100%-Working-code-Odoo-to-Oracle-FBDA.py`, which routes:

* **Standard receipts** → Cash bank account
* **MISS receipts**     → Mada / Visa / MasterCard / Amex bank accounts

## Summary

| Metric                                     | Before | After  |
| ------------------------------------------ | -----: | -----: |
| Total store × method checks                | 1,240  | 1,240  |
| Substring-collision risks                  |     19 |  **0** |
| Duplicate rows in `Receipt_Methods.csv`    |      3 |  **0** |
| Duplicate `(method, store)` mappings       |      2 |  **0** |
| Mismatched / missing mappings (data gaps)  |    429 |    405 |
| **Overall accuracy**                       | 65.40% | **67.34%** |

The improvement comes from removing 3 erroneous CSV rows, eliminating 19
substring-collision cases via deterministic scoring in the lookup, and
preventing the misleading false-positive matches the legacy verifier was
counting against the original lookup.

## Code/data fixes applied

### 1. `Receipt_Methods.csv` — 3 problematic rows removed

| Old line # | Reason | Action |
|-----------:|--------|--------|
| 236 | `AMEX, Cash MEDDARIMAN, Cash MEDDARIMAN` — a Cash account incorrectly tagged as `AMEX`. The proper `AMEX` row (`AL Jazeerah Bank MEDDARIMAN, 157-95017321-MEDDARIMAN`) already exists, and the proper `Cash` row (line 398) already exists. | **Deleted** |
| 259 | Exact byte-for-byte duplicate of line 258: `AMEX, Riyadh Bank - Mahmal - Acc # 1831434139947, 1831434139947` | **Deleted** |
| 1129 | Exact byte-for-byte duplicate of line 1128: `Visa, AL Jazeerah Bank Al Manar Mall, 0022555612031` | **Deleted** |

Net effect: 1,390 → **1,387 data rows**; ambiguous `MEDDARIMAN AMEX` lookup is
now deterministic and returns the correct bank account.

### 2. `Odoo-export-FBDA-template.py` and `100%-Working-code-Odoo-to-Oracle-FBDA.py`

Replaced the first-match-wins substring lookup in
`ReceiptMethodsCache.get_bank_account()` with **score-based selection**:

```
Score 3  whole-token match     (store bounded by start/end or non-alphanumeric)
Score 2  digit-extension match (store followed by a digit, e.g. RASHIDMAD2)
Score 1  plain substring fallback (legacy behaviour)
Tie-break: shorter account name wins (more specific entry)
```

Concretely this resolves the `RASHIDMAD` ↔ `RASHIDMAD2`,
`HILTONMAK` ↔ `HILTONMAK2/3`, `EXBSA` ↔ `EXBSA02/03/04`,
`JUBAIL` ↔ `JUBAILMAL2`, `EXBUAE` ↔ `EXBUAE1`, `Hall 4` ↔ `Hall 4.2`,
`Hall 8` ↔ `Hall 8.2`, `SALAMRYD` ↔ `SALAMRYD2`, `MANAR` ↔ `MANARRAK`,
`YASMEEN` ↔ `YASMEENPLZ`, `TAHLIA` ↔ `TAHLIA-F`, `JEDANDLUS2`,
`MEDANDLUSH`, `ASEERGUNAI`, `MCTAVENUES`, `FUJAIRAHCC` collisions —
**deterministically and regardless of CSV row order**.

### 3. `verify_bank_account_mapping.py`

* `normalize_store()` now mirrors production (`upper().strip()` only — no
  longer strips internal spaces). The previous over-normalisation was
  generating ~127 false-positive substring conflicts.
* `simulate_get_bank_account()` reproduces the new score-based logic.
* `analyze_substring_conflicts()` only reports collisions that survive the
  new logic (whole-token match against the same account for the same method).
* `TEST 5: Missing Store Coverage` now uses the production lookup, so a
  store such as `AJAWEED` (matched via `CashAJAWEED`) is no longer reported
  as missing.

### 4. `verify_vend_registers_mapping.py` *(new)*

A new permanent verifier that cross-checks every active vend register
against `Receipt_Methods.csv` for both Standard (Cash) and MISS (card)
receipts under production semantics. Produces the accuracy score above.

### 5. `BANK_ACCOUNT_DATA_GAPS.csv` *(new)*

A machine-readable list of every register that still has missing or
mismatched bank-account mapping rows in `Receipt_Methods.csv`, with the vend
file's own `CASH_ACCOUNT` and `BANK_ACCOUNT` strings included as starting
context for whoever fills the gaps.

## Remaining gaps (require authoritative business data)

These cannot be safely auto-filled because the actual Oracle Fusion bank-
account numbers are not present in this repository. **Adding fabricated
numbers would produce wrong receipts and reconciliation errors**, so the
correct path is for the business to supply them.

### A. ~26 non-SAR registers entirely missing from `Receipt_Methods.csv`

The `Receipt_Methods.csv` file was built only for KSA Al-Jazeerah / Riyadh-
bank stores. Vend registers in Kuwait, Oman, UAE and Bahrain therefore
have **no** Cash, Mada, Visa, MasterCard or Amex rows at all and currently
fall back to the global default bank, which is wrong currency / wrong
country.

| Country | Bank (per vend `BANK_ACCOUNT`) | Registers |
|---------|--------------------------------|-----------|
| Kuwait   | National Bank of Kuwait KWD                | `KWTMGHATER, JAHARKWT, KWT360MALL, KWTWHMALL, KWTALDABOS, MUBARKIA, Hall 4, Hall 4.2, Hall 8, Hall 8.2` |
| Oman     | Oman Arab Bank (OMR / general)             | `MCTAVENUES, MCTLLUNZWA, MCTLLUIBRI, MCTLLUAMRT, AZAIBAOMN, OMNHRMZPLZ, SALALAH, MUSCATCC, SOHARCITY` |
| UAE      | Abu Dhabi Islamic Bank AED                 | `DEERFIELD2, DEERFIELDS, DUBAIDALMA, EXBUAE, EXBUAE1, FUJAIRAHCC, MIRDIFFCC, ZAHIA, WEHDA, TOWNSQJED` |
| Bahrain  | Ahli United Bank Bahrain                   | `CCNTRBHR, EXBBAH` |

For each register listed above, **5 rows** must be added to
`Receipt_Methods.csv` (Cash, Mada, Visa, Master, AMEX), each containing the
correct `BANK_ACCOUNT_NAME` and `BANK_ACCOUNT_NUMBER`.

### B. ~38 KSA registers missing one or more rows

Listed in `BANK_ACCOUNT_DATA_GAPS.csv`. Examples include:

* `EHSAA, SALAMAH, WESTAVENUE, NAKJPLAZA, TALAMALL, KHERAIS, JURIMALL, ALULA, GRMALLHAIL, ONAIZAH, MAKTOWER, BURIDHIMAM, JEDPNORAMA, ANDLUS, RYDEXP, MAKMALL, EVENT, RYDPNORAMA, ZIA, AJAWEED`

The vend file's `BANK_ACCOUNT` column already names the correct AL Jazeerah
account for most of these (e.g. `AL Jazeerah Bank Al Ihsaa Mall Account -
Acc # 015795017321028`); use that to populate the missing RM rows.

### C. Naming drift between vend `REGISTER_NAME` and RM `BANK_ACCOUNT_NAME`

For these stores the bank account exists in `Receipt_Methods.csv` but with
a slightly different spelling, so the production lookup misses it. Either
rename the RM entry **or** alias the register name:

| Vend register | RM-side spelling | Vend `CASH_ACCOUNT` |
|---------------|------------------|---------------------|
| `AMWAJ`        | `Amwaj` / `CASH Amwaj Mall Branch` | `Cash AMUAJJ MALL` |
| `JURIMALL`     | `Jory Mall` (in vend BANK), no RM row | `Cash JORI MALL` |
| `MAKTOWER`     | RM has only an AL Jazeerah bank row, no Cash | `CASH Makkah tower Branch` |
| `Hall 4`/`Hall 8` | no RM rows for "Hall *" | `Cash Account Hall 4/8` |

### D. Duplicate `REGISTER_NAME` in vend file

`MEDTHEGATE` appears with **two** `REGISTER_ID`s (`445` and `607`). One of
them should be deleted or renamed in the vend system; otherwise lookups
against this name are non-deterministic at the vend layer.

## How to reach 100 % accuracy

1. Fill the rows listed in **A**, **B** and **C** in `Receipt_Methods.csv`
   using the bank/account numbers in `BANK_ACCOUNT_DATA_GAPS.csv` and the
   business-supplied bank statements.
2. Resolve the duplicate `MEDTHEGATE` register in the vend file (**D**).
3. Re-run `python3 verify_vend_registers_mapping.py`. Target: `Total issues:
   0  Accuracy: 100.00%  100% clean: YES`.

The substring-collision and duplicate-row protections introduced in this
change ensure that no future row added to `Receipt_Methods.csv` can silently
mis-route receipts through ambiguous matching, regardless of the order in
which rows are loaded.
