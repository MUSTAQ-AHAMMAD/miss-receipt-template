# Verification Report - Quick Reference Card

## 🚀 30-Second Quick Check

1. **Open** Verification_Report_TIMESTAMP.txt
2. **Look at** top checklist section
3. **Check** Overall Status
4. **Scan** for `[✗]` or `[⚠]` symbols

**If all `[✓]`** → Ready to import ✅
**If any `[✗]`** → Fix issues first ❌
**If any `[⚠]`** → Review details, may be OK ⚠️

---

## 📋 Checkbox Meanings

| Symbol | Status | Meaning | Action |
|--------|--------|---------|--------|
| `[✓]` | PASS | All good | None needed |
| `[✗]` | FAIL | Issue found | Must fix |
| `[⚠]` | WARN | Check needed | Review details |
| `[ℹ]` | INFO | FYI only | No action |

---

## 🎯 What Each Check Does

### Line Count Verification
**Checks**: All input rows → AR rows
**Pass**: Input count = Output count
**Fail**: Data loss during processing

### Amount Reconciliation
**Checks**: Receipt totals = Payment totals
**Pass**: Difference < 0.01 SAR
**Fail**: Missing payments or receipts

### AR vs Payment Match
**Checks**: AR total = Payment file total
**Pass**: Difference < 10 SAR (rounding OK)
**Warn**: > 10 SAR difference

### Segment Uniqueness
**Checks**: No duplicate segment values
**Pass**: All segments unique
**Fail**: Duplicates found (regenerate needed)

---

## 🔍 Payment Method Table

Find section: "PAYMENT METHOD RECONCILIATION"

**Look for**:
- `✓ OK` = Good (difference 0.00 or < 0.01)
- `⚠ CHECK` = Mismatch needs review
- `BNPL (No Rcpt)` = Expected for TAMARA/TABBY

**Common issue**: If Cash, Mada, Visa, or MasterCard show `⚠ CHECK`, review receipt generation for that method.

---

## 📊 CSV Summary for Excel

**File**: Verification_Report_TIMESTAMP_Summary.csv

**Quick Excel Steps**:
1. Open in Excel
2. Apply AutoFilter (Data → Filter)
3. Filter Status column to "FAIL" or "WARN"
4. Conditional formatting: Red=FAIL, Yellow=WARN, Green=PASS

---

## ✅ Ready to Import Checklist

- [ ] Overall Status = "ALL CHECKS PASSED"
- [ ] No `[✗]` failures in checklist
- [ ] All payment methods show `✓ OK`
- [ ] Line count matches (input = output)
- [ ] Amount difference < 10 SAR
- [ ] No segment duplicates

**If all checked** → Proceed to Oracle Fusion import

---

## ⚠️ Common Issues & Quick Fixes

### Issue: Line Count Mismatch
**Symptom**: `[✗] Line Count Verification`
**Fix**: Regenerate AR Invoice, check data quality

### Issue: Amount Mismatch
**Symptom**: `[✗] Amount Reconciliation`
**Fix**: Check Payment Method table, verify all methods have receipts

### Issue: Payment Method Shows ⚠ CHECK
**Symptom**: Difference > 0.01 in method table
**Fix**: Verify receipt files generated for that method

### Issue: Segment Duplicates
**Symptom**: `[✗] Segment 1/2 Uniqueness`
**Fix**: Regenerate AR Invoice (system error)

---

## 📁 File Outputs

**Text Report**: Verification_Report_TIMESTAMP.txt
- Quick checklist at top
- Detailed sections below
- Payment method table
- Date-wise comparison

**CSV Summary**: Verification_Report_TIMESTAMP_Summary.csv
- Excel-compatible
- Easy filtering
- Conditional formatting ready

**Both files** in output ZIP alongside AR Invoice and Receipts

---

## ⏱️ Time Estimates

**Quick check** (checklist only): 30 seconds
**Standard review** (checklist + payment methods): 1-2 minutes
**Deep dive** (full report + CSV): 5-10 minutes
**Troubleshooting**: 10-20 minutes

---

## 💡 Pro Tips

1. **Daily runs**: Just scan checklist, takes 30 sec
2. **Month-end**: Review payment method table too
3. **First time**: Read full report to understand
4. **Use Excel**: CSV makes trends visible
5. **Archive reports**: Keep for audit trail

---

## 🆘 Quick Troubleshooting

**Problem**: Can't find issue
**Solution**: Open CSV, filter by FAIL/WARN

**Problem**: Small difference in totals
**Solution**: If < 10 SAR on 100k+, it's rounding (OK)

**Problem**: TAMARA shows 0 receipts
**Solution**: That's correct - BNPL doesn't get receipts

**Problem**: Multiple issues
**Solution**: Start with line count, then amounts, then methods

---

## 📞 Need Help?

1. Read detailed section in verification report
2. Check ENHANCED_VERIFICATION_GUIDE.md
3. Review Payment Method Reconciliation table
4. Check processing logs in web UI
5. Regenerate from source files if needed

---

**Remember**: The goal is FAST manual verification!
- ✅ Green `[✓]` = Good
- ❌ Red `[✗]` = Fix
- ⚠️ Yellow `[⚠]` = Check

**Most common result**: All `[✓]`, takes 30 seconds, ready to import! 🎉
