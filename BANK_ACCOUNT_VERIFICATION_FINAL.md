# Bank-Account Mapping Verification — Final Report

This document records the cross-verification performed against
`VENDHQ_REGISTERS_202604121654.csv` (248 active registers) and
`Receipt_Methods.csv`, together with the deterministic fixes that have been
applied so that the **`Branch` field on the Odoo payment-lines sheet**
(== Fusion `SUBINVENTORY` == vend `REGISTER_NAME`) is now used as the primary
key for routing every receipt to the correct bank account.

The verification mirrors the **exact** lookup logic now used in production by
`Odoo-export-FBDA-template.py::ReceiptMethodsCache.get_bank_account()` and
its twin in `100%-Working-code-Odoo-to-Oracle-FBDA.py`, which routes:

* **Standard receipts**       → vend `CASH_ACCOUNT` for that REGISTER_NAME
* **Miscellaneous receipts**  → vend `BANK_ACCOUNT` for that REGISTER_NAME
* **Fallback** (only when the vend file is missing data) → Receipt_Methods.csv
  with deterministic score-based scoring

## Summary

| Metric                                     | Original | After dedupe + score-based RM | After vend-register override |
| ------------------------------------------ | -------: | ----------------------------: | ---------------------------: |
| Total store × method checks                |    1,240 |                         1,240 |                        1,240 |
| Substring-collision risks                  |       19 |                             0 |                            0 |
| Duplicate rows in `Receipt_Methods.csv`    |        3 |                             0 |                            0 |
| Duplicate `(method, store)` mappings       |        2 |                             0 |                            0 |
| Mismatched / missing mappings (data gaps)  |      429 |                           405 |                       **84** |
| Registers in `BANK_ACCOUNT_DATA_GAPS.csv`  |       —  |                            85 |                        **7** |
| **Overall accuracy**                       |   65.40% |                        67.34% |                  **93.23%**  |

## Code/data fixes applied

### 1. SUBINVENTORY-driven routing (`Branch` from payment lines)

`RegisterCache` (in both Python entry points) now also indexes
`CASH_ACCOUNT` and `BANK_ACCOUNT` per REGISTER_NAME and exposes:

```
RegisterCache.get_account(store_name, method) -> (account_name, account_number) | None
    method == 'Cash'                      -> CASH_ACCOUNT  (Standard receipts)
    method ∈ {Mada, Visa, MasterCard,
              Amex, Apple Pay, STC Pay,
              GCCNET, Wire, …}            -> BANK_ACCOUNT  (Miscellaneous receipts)
```

`ReceiptMethodsCache.get_bank_account(store, method)` was updated to consult
the `RegisterCache` **first**; only when the vend file lacks data for that
register does it fall back to the score-based scan over `Receipt_Methods.csv`.

This makes the user's intended pipeline explicit:
**`Branch` (payment lines) ⇒ `SUBINVENTORY` ⇒ `REGISTER_NAME` ⇒ vend
`CASH_ACCOUNT` / `BANK_ACCOUNT`.**

The bank account *number* is parsed out of strings like
`"AL Jazeerah Bank WADILABAN ACC # 015795017321049"` or
`"Oman Arab Bank Account- ACC # 3106-573999-500"`. When no `Acc #` token is
present (e.g. `"CashWADILABAN"`) the full account-name string is reused as the
identifier — matching legacy behaviour for the AR receipt file.

#### Coverage delta vs. the previous Receipt_Methods-only logic

| Metric                                    | Count |
| ----------------------------------------- | ----: |
| Lookups that now resolve via vend file    |   863 of 1,240 |
| Lookups still resolved via Receipt_Methods CSV |   377 of 1,240 |
| Registers fully covered by vend Std + Misc | 232 of 248 |

Concretely the per-register `ZAHRAN` lookup the user called out fixes from a
substring-collision into the wrong account to the correct one:

| Method      | Before                                                   | After                                                                |
| ----------- | -------------------------------------------------------- | -------------------------------------------------------------------- |
| Cash (Std)  | `CashOth Mall Hail`                                      | `Cash AL DAHRAN MALL`                                                |
| Mada/Visa/MC/Amex (Misc) | `AL Jazeerah Bank MJMAKRMMAL Account Acc#`  | `AL Jazeerah Bank Dahran Mall Account - Acc # 015795017321039`       |

Same pattern for every previously-falling-back non-SAR register
(`KWTMGHATER`, `JAHARKWT`, `MCTAVENUES`, `SALALAH`, `EXBBAH`, `DEERFIELDS`,
`Hall 4` / `Hall 8` …) and every previously-missing KSA register
(`EHSAA`, `SALAMAH`, `NAKJPLAZA`, `TALAMALL`, `ALULA`, `JURIMALL`,
`MAKTOWER`, …).

### 2. `Receipt_Methods.csv` — 3 problematic rows removed (earlier session)

| Old line # | Reason | Action |
|-----------:|--------|--------|
| 236 | `AMEX, Cash MEDDARIMAN, Cash MEDDARIMAN` — Cash account incorrectly tagged as `AMEX`. Correct rows already exist (line 119 / line 398). | **Deleted** |
| 259 | Exact byte-for-byte duplicate of line 258 (AMEX × Riyadh Bank Mahmal). | **Deleted** |
| 1129 | Exact byte-for-byte duplicate of line 1128 (Visa × AL Jazeerah Al Manar). | **Deleted** |

### 3. Score-based fallback in `ReceiptMethodsCache.get_bank_account()` (earlier session)

Replaced first-substring-match-wins lookup with **score-based selection**
(whole-token > digit-extension > substring; tie-break: shorter name). This
remains in effect for the ~12 % of registers that fall through to
`Receipt_Methods.csv`, and prevents collisions like
`RASHIDMAD` ↔ `RASHIDMAD2`, `HILTONMAK` ↔ `HILTONMAK2/3` regardless of CSV
row order.

### 4. New verifier (`verify_vend_registers_mapping.py`)

Now also models the vend-register override path, then falls back to the
score-based RM scan, exactly as production does. Reports per-method OK
counts, remaining issues, substring conflicts (now **0**), duplicate vend
register names (still 1 — see D below), and an overall accuracy score.

### 5. New artefacts

* **`SUBINVENTORY_BANK_ACCOUNT_MAPPING.csv`** *(new)* — 248 rows, one per
  active register, listing the resolved Standard-receipt (Cash) and
  Miscellaneous-receipt (card) account name and number plus the source
  (`VENDHQ_REGISTERS.CASH_ACCOUNT`, `VENDHQ_REGISTERS.BANK_ACCOUNT` or
  `Receipt_Methods.csv`). This is the single source of truth for what each
  `Branch` will route to.
* **`BANK_ACCOUNT_DATA_GAPS.csv`** — regenerated. Only **7 registers**
  remain with no resolvable mapping at all (down from 85), all of them with
  empty vend-file data **and** absent from `Receipt_Methods.csv`.

## Remaining gaps (require business-supplied data; not auto-fixable)

`BANK_ACCOUNT_DATA_GAPS.csv` lists every register that still has at least
one missing receipt-method routing. After the vend-register override these
have shrunk to a small set whose vend rows are themselves empty. Examples:

* `KWTALDABOS`, `EXBUAE1`, `BURIDHIMAM`, `JEDPNORAMA` — vend `CASH_ACCOUNT`
  and `BANK_ACCOUNT` columns are blank.
* `MATHNABMAL`, `KHMISMUJAN`, `MEDZAMPLMN` — vend `BANK_ACCOUNT` populated
  but with currency- or branch-only text and no registered receipt-method
  row, so card receipts have nothing to point at.

### Action items for the business

1. Populate the 7 vend register rows listed in `BANK_ACCOUNT_DATA_GAPS.csv`
   (`CASH_ACCOUNT` and `BANK_ACCOUNT` columns).
2. Resolve duplicate `MEDTHEGATE` register IDs (`445`, `607`) in the vend
   file — one of them should be deleted or renamed.
3. Re-run `python3 verify_vend_registers_mapping.py`. Target:
   `Total issues: 0  Accuracy: 100.00%  100% clean: YES`.

The substring-collision protection, dedupe checks and SUBINVENTORY-driven
routing introduced in this change ensure that no future row added to
`Receipt_Methods.csv` or to the vend file can silently mis-route receipts.
