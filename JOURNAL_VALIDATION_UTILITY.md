# Journal Entry Validation and Fix Utility

## Overview

This utility provides comprehensive validation and automatic fixing for unbalanced journal entries based on strict accounting system rules used in Oracle Fusion Financial integration.

## Files

- **`validateAndFixJournalEntries.js`** - Main validation utility function

## System Rules

### Rule 1: Account Series Validation

- **3-series accounts** (e.g., `3020044`) MUST ALWAYS be in the **Debit** column
- **5-series accounts** (e.g., `5000104`) MUST ALWAYS be in the **Credit** column
- If a 3-series account has a value in the Credit column, it's **WRONG**
- If a 5-series account has a value in the Debit column, it's **WRONG**

### Rule 2: Balance Validation

- Sum of ALL Entered Debit Amounts MUST EQUAL Sum of ALL Entered Credit Amounts
- Sum of ALL Converted Debit Amounts MUST EQUAL Sum of ALL Converted Credit Amounts
- If these don't match, the journal will throw an error and cannot be posted

### Rule 3: Root Cause of Imbalance

- When debits and credits don't balance, it's ALWAYS because an amount was placed in the WRONG column
- The correct amount exists, but it's on the wrong side (debit instead of credit, or credit instead of debit)

## Data Structure

Each journal entry object has these fields:

```javascript
{
  accountNumber: string,        // e.g., "3020044" or "5000104"
  enteredDebitAmount: number,   // amount in debit column
  enteredCreditAmount: number,  // amount in credit column
  convertedDebitAmount: number, // converted currency debit amount
  convertedCreditAmount: number // converted currency credit amount
}
```

## Function Signature

```javascript
validateAndFixJournalEntries(entries)
```

### Parameters

- **`entries`** (Array): Array of journal entry objects

### Returns

```javascript
{
  isValid: boolean,
  accountSeriesErrors: [
    {
      entryIndex: number,
      accountNumber: string,
      issue: string
    }
  ],
  balanceErrors: {
    enteredDebitTotal: number,
    enteredCreditTotal: number,
    enteredDifference: number,
    convertedDebitTotal: number,
    convertedCreditTotal: number,
    convertedDifference: number
  },
  suggestedFixes: [
    {
      entryIndex: number,
      accountNumber: string,
      currentState: string,
      problem: string,
      fix: string,
      moveAmount: number,
      moveFromColumn: string,
      moveToColumn: string,
      type: "entered" | "converted"
    }
  ],
  correctedEntries: [] // The entries with fixes applied
}
```

## Usage Examples

### Example 1: Production Scenario (Unbalanced Entries)

```javascript
const entries = [
  {
    accountNumber: "3020044",
    enteredDebitAmount: 99,
    enteredCreditAmount: 0,
    convertedDebitAmount: 99,
    convertedCreditAmount: 0
  },
  {
    accountNumber: "5000104",
    enteredDebitAmount: 99,  // WRONG! 5-series should be in credit
    enteredCreditAmount: 0,
    convertedDebitAmount: 99,  // WRONG! 5-series should be in credit
    convertedCreditAmount: 0
  }
];

const result = validateAndFixJournalEntries(entries);

// Expected output:
// - Account series error: 5000104 should not have debit amount
// - Balance error: Total Debits = 198, Total Credits = 0, Difference = 198
// - Suggested fix: Move 99 from Debit to Credit for account 5000104
// - After fix: Total Debits = 99 (3020044), Total Credits = 99 (5000104), BALANCED
```

### Example 2: Valid Balanced Entries

```javascript
const entries = [
  {
    accountNumber: "3020044",
    enteredDebitAmount: 99,
    enteredCreditAmount: 0,
    convertedDebitAmount: 99,
    convertedCreditAmount: 0
  },
  {
    accountNumber: "5000104",
    enteredDebitAmount: 0,
    enteredCreditAmount: 99,  // Correct! 5-series in credit
    convertedDebitAmount: 0,
    convertedCreditAmount: 99  // Correct! 5-series in credit
  }
];

const result = validateAndFixJournalEntries(entries);

// Expected output:
// - isValid: true
// - accountSeriesErrors: []
// - No balance errors
// - No fixes needed
```

## How to Run

### In Node.js

```bash
# Run the examples directly
node validateAndFixJournalEntries.js
```

### In Browser

```html
<!DOCTYPE html>
<html>
<head>
  <title>Journal Validation Test</title>
  <script src="validateAndFixJournalEntries.js"></script>
</head>
<body>
  <script>
    const entries = [
      {
        accountNumber: "3020044",
        enteredDebitAmount: 99,
        enteredCreditAmount: 0,
        convertedDebitAmount: 99,
        convertedCreditAmount: 0
      },
      {
        accountNumber: "5000104",
        enteredDebitAmount: 99,
        enteredCreditAmount: 0,
        convertedDebitAmount: 99,
        convertedCreditAmount: 0
      }
    ];

    const result = validateAndFixJournalEntries(entries);
    console.log(result);
  </script>
</body>
</html>
```

### As a Module

```javascript
// Import the function
const { validateAndFixJournalEntries } = require('./validateAndFixJournalEntries.js');

// Use in your code
const entries = [...]; // your journal entries
const result = validateAndFixJournalEntries(entries);

if (!result.isValid) {
  console.log('Errors found:', result.accountSeriesErrors);
  console.log('Suggested fixes:', result.suggestedFixes);
  console.log('Corrected entries:', result.correctedEntries);
}
```

## Validation Process

The function performs validation in 4 steps:

### Step 1: Account Series Validation

- Scans all entries
- Flags any 3-series account with credit amount > 0
- Flags any 5-series account with debit amount > 0
- Returns these as "accountSeriesErrors"

### Step 2: Balance Validation

- Calculates totalDebits = sum of all enteredDebitAmount
- Calculates totalCredits = sum of all enteredCreditAmount
- Calculates totalConvertedDebits = sum of all convertedDebitAmount
- Calculates totalConvertedCredits = sum of all convertedCreditAmount
- Flags as unbalanced if totals don't match

### Step 3: Fix Suggestion Logic

- Identifies the DIFFERENCE between total debits and credits
- Finds the MISPLACED AMOUNT: Looks for an entry where moving its value to the opposite column would balance the totals
- Suggests the exact correction: "Move [AMOUNT] from [WRONG_COLUMN] to [CORRECT_COLUMN] for account [ACCOUNT_NUMBER]"
- Does this for BOTH entered amounts and converted amounts

### Step 4: Apply Fixes

- Creates a copy of the original entries
- Applies all suggested fixes
- Returns the corrected entries
- Verifies that corrected entries are now balanced

## Edge Cases Handled

- ✅ Entries with amounts in BOTH debit and credit columns
- ✅ Multiple entries with the same account number
- ✅ Floating-point precision issues (uses epsilon comparison)
- ✅ Multiple possible fixes (returns all suggestions)
- ✅ Complex imbalances across multiple entries
- ✅ Independent validation for entered and converted amounts

## Output Logging

The function includes comprehensive console logging to trace:

- Validation start and completion
- Each validation step
- Account series errors found
- Balance calculation results
- Fix suggestions generated
- Fixes applied
- Final balance verification

## Testing

The file includes 3 built-in test scenarios:

1. **Production Scenario** - Demonstrates fixing a 5-series account in wrong column
2. **Valid Entries** - Shows validation passing for correct entries
3. **Complex Imbalance** - Multiple entries with mixed errors

Run all tests:

```bash
node validateAndFixJournalEntries.js
```

## Error Handling

The function is production-ready with:

- ✅ Null/undefined checks
- ✅ Safe navigation for missing properties
- ✅ Defensive programming practices
- ✅ Comprehensive error messages
- ✅ Detailed logging for debugging

## Integration with Existing Codebase

This utility can be integrated with the existing Python codebase:

1. **Pre-validation**: Run before generating journal templates
2. **Post-validation**: Validate generated journal entries before export
3. **Debugging**: Use to diagnose why journal entries are failing in Oracle
4. **Testing**: Verify that journal generation logic produces balanced entries

### Example Python Integration

```python
import subprocess
import json

def validate_journal_entries(entries):
    """Validate journal entries using JavaScript utility"""
    # Convert Python entries to JSON
    entries_json = json.dumps(entries)

    # Call Node.js validator
    result = subprocess.run(
        ['node', '-e', f'''
        const {{ validateAndFixJournalEntries }} = require('./validateAndFixJournalEntries.js');
        const entries = {entries_json};
        const result = validateAndFixJournalEntries(entries);
        console.log(JSON.stringify(result));
        '''],
        capture_output=True,
        text=True
    )

    # Parse result
    validation_result = json.loads(result.stdout)
    return validation_result
```

## Benefits

1. **Prevents Oracle Errors** - Catches imbalances before journal import
2. **Automatic Fixes** - Suggests and applies corrections automatically
3. **Clear Diagnostics** - Detailed error messages explain what's wrong
4. **Production Ready** - Comprehensive error handling and logging
5. **Reusable** - Works in Node.js and browsers
6. **Well Documented** - Inline comments explain each step
7. **Testable** - Includes test cases and examples

## License

This utility is part of the Oracle Fusion Financial Integration system and follows the same license as the parent repository.

## Support

For questions or issues, refer to the main repository documentation or create an issue in the GitHub repository.
