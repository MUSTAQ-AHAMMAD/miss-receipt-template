# Bank Account Mapping - Mismatch & Issues Report

**Generated:** 2026-04-23
**Purpose:** Identify all mismatches, conflicts, and missing data for correction

---

## 🔴 CRITICAL ISSUES TO FIX

### Issue 1: 57 Stores Missing Bank Account Mappings

These stores exist in `RCPT_Mapping_DATA.csv` but have NO bank accounts in `Receipt_Methods.csv`:

| Store Name | Status | Impact |
|------------|--------|--------|
| AJAWEED | ❌ Missing | Will use fallback bank account |
| ALULA | ❌ Missing | Will use fallback bank account |
| AMWAJ | ❌ Missing | Will use fallback bank account |
| ANDLUS | ❌ Missing | Will use fallback bank account |
| ARARMALL | ❌ Missing | Will use fallback bank account |
| ASEER | ❌ Missing | Will use fallback bank account |
| ASEERGUNAI | ❌ Missing | Will use fallback bank account |
| AZIZMALL | ❌ Missing | Will use fallback bank account |
| BUROTHAIM | ❌ Missing | Will use fallback bank account |
| DAMMOTHAIM | ❌ Missing | Will use fallback bank account |
| DANA | ❌ Missing | Will use fallback bank account |
| DAREEN | ❌ Missing | Will use fallback bank account |
| EHSAA | ❌ Missing | Will use fallback bank account |
| EHSALBUSTA | ❌ Missing | Will use fallback bank account |
| EXBSA | ❌ Missing | Will use fallback bank account |
| EXBSA02 | ❌ Missing | Will use fallback bank account |
| EXBSA03 | ❌ Missing | Will use fallback bank account |
| EXBSA04 | ❌ Missing | Will use fallback bank account |
| FLAMINGO | ❌ Missing | Will use fallback bank account |
| GRANADA | ❌ Missing | Will use fallback bank account |
| GRMALLHAIL | ❌ Missing | Will use fallback bank account |
| HAFRBATIN | ❌ Missing | Will use fallback bank account |
| HAIFAA | ❌ Missing | Will use fallback bank account |
| HAMRAA | ❌ Missing | Will use fallback bank account |
| HAYAT | ❌ Missing | Will use fallback bank account |
| HIJABMALL | ❌ Missing | Will use fallback bank account |
| JBLIMALMAL | ❌ Missing | Will use fallback bank account |
| JUBAIL | ❌ Missing | Will use fallback bank account |
| LULUMAKKAH | ❌ Missing | Will use fallback bank account |
| LULUMADENA | ❌ Missing | Will use fallback bank account |
| MADINMUEAZ | ❌ Missing | Will use fallback bank account |
| MALZJUBAIL | ❌ Missing | Will use fallback bank account |
| MANAR | ❌ Missing | Will use fallback bank account |
| MJMAKRMMAL | ❌ Missing | Will use fallback bank account |
| NAKHELMALL | ❌ Missing | Will use fallback bank account |
| NAKJPLAZA | ❌ Missing | Will use fallback bank account |
| OTHAIMDAMM | ❌ Missing | Will use fallback bank account |
| PARKMALL | ❌ Missing | Will use fallback bank account |
| PENINSULA | ❌ Missing | Will use fallback bank account |
| RABWA | ❌ Missing | Will use fallback bank account |
| RASHIDMAD | ❌ Missing | Will use fallback bank account |
| REDSEAMALL | ❌ Missing | Will use fallback bank account |
| SALAMRYD | ❌ Missing | Will use fallback bank account |
| SAWARIJEDU | ❌ Missing | Will use fallback bank account |
| SMSYDMALL | ❌ Missing | Will use fallback bank account |
| SUNNYGRJED | ❌ Missing | Will use fallback bank account |
| TABOUKMALL | ❌ Missing | Will use fallback bank account |
| URWTHQAAIF | ❌ Missing | Will use fallback bank account |
| YASMALMALL | ❌ Missing | Will use fallback bank account |
| ZAHRAN | ❌ Missing | Will use fallback bank account |
| ZINJALWARD | ❌ Missing | Will use fallback bank account |

**Additional stores (partial list):**
- HILTONMAK, HILTONMAK2, HILTONMAK3
- LULUMAKKAH, LULUMADENA
- PANORAMA, PLAZA, RIYADH, etc.

**Total: 57 stores without bank account mappings**

---

## ⚠️ SUBSTRING MATCHING CONFLICTS

These store pairs have substring relationships that could cause incorrect bank account assignment:

### High-Risk Conflicts (Store name is substring of another)

| Shorter Name | Longer Name | Risk |
|--------------|-------------|------|
| ABHATIMSQR | CASHABHATIMSQR | ⚠️ Could match Cash account instead |
| ABHHIZAMST | CASHABHHIZAMST | ⚠️ Could match Cash account instead |
| ABHLVNDAPK | CASHABHLVNDAPK | ⚠️ Could match Cash account instead |
| ALAQEQRYD | CASHALAQEQRYD | ⚠️ Could match Cash account instead |
| ALARIDAH | CASHALARIDAH | ⚠️ Could match Cash account instead |
| ALBAHAMAL | CASHALBAHAMAL | ⚠️ Could match Cash account instead |
| ALMALGARYD | CASHALMALGARYD | ⚠️ Could match Cash account instead |
| ALQASRMALL | CASHALQASRMALL | ⚠️ Could match Cash account instead |
| ARABMALL | CASHARABMALLBRANCH | ⚠️ Could match wrong Cash account |
| ARABMALL | ARABMALL-015795017321008 | ⚠️ Ambiguous - multiple matches |
| ARARMHMDIA | CASHARARMHMDIA | ⚠️ Could match Cash account instead |
| ARARWOMNM2 | CASHARARWOMNM2 | ⚠️ Could match Cash account instead |
| ARARWOMNMT | CASHARARWOMNMT | ⚠️ Could match Cash account instead |
| ASEERGUNAIM | CASHASEERGUNAIM | ⚠️ Could match Cash account instead |
| AZIZIARYD | CASHAZIZIARYD | ⚠️ Could match Cash account instead |
| BAHAAVENUS | CASHBAHAAVENUS | ⚠️ Could match Cash account instead |
| BURIDHIMAM | CASHBURIDHIMAM | ⚠️ Could match Cash account instead |
| BURSULMAVE | CASHBURSULMAVE | ⚠️ Could match Cash account instead |
| HILTONMAK | HILTONMAK2 | ⚠️ Ambiguous - multiple stores |
| HILTONMAK | HILTONMAK3 | ⚠️ Ambiguous - multiple stores |
| CASHHILTONMAK | CASHHILTONMAK2 | ⚠️ Cash accounts conflict |
| CASHHILTONMAK | CASHHILTONMAK3 | ⚠️ Cash accounts conflict |
| PANORAMA | PANORAMA-WRONG | ⚠️ Could match wrong account |
| RASHIDMAD | RASHIDMAD2 | ⚠️ Ambiguous - multiple stores |
| SALAMMALL | SALAMMALLJEDDAHBRANCH | ⚠️ Could match branch account |

**Total: 127 substring conflicts detected**

### Why This Matters:

When the system searches for "ARABMALL", it uses substring matching (`store_upper in acct_upper`). This means:
- Searching for **"ARABMALL"** could incorrectly match **"CASHARABMALLBRANCH"**
- The **wrong bank account** would be assigned to receipts

---

## 🔄 DUPLICATE MAPPINGS

These store/method combinations have multiple bank account entries:

### Duplicate 1: AMEX + MAHMAL Store
**Problem:** Two identical entries for the same store/method

```
Method: AMEX
Store: RIYADH-MAHMAL-1831434139947
Accounts:
  - Account 1: 1831434139947 (Riyadh Bank - Mahmal - Acc # 1831434139947)
  - Account 2: 1831434139947 (Riyadh Bank - Mahmal - Acc # 1831434139947)
```

**Impact:** Duplicate entries - should be cleaned up

### Duplicate 2: Visa + MANARMALL Store
**Problem:** Two identical entries for the same store/method

```
Method: Visa
Store: MANARMALL
Accounts:
  - Account 1: 0022555612031 (AL Jazeerah Bank Al Manar Mall)
  - Account 2: 0022555612031 (AL Jazeerah Bank Al Manar Mall)
```

**Impact:** Duplicate entries - should be cleaned up

---

## 🔍 PAYMENT METHOD MISMATCHES

### Missing Method: "MasterCard"

**Issue:** The code expects payment method "MasterCard" but Receipt_Methods.csv uses "Master"

```
Expected in code: MasterCard
Found in data:    Master
```

**Impact:**
- MISS receipts won't be generated for "MasterCard" transactions
- Only "Master" will generate MISS receipts
- Check if your payment data uses "Master" or "MasterCard"

**Fix:** Either:
1. Update code to use "Master" instead of "MasterCard"
2. OR update Receipt_Methods.csv to use "MasterCard"

### Missing Method: "Amex"

**Issue:** The code might expect "Amex" but Receipt_Methods.csv uses "AMEX"

```
Expected: Amex
Found:    AMEX
```

**Impact:** Minor - case sensitivity might cause issues

---

## 📊 STATISTICS SUMMARY

| Category | Count | Status |
|----------|-------|--------|
| Total Bank Account Records | 1,390 | ✅ |
| Unique Stores in Mappings | 488 | ✅ |
| Stores in RCPT_Mapping_DATA | 189 | ✅ |
| **Missing Store Mappings** | **57** | ❌ |
| **Substring Conflicts** | **127** | ⚠️ |
| **Duplicate Entries** | **2** | ⚠️ |
| Payment Methods Configured | 9 | ✅ |

---

## 🎯 RECOMMENDED ACTIONS

### Priority 1: Add Missing Store Mappings

Add bank account entries to `Receipt_Methods.csv` for these 57 stores:

```csv
ORGANIZATION_ID,ORG_NAME,RECEIPT_METHOD_NAME,BANK_ACCOUNT_NAME,BANK_ACCOUNT_NUMBER
300000052613062,AlQurashi-KSA,Cash,AL Jazeerah Bank AJAWEED,[BANK_ACCOUNT_NUMBER]
300000052613062,AlQurashi-KSA,Mada,AL Jazeerah Bank AJAWEED,[BANK_ACCOUNT_NUMBER]
300000052613062,AlQurashi-KSA,Visa,AL Jazeerah Bank AJAWEED,[BANK_ACCOUNT_NUMBER]
... (repeat for each missing store and payment method)
```

**For each missing store, you need to add entries for ALL payment methods:**
- Cash
- Mada
- Visa
- Master (or MasterCard)
- AMEX
- GCCNET
- Wire (if applicable)

### Priority 2: Fix Substring Conflicts

**Option A:** Use exact store name matching (requires code change)
**Option B:** Rename conflicting entries in Receipt_Methods.csv to avoid substrings

For example:
- Change "CASHABHATIMSQR" → "CASH ABHATIMSQR ONLY" (to avoid matching ABHATIMSQR)
- Or ensure ABHATIMSQR entries are listed BEFORE CASHABHATIMSQR entries

### Priority 3: Remove Duplicate Entries

Delete duplicate rows in Receipt_Methods.csv:
1. AMEX + MAHMAL - remove one duplicate entry
2. Visa + MANARMALL - remove one duplicate entry

### Priority 4: Standardize Payment Method Names

Decide on standard names and update everywhere:
- Use "Master" OR "MasterCard" (not both)
- Use "AMEX" OR "Amex" (not both)

---

## 📋 VERIFICATION CHECKLIST

After making corrections, verify:

- [ ] All 57 missing stores have bank account entries added
- [ ] Each store has entries for ALL payment methods (Cash, Mada, Visa, Master, AMEX)
- [ ] Duplicate entries removed from Receipt_Methods.csv
- [ ] Substring conflicts resolved (either via renaming or code fix)
- [ ] Payment method names standardized
- [ ] Run `verify_bank_account_mapping.py` again to confirm fixes
- [ ] Generate test receipts and check verification report
- [ ] Spot-check generated CSV files for correct bank accounts

---

## 🛠️ HOW TO USE THIS REPORT

1. **Review Missing Stores List** - Identify which stores need bank accounts
2. **Gather Bank Account Information** - Get actual bank account numbers for each missing store
3. **Update Receipt_Methods.csv** - Add new rows for missing stores
4. **Clean Up Duplicates** - Remove duplicate entries
5. **Re-run Verification** - Execute `python verify_bank_account_mapping.py`
6. **Test with Real Data** - Generate receipts and verify bank accounts are correct

---

## 📝 NEXT STEPS

1. **Provide bank account numbers** for the 57 missing stores
2. **Update Receipt_Methods.csv** with the new entries
3. **Re-run verification tool** to confirm all issues are resolved
4. **Generate test receipts** to verify the mapping works correctly

---

*Generated by Bank Account Mapping Verification Tool*
*Date: 2026-04-23*
