/**
 * ================================================================================
 * JOURNAL ENTRY VALIDATION AND FIX UTILITY
 * ================================================================================
 *
 * This module provides comprehensive validation and automatic fixing for
 * unbalanced journal entries based on strict accounting system rules.
 *
 * SYSTEM RULES:
 * 1. Account Series Validation:
 *    - 3-series accounts (e.g., 3020044) MUST be in Debit column
 *    - 5-series accounts (e.g., 5000104) MUST be in Credit column
 *
 * 2. Balance Validation:
 *    - Sum of Entered Debits MUST equal Sum of Entered Credits
 *    - Sum of Converted Debits MUST equal Sum of Converted Credits
 *
 * 3. Fix Logic:
 *    - Find misplaced amounts and suggest moving them to correct column
 *    - Provide corrected entries with fixes applied
 *
 * @module validateAndFixJournalEntries
 * @version 1.0.0
 * ================================================================================
 */

/**
 * Validates and fixes unbalanced journal entries
 *
 * @param {Array<Object>} entries - Array of journal entry objects
 * @param {string} entries[].accountNumber - Account number (e.g., "3020044")
 * @param {number} entries[].enteredDebitAmount - Entered debit amount
 * @param {number} entries[].enteredCreditAmount - Entered credit amount
 * @param {number} entries[].convertedDebitAmount - Converted debit amount
 * @param {number} entries[].convertedCreditAmount - Converted credit amount
 *
 * @returns {Object} Validation result with fixes
 */
function validateAndFixJournalEntries(entries) {
  console.log('\n=== JOURNAL ENTRY VALIDATION STARTED ===');
  console.log(`Total entries to validate: ${entries.length}`);

  // Initialize result structure
  const result = {
    isValid: true,
    accountSeriesErrors: [],
    balanceErrors: {
      enteredDebitTotal: 0,
      enteredCreditTotal: 0,
      enteredDifference: 0,
      convertedDebitTotal: 0,
      convertedCreditTotal: 0,
      convertedDifference: 0
    },
    suggestedFixes: [],
    correctedEntries: []
  };

  // ============================================================================
  // STEP 1: ACCOUNT SERIES VALIDATION
  // ============================================================================
  console.log('\n--- Step 1: Validating Account Series Rules ---');

  entries.forEach((entry, index) => {
    const accountNumber = entry.accountNumber || '';
    const firstDigit = accountNumber.charAt(0);

    // Check 3-series accounts (must be in debit column)
    if (firstDigit === '3' && entry.enteredCreditAmount > 0) {
      const error = {
        entryIndex: index,
        accountNumber: accountNumber,
        issue: `3-series account ${accountNumber} has credit amount ${entry.enteredCreditAmount} but must only have debit amounts`
      };
      result.accountSeriesErrors.push(error);
      result.isValid = false;
      console.log(`  ❌ ERROR at index ${index}: ${error.issue}`);
    }

    // Check 5-series accounts (must be in credit column)
    if (firstDigit === '5' && entry.enteredDebitAmount > 0) {
      const error = {
        entryIndex: index,
        accountNumber: accountNumber,
        issue: `5-series account ${accountNumber} has debit amount ${entry.enteredDebitAmount} but must only have credit amounts`
      };
      result.accountSeriesErrors.push(error);
      result.isValid = false;
      console.log(`  ❌ ERROR at index ${index}: ${error.issue}`);
    }
  });

  if (result.accountSeriesErrors.length === 0) {
    console.log('  ✓ All account series validations passed');
  } else {
    console.log(`  ✗ Found ${result.accountSeriesErrors.length} account series errors`);
  }

  // ============================================================================
  // STEP 2: BALANCE VALIDATION
  // ============================================================================
  console.log('\n--- Step 2: Validating Balance Requirements ---');

  // Calculate totals for entered amounts
  entries.forEach(entry => {
    result.balanceErrors.enteredDebitTotal += entry.enteredDebitAmount || 0;
    result.balanceErrors.enteredCreditTotal += entry.enteredCreditAmount || 0;
    result.balanceErrors.convertedDebitTotal += entry.convertedDebitAmount || 0;
    result.balanceErrors.convertedCreditTotal += entry.convertedCreditAmount || 0;
  });

  // Calculate differences
  result.balanceErrors.enteredDifference =
    result.balanceErrors.enteredDebitTotal - result.balanceErrors.enteredCreditTotal;
  result.balanceErrors.convertedDifference =
    result.balanceErrors.convertedDebitTotal - result.balanceErrors.convertedCreditTotal;

  // Log balance status
  console.log(`  Entered Debits Total:  ${result.balanceErrors.enteredDebitTotal.toFixed(2)}`);
  console.log(`  Entered Credits Total: ${result.balanceErrors.enteredCreditTotal.toFixed(2)}`);
  console.log(`  Entered Difference:    ${result.balanceErrors.enteredDifference.toFixed(2)}`);
  console.log(`  Converted Debits Total:  ${result.balanceErrors.convertedDebitTotal.toFixed(2)}`);
  console.log(`  Converted Credits Total: ${result.balanceErrors.convertedCreditTotal.toFixed(2)}`);
  console.log(`  Converted Difference:    ${result.balanceErrors.convertedDifference.toFixed(2)}`);

  // Check if balanced (using small epsilon for floating point comparison)
  const epsilon = 0.01;
  const enteredBalanced = Math.abs(result.balanceErrors.enteredDifference) < epsilon;
  const convertedBalanced = Math.abs(result.balanceErrors.convertedDifference) < epsilon;

  if (!enteredBalanced || !convertedBalanced) {
    result.isValid = false;
    console.log('  ❌ Journal entries are UNBALANCED');
  } else {
    console.log('  ✓ Journal entries are BALANCED');
  }

  // ============================================================================
  // STEP 3: FIX SUGGESTION LOGIC
  // ============================================================================
  console.log('\n--- Step 3: Generating Fix Suggestions ---');

  // Function to find potential fixes for a given difference and amount type
  function findFixesForType(entries, difference, amountType) {
    const fixes = [];
    const isEntered = amountType === 'entered';

    // If difference is positive, we have more debits than credits
    // Need to move amount from debit to credit
    // If difference is negative, we have more credits than debits
    // Need to move amount from credit to debit

    const moveFromColumn = difference > 0 ? 'Debit' : 'Credit';
    const moveToColumn = difference > 0 ? 'Credit' : 'Debit';
    const targetAmount = Math.abs(difference);

    console.log(`  Searching for ${amountType} fixes: need to move ${targetAmount.toFixed(2)} from ${moveFromColumn} to ${moveToColumn}`);

    entries.forEach((entry, index) => {
      const debitAmount = isEntered ? entry.enteredDebitAmount : entry.convertedDebitAmount;
      const creditAmount = isEntered ? entry.enteredCreditAmount : entry.convertedCreditAmount;

      // Check if moving this entry's debit amount to credit would fix or partially fix the balance
      if (difference > 0 && debitAmount > 0) {
        // Check if this exact amount would balance
        if (Math.abs(debitAmount - targetAmount) < epsilon) {
          const fix = {
            entryIndex: index,
            accountNumber: entry.accountNumber,
            currentState: `${entry.accountNumber} has ${debitAmount} in ${moveFromColumn} column`,
            problem: `This amount should be in ${moveToColumn} column to balance the journal`,
            fix: `Move ${debitAmount} from ${moveFromColumn} to ${moveToColumn} for account ${entry.accountNumber}`,
            moveAmount: debitAmount,
            moveFromColumn: moveFromColumn,
            moveToColumn: moveToColumn,
            type: amountType
          };
          fixes.push(fix);
          console.log(`    ✓ Found potential fix at index ${index}: ${fix.fix}`);
        }
        // Check if this amount is a divisor of the target (multiple entries may need fixing)
        else if (targetAmount % debitAmount < epsilon && debitAmount > 0) {
          const fix = {
            entryIndex: index,
            accountNumber: entry.accountNumber,
            currentState: `${entry.accountNumber} has ${debitAmount} in ${moveFromColumn} column`,
            problem: `This amount should be in ${moveToColumn} column to partially balance the journal`,
            fix: `Move ${debitAmount} from ${moveFromColumn} to ${moveToColumn} for account ${entry.accountNumber} (partial fix)`,
            moveAmount: debitAmount,
            moveFromColumn: moveFromColumn,
            moveToColumn: moveToColumn,
            type: amountType
          };
          fixes.push(fix);
          console.log(`    ✓ Found potential partial fix at index ${index}: ${fix.fix}`);
        }
      }

      // Check if moving this entry's credit amount to debit would fix or partially fix the balance
      if (difference < 0 && creditAmount > 0) {
        // Check if this exact amount would balance
        if (Math.abs(creditAmount - targetAmount) < epsilon) {
          const fix = {
            entryIndex: index,
            accountNumber: entry.accountNumber,
            currentState: `${entry.accountNumber} has ${creditAmount} in ${moveFromColumn} column`,
            problem: `This amount should be in ${moveToColumn} column to balance the journal`,
            fix: `Move ${creditAmount} from ${moveFromColumn} to ${moveToColumn} for account ${entry.accountNumber}`,
            moveAmount: creditAmount,
            moveFromColumn: moveFromColumn,
            moveToColumn: moveToColumn,
            type: amountType
          };
          fixes.push(fix);
          console.log(`    ✓ Found potential fix at index ${index}: ${fix.fix}`);
        }
        // Check if this amount is a divisor of the target (multiple entries may need fixing)
        else if (targetAmount % creditAmount < epsilon && creditAmount > 0) {
          const fix = {
            entryIndex: index,
            accountNumber: entry.accountNumber,
            currentState: `${entry.accountNumber} has ${creditAmount} in ${moveFromColumn} column`,
            problem: `This amount should be in ${moveToColumn} column to partially balance the journal`,
            fix: `Move ${creditAmount} from ${moveFromColumn} to ${moveToColumn} for account ${entry.accountNumber} (partial fix)`,
            moveAmount: creditAmount,
            moveFromColumn: moveFromColumn,
            moveToColumn: moveToColumn,
            type: amountType
          };
          fixes.push(fix);
          console.log(`    ✓ Found potential partial fix at index ${index}: ${fix.fix}`);
        }
      }
    });

    return fixes;
  }

  // Find fixes for entered amounts if unbalanced
  if (!enteredBalanced) {
    const enteredFixes = findFixesForType(entries, result.balanceErrors.enteredDifference, 'entered');
    result.suggestedFixes.push(...enteredFixes);
  }

  // Find fixes for converted amounts if unbalanced
  if (!convertedBalanced) {
    const convertedFixes = findFixesForType(entries, result.balanceErrors.convertedDifference, 'converted');
    result.suggestedFixes.push(...convertedFixes);
  }

  if (result.suggestedFixes.length === 0 && !result.isValid) {
    console.log('  ⚠ No simple single-entry fixes found. The imbalance may be across multiple entries.');
  } else if (result.suggestedFixes.length > 0) {
    console.log(`  ✓ Generated ${result.suggestedFixes.length} fix suggestion(s)`);
  }

  // ============================================================================
  // STEP 4: APPLY FIXES TO CREATE CORRECTED ENTRIES
  // ============================================================================
  console.log('\n--- Step 4: Applying Fixes to Generate Corrected Entries ---');

  // Deep copy entries
  result.correctedEntries = JSON.parse(JSON.stringify(entries));

  // Strategy: Prioritize fixing account series errors first
  // Only fix entries that violate account series rules
  // This ensures we don't over-correct

  // Group fixes by entry index
  const fixesByIndex = {};
  result.suggestedFixes.forEach(fix => {
    if (!fixesByIndex[fix.entryIndex]) {
      fixesByIndex[fix.entryIndex] = [];
    }
    fixesByIndex[fix.entryIndex].push(fix);
  });

  // Prioritize fixing entries with account series errors
  const accountErrorIndices = new Set(
    result.accountSeriesErrors.map(err => err.entryIndex)
  );

  // Apply fixes only to entries with account series errors first
  accountErrorIndices.forEach(index => {
    if (fixesByIndex[index]) {
      const entryFixes = fixesByIndex[index];
      entryFixes.forEach(fix => {
        const entry = result.correctedEntries[index];

        if (fix.type === 'entered') {
          if (fix.moveFromColumn === 'Debit' && fix.moveToColumn === 'Credit') {
            // Move from debit to credit
            entry.enteredCreditAmount = entry.enteredDebitAmount;
            entry.enteredDebitAmount = 0;
            console.log(`  ✓ Applied fix at index ${index}: Moved ${fix.moveAmount} from Entered Debit to Entered Credit (fixes account series error)`);
          } else if (fix.moveFromColumn === 'Credit' && fix.moveToColumn === 'Debit') {
            // Move from credit to debit
            entry.enteredDebitAmount = entry.enteredCreditAmount;
            entry.enteredCreditAmount = 0;
            console.log(`  ✓ Applied fix at index ${index}: Moved ${fix.moveAmount} from Entered Credit to Entered Debit (fixes account series error)`);
          }
        }

        if (fix.type === 'converted') {
          if (fix.moveFromColumn === 'Debit' && fix.moveToColumn === 'Credit') {
            // Move from debit to credit
            entry.convertedCreditAmount = entry.convertedDebitAmount;
            entry.convertedDebitAmount = 0;
            console.log(`  ✓ Applied fix at index ${index}: Moved ${fix.moveAmount} from Converted Debit to Converted Credit (fixes account series error)`);
          } else if (fix.moveFromColumn === 'Credit' && fix.moveToColumn === 'Debit') {
            // Move from credit to debit
            entry.convertedDebitAmount = entry.convertedCreditAmount;
            entry.convertedCreditAmount = 0;
            console.log(`  ✓ Applied fix at index ${index}: Moved ${fix.moveAmount} from Converted Credit to Converted Debit (fixes account series error)`);
          }
        }
      });
    }
  });

  // Verify corrected entries are now balanced
  if (result.correctedEntries.length > 0) {
    let correctedEnteredDebitTotal = 0;
    let correctedEnteredCreditTotal = 0;
    let correctedConvertedDebitTotal = 0;
    let correctedConvertedCreditTotal = 0;

    result.correctedEntries.forEach(entry => {
      correctedEnteredDebitTotal += entry.enteredDebitAmount || 0;
      correctedEnteredCreditTotal += entry.enteredCreditAmount || 0;
      correctedConvertedDebitTotal += entry.convertedDebitAmount || 0;
      correctedConvertedCreditTotal += entry.convertedCreditAmount || 0;
    });

    const correctedEnteredDiff = correctedEnteredDebitTotal - correctedEnteredCreditTotal;
    const correctedConvertedDiff = correctedConvertedDebitTotal - correctedConvertedCreditTotal;

    console.log('\n  Corrected Entries Balance Check:');
    console.log(`    Entered Debits:  ${correctedEnteredDebitTotal.toFixed(2)}`);
    console.log(`    Entered Credits: ${correctedEnteredCreditTotal.toFixed(2)}`);
    console.log(`    Difference:      ${correctedEnteredDiff.toFixed(2)}`);
    console.log(`    Converted Debits:  ${correctedConvertedDebitTotal.toFixed(2)}`);
    console.log(`    Converted Credits: ${correctedConvertedCreditTotal.toFixed(2)}`);
    console.log(`    Difference:        ${correctedConvertedDiff.toFixed(2)}`);

    if (Math.abs(correctedEnteredDiff) < epsilon && Math.abs(correctedConvertedDiff) < epsilon) {
      console.log('  ✓ Corrected entries are now BALANCED!');
    } else {
      console.log('  ⚠ Corrected entries are still unbalanced. Additional fixes may be needed.');
    }
  }

  // ============================================================================
  // FINAL SUMMARY
  // ============================================================================
  console.log('\n=== VALIDATION SUMMARY ===');
  console.log(`Status: ${result.isValid ? '✓ VALID' : '✗ INVALID'}`);
  console.log(`Account Series Errors: ${result.accountSeriesErrors.length}`);
  console.log(`Balance Errors: ${(!enteredBalanced || !convertedBalanced) ? 'YES' : 'NO'}`);
  console.log(`Suggested Fixes: ${result.suggestedFixes.length}`);
  console.log('=== VALIDATION COMPLETED ===\n');

  return result;
}

// ============================================================================
// EXAMPLE USAGE AND TEST CASES
// ============================================================================

/**
 * Example 1: Production scenario from problem statement
 */
function exampleProductionScenario() {
  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║           EXAMPLE 1: PRODUCTION SCENARIO                       ║');
  console.log('╚════════════════════════════════════════════════════════════════╝');

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

  console.log('\n📊 RESULT SUMMARY:');
  console.log(JSON.stringify(result, null, 2));

  return result;
}

/**
 * Example 2: Valid balanced entries
 */
function exampleValidEntries() {
  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║           EXAMPLE 2: VALID BALANCED ENTRIES                    ║');
  console.log('╚════════════════════════════════════════════════════════════════╝');

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

  console.log('\n📊 RESULT SUMMARY:');
  console.log(`Valid: ${result.isValid}`);
  console.log(`Errors: ${result.accountSeriesErrors.length + (result.suggestedFixes.length > 0 ? 1 : 0)}`);

  return result;
}

/**
 * Example 3: Multiple entries with complex imbalance
 */
function exampleComplexImbalance() {
  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║           EXAMPLE 3: COMPLEX IMBALANCE                         ║');
  console.log('╚════════════════════════════════════════════════════════════════╝');

  const entries = [
    {
      accountNumber: "3020044",
      enteredDebitAmount: 100,
      enteredCreditAmount: 0,
      convertedDebitAmount: 100,
      convertedCreditAmount: 0
    },
    {
      accountNumber: "5000104",
      enteredDebitAmount: 0,
      enteredCreditAmount: 50,
      convertedDebitAmount: 0,
      convertedCreditAmount: 50
    },
    {
      accountNumber: "3020044",
      enteredDebitAmount: 75,
      enteredCreditAmount: 0,
      convertedDebitAmount: 75,
      convertedCreditAmount: 0
    },
    {
      accountNumber: "5000104",
      enteredDebitAmount: 0,
      enteredCreditAmount: 75,
      convertedDebitAmount: 0,
      convertedCreditAmount: 75
    },
    {
      accountNumber: "5000104",
      enteredDebitAmount: 50,  // WRONG! Should be in credit
      enteredCreditAmount: 0,
      convertedDebitAmount: 50,  // WRONG! Should be in credit
      convertedCreditAmount: 0
    }
  ];

  const result = validateAndFixJournalEntries(entries);

  console.log('\n📊 RESULT SUMMARY:');
  console.log(`Valid: ${result.isValid}`);
  console.log(`Account Series Errors: ${result.accountSeriesErrors.length}`);
  console.log(`Suggested Fixes: ${result.suggestedFixes.length}`);

  return result;
}

// ============================================================================
// EXPORT FOR USE IN OTHER MODULES
// ============================================================================

// For Node.js
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    validateAndFixJournalEntries,
    exampleProductionScenario,
    exampleValidEntries,
    exampleComplexImbalance
  };
}

// For browsers
if (typeof window !== 'undefined') {
  window.validateAndFixJournalEntries = validateAndFixJournalEntries;
  window.journalValidationExamples = {
    exampleProductionScenario,
    exampleValidEntries,
    exampleComplexImbalance
  };
}

// ============================================================================
// RUN EXAMPLES IF EXECUTED DIRECTLY
// ============================================================================

// Check if this script is being run directly (not imported)
if (typeof require !== 'undefined' && require.main === module) {
  console.log('\n' + '='.repeat(70));
  console.log('  JOURNAL ENTRY VALIDATION AND FIX UTILITY - TEST SUITE');
  console.log('='.repeat(70));

  // Run all examples
  exampleProductionScenario();
  exampleValidEntries();
  exampleComplexImbalance();

  console.log('\n' + '='.repeat(70));
  console.log('  ALL TESTS COMPLETED');
  console.log('='.repeat(70) + '\n');
}
