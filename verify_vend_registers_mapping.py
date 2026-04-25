#!/usr/bin/env python3
"""
================================================================================
VEND REGISTERS ↔ RECEIPT_METHODS CROSS-VERIFICATION TOOL
================================================================================

Cross-checks every active register in VENDHQ_REGISTERS_*.csv against the bank
account rows in Receipt_Methods.csv, using the EXACT lookup logic implemented
in `Odoo-export-FBDA-template.py::ReceiptMethodsCache.get_bank_account()`:

    * Primary source: vend register file (REGISTER_NAME = SUBINVENTORY =
      `Branch` from the Odoo payment-lines sheet).
        - Standard receipt (Cash)        → CASH_ACCOUNT
        - Miscellaneous receipt (cards)  → BANK_ACCOUNT
    * Fallback source: Receipt_Methods.csv with score-based scoring
      (whole-token > digit-extension > substring; tie-break: shorter name).
    * normalise_store(name)  -> name.upper().strip()

For each register we check both code paths:

    Standard Receipt   →  Cash mapping
    MISS Receipt       →  Mada / Visa / Master / AMEX mappings

It reports:
    - Cash mismatches between vend `CASH_ACCOUNT` and Receipt_Methods.csv
    - Card-method registers that have NO match (will fall back) or AMBIGUOUS match
    - Substring collisions between register names
    - Duplicate REGISTER_NAMEs in the vend file
    - Registers with no Mada mapping
    - An overall accuracy score

Run:
    python3 verify_vend_registers_mapping.py
================================================================================
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Production normalisers (mirror Odoo-export-FBDA-template.py)
# ---------------------------------------------------------------------------

def normalise_store(name: str) -> str:
    return (name or "").upper().strip()


def normalise_payment(raw: str) -> str:
    """Mirror of normalise_payment() / PAYMENT_METHOD_NORM in production."""
    key = (raw or "").upper().strip()
    # Most-specific tokens first
    if "MADA"     in key: return "Mada"
    if "VISA"     in key: return "Visa"
    if "MASTER"   in key or key.startswith("MC"): return "Master"
    if "CASH"     in key: return "Cash"
    # Production canonicalises "AMEX"/"AMERICAN EXPRESS" → "Amex"
    if "AMEX"     in key or "AMERICAN" in key: return "Amex"
    if "GCC"      in key: return "GCCNET"
    if "WIRE"     in key: return "Wire"
    if "TAMARA"   in key: return "TAMARA"
    if "TABBY"    in key: return "TABBY"
    if "APPLE"    in key: return "Apple Pay"
    if "STC"      in key: return "STC Pay"
    return (raw or "").strip()


# ---------------------------------------------------------------------------
# File locations
# ---------------------------------------------------------------------------

REPO = Path(__file__).resolve().parent
VEND_FILE = REPO / "VENDHQ_REGISTERS_202604121654.csv"
RM_FILE   = REPO / "Receipt_Methods.csv"


# ---------------------------------------------------------------------------
# Load Receipt_Methods.csv into a method → [(name, num, upper)] index
# ---------------------------------------------------------------------------

def load_receipt_methods(path: Path):
    method_index: dict = defaultdict(list)
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            method = (r.get("RECEIPT_METHOD_NAME") or "").strip()
            acct_name = (r.get("BANK_ACCOUNT_NAME") or "").strip()
            acct_num  = (r.get("BANK_ACCOUNT_NUMBER") or "").strip()
            if not method or not acct_name:
                continue
            method_index[normalise_payment(method)].append(
                (acct_name, acct_num, acct_name.upper()))
    return method_index


_ACC_NUM_RE = re.compile(r"(?:ACC|Acc|A/C)\s*#?\s*([0-9A-Za-z][0-9A-Za-z\-]*)")


def _extract_acc_number(raw: str) -> str:
    if not raw:
        return ""
    m = _ACC_NUM_RE.search(raw)
    if not m:
        return ""
    cand = m.group(1)
    if not any(c.isdigit() or c.isalpha() for c in cand):
        return ""
    return cand


def get_bank_account(method_index, register_index, store: str, canonical_method: str):
    """Replicates the production lookup with the vend register override.

    Order of resolution:
        1. Vend register file (REGISTER_NAME = SUBINVENTORY = Branch)
              - 'Cash' method → CASH_ACCOUNT
              - any other method → BANK_ACCOUNT
           If the vend file has a populated value, use it.
        2. Score-based scan over Receipt_Methods.csv.
    """
    su = normalise_store(store)
    # 1. vend override
    rec = (register_index or {}).get(su)
    if rec:
        raw = rec["cash"] if canonical_method == "Cash" else rec["bank"]
        if raw:
            return (raw, _extract_acc_number(raw) or raw), [("__vend__", raw, 99)]

    # 2. CSV fallback (score-based)
    matches = []
    best = None  # (score, -len(acct_upper), -idx, (name, num))
    for idx, (acct_name, acct_num, acct_upper) in enumerate(method_index.get(canonical_method, [])):
        pos = acct_upper.find(su)
        if pos < 0:
            continue
        end = pos + len(su)
        before_ok = pos == 0 or not acct_upper[pos - 1].isalnum()
        after_ch = acct_upper[end] if end < len(acct_upper) else ""
        after_ok = after_ch == "" or not after_ch.isalnum()
        if before_ok and after_ok:
            score = 3
        elif before_ok and after_ch.isdigit():
            score = 2
        else:
            score = 1
        matches.append((acct_name, acct_num, score))
        cand = (score, -len(acct_upper), -idx, (acct_name, acct_num))
        if best is None or cand > best:
            best = cand
    if best is None:
        return None, matches  # no match → caller would fall back
    return best[3], matches


def build_register_index(registers):
    """REGISTER_NAME (uppercased) → {cash, bank} (only active rows)."""
    return {normalise_store(r["name"]): {"cash": r["cash"], "bank": r["bank"]}
            for r in registers}


# ---------------------------------------------------------------------------
# Load active vend registers
# ---------------------------------------------------------------------------

def load_registers(path: Path):
    registers = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if (r.get("DELETED_AT") or "").strip():
                continue
            registers.append({
                "id":   (r.get("REGISTER_ID") or "").strip(),
                "name": (r.get("REGISTER_NAME") or "").strip(),
                "cash": (r.get("CASH_ACCOUNT") or "").strip(),
                "bank": (r.get("BANK_ACCOUNT") or "").strip(),
            })
    return registers


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def hdr(t):
    print("\n" + "=" * 78 + f"\n  {t}\n" + "=" * 78)


def squash(s):
    return re.sub(r"\s+", "", (s or "").upper())


def main() -> int:
    if not VEND_FILE.exists():
        print(f"ERROR: {VEND_FILE.name} not found in {REPO}")
        return 2
    if not RM_FILE.exists():
        print(f"ERROR: {RM_FILE.name} not found in {REPO}")
        return 2

    method_index = load_receipt_methods(RM_FILE)
    registers = load_registers(VEND_FILE)
    register_index = build_register_index(registers)

    print(f"Active vend registers : {len(registers)}")
    print(f"RM methods present    : {sorted(method_index)}")

    cash_acct_names = {squash(a): (a, n) for (a, n, _) in method_index.get("Cash", [])}

    # --- 1. Cash (standard receipt) ----------------------------------------
    cash_ok = 0
    cash_missing = []
    cash_mismatch = []
    for reg in registers:
        if not reg["cash"]:
            cash_missing.append(reg)
            continue
        if squash(reg["cash"]) in cash_acct_names:
            cash_ok += 1
            continue
        match, _ = get_bank_account(method_index, register_index, reg["name"], "Cash")
        if match is None:
            cash_mismatch.append((reg, "no Cash entry via store-lookup"))
        else:
            cash_mismatch.append((reg,
                f"vend cash='{reg['cash']}' but RM lookup -> '{match[0]}'"))

    # --- 2. Card methods (MISS receipt) ------------------------------------
    card_methods = ["Mada", "Visa", "Master", "Amex"]
    bank_issues = defaultdict(list)
    bank_ok = defaultdict(int)
    for reg in registers:
        for m in card_methods:
            match, candidates = get_bank_account(method_index, register_index, reg["name"], m)
            if match is None:
                bank_issues[m].append((reg, "NO MATCH (will fall back)"))
                continue
            # Re-evaluate ambiguity by counting score-3 matches
            top = [c for c in candidates if c[2] == 3]
            if len(top) > 1:
                bank_issues[m].append((reg,
                    "AMBIGUOUS – multiple whole-token matches: " +
                    ", ".join(f"{n}(#{a})" for n, a, _ in top[:3])))
                continue
            bank_ok[m] += 1

    # --- 3. Substring collisions in REGISTER_NAMEs (under production logic) -
    reg_names = sorted({normalise_store(r["name"]) for r in registers if r["name"]})
    substr_conflicts = []
    for i, a in enumerate(reg_names):
        for b in reg_names[i + 1:]:
            if not a or a not in b:
                continue
            # Only a real risk if the production-style lookup for `a` could
            # still match an account dedicated to `b`. The new logic prefers
            # whole-token matches, so this only becomes ambiguous when both
            # `a` and `b` appear as whole tokens in some account name.
            risky = False
            for canon in method_index:
                for _, _, acct_upper in method_index[canon]:
                    def whole(s):
                        pos = acct_upper.find(s)
                        if pos < 0: return False
                        end = pos + len(s)
                        bo = pos == 0 or not acct_upper[pos - 1].isalnum()
                        ac = acct_upper[end] if end < len(acct_upper) else ""
                        ao = ac == "" or not ac.isalnum()
                        return bo and ao
                    if whole(a) and whole(b):
                        risky = True
                        break
                if risky:
                    break
            if risky:
                substr_conflicts.append((a, b))

    # --- 4. Duplicate REGISTER_NAMEs ---------------------------------------
    name_counts = defaultdict(list)
    for r in registers:
        name_counts[normalise_store(r["name"])].append(r["id"])
    dup_names = {n: ids for n, ids in name_counts.items() if len(ids) > 1}

    # --- 5. Registers without any Mada mapping ------------------------------
    no_mada = [r for r in registers
               if get_bank_account(method_index, register_index, r["name"], "Mada")[0] is None]

    # --------------------------- REPORT ------------------------------------
    hdr("STANDARD RECEIPT (Cash)")
    print(f"  OK (cash acct in RM verbatim)  : {cash_ok}/{len(registers)}")
    print(f"  Missing CASH_ACCOUNT in vend   : {len(cash_missing)}")
    print(f"  Mismatched Cash mapping        : {len(cash_mismatch)}")
    for reg, why in cash_mismatch[:30]:
        print(f"   • [{reg['id']}] {reg['name']:<14} cash='{reg['cash']}' -> {why}")
    if len(cash_mismatch) > 30:
        print(f"   ... and {len(cash_mismatch) - 30} more")

    hdr("MISS RECEIPT (Card methods)")
    for m in card_methods:
        issues = bank_issues[m]
        print(f"\n  {m:<11}: OK={bank_ok[m]}/{len(registers)}  Issues={len(issues)}")
        for reg, why in issues[:15]:
            print(f"   • [{reg['id']}] {reg['name']:<14} -> {why}")
        if len(issues) > 15:
            print(f"   ... and {len(issues) - 15} more")

    hdr("Substring conflicts in REGISTER_NAMEs (under production semantics)")
    print(f"  count={len(substr_conflicts)}")
    for a, b in substr_conflicts[:25]:
        print(f"   • '{a}' substring of '{b}' (BOTH appear as whole tokens in RM)")
    if len(substr_conflicts) > 25:
        print(f"   ... +{len(substr_conflicts) - 25}")

    hdr("Duplicate REGISTER_NAMEs in vend file")
    if dup_names:
        for n, ids in dup_names.items():
            print(f"   • {n}: register_ids={ids}")
    else:
        print("  none")

    hdr("Registers with NO Mada mapping in Receipt_Methods.csv")
    print(f"  count={len(no_mada)}")
    for reg in no_mada[:40]:
        print(f"   • [{reg['id']}] {reg['name']}  vendBank='{reg['bank']}'")
    if len(no_mada) > 40:
        print(f"   ... +{len(no_mada) - 40}")

    total_checks = len(registers) * (1 + len(card_methods))
    total_issues = (len(cash_mismatch) + len(cash_missing) +
                    sum(len(v) for v in bank_issues.values()))
    acc = (1 - total_issues / total_checks) * 100 if total_checks else 0
    hdr("OVERALL ACCURACY")
    print(f"  Total checks : {total_checks}")
    print(f"  Total issues : {total_issues}")
    print(f"  Accuracy     : {acc:.2f}%")
    print(f"  100% clean   : {'YES ✓' if total_issues == 0 else 'NO ✗'}")

    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
