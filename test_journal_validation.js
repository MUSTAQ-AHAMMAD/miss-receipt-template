/**
 * ================================================================================
 * COMPREHENSIVE TEST SUITE FOR JOURNAL ENTRY VALIDATION
 * ================================================================================
 *
 * This file contains comprehensive tests for the validateAndFixJournalEntries
 * utility to ensure it handles all edge cases and scenarios correctly.
 *
 * Run: node test_journal_validation.js
 * ================================================================================
 */

const { validateAndFixJournalEntries } = require('./validateAndFixJournalEntries.js');

// Test counters
let totalTests = 0;
let passedTests = 0;
let failedTests = 0;

/**
 * Assert helper function
 */
function assert(condition, testName, details = '') {
  totalTests++;
  if (condition) {
    passedTests++;
    console.log(`  ✅ PASS: ${testName}`);
  } else {
    failedTests++;
    console.log(`  ❌ FAIL: ${testName}`);
    if (details) {
      console.log(`     Details: ${details}`);
    }
  }
}

/**
 * Test Suite 1: Account Series Validation
 */
function testAccountSeriesValidation() {
  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║  TEST SUITE 1: ACCOUNT SERIES VALIDATION                       ║');
  console.log('╚════════════════════════════════════════════════════════════════╝');

  // Test 1.1: 3-series account in credit column (WRONG)
  const test1 = validateAndFixJournalEntries([
    {
      accountNumber: "3020044",
      enteredDebitAmount: 0,
      enteredCreditAmount: 100,  // WRONG! 3-series must be in debit
      convertedDebitAmount: 0,
      convertedCreditAmount: 100
    }
  ]);
  assert(
    !test1.isValid && test1.accountSeriesErrors.length === 1,
    'Test 1.1: Detects 3-series account in credit column',
    `Expected 1 error, got ${test1.accountSeriesErrors.length}`
  );

  // Test 1.2: 5-series account in debit column (WRONG)
  const test2 = validateAndFixJournalEntries([
    {
      accountNumber: "5000104",
      enteredDebitAmount: 100,  // WRONG! 5-series must be in credit
      enteredCreditAmount: 0,
      convertedDebitAmount: 100,
      convertedCreditAmount: 0
    }
  ]);
  assert(
    !test2.isValid && test2.accountSeriesErrors.length === 1,
    'Test 1.2: Detects 5-series account in debit column',
    `Expected 1 error, got ${test2.accountSeriesErrors.length}`
  );

  // Test 1.3: Correct placement (3-series in debit, 5-series in credit)
  const test3 = validateAndFixJournalEntries([
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
      enteredCreditAmount: 100,
      convertedDebitAmount: 0,
      convertedCreditAmount: 100
    }
  ]);
  assert(
    test3.isValid && test3.accountSeriesErrors.length === 0,
    'Test 1.3: Valid when 3-series in debit and 5-series in credit',
    `Expected valid=true, got ${test3.isValid}`
  );

  // Test 1.4: Multiple account series errors
  const test4 = validateAndFixJournalEntries([
    {
      accountNumber: "3020044",
      enteredDebitAmount: 0,
      enteredCreditAmount: 50,  // WRONG
      convertedDebitAmount: 0,
      convertedCreditAmount: 50
    },
    {
      accountNumber: "5000104",
      enteredDebitAmount: 100,  // WRONG
      enteredCreditAmount: 0,
      convertedDebitAmount: 100,
      convertedCreditAmount: 0
    }
  ]);
  assert(
    !test4.isValid && test4.accountSeriesErrors.length === 2,
    'Test 1.4: Detects multiple account series errors',
    `Expected 2 errors, got ${test4.accountSeriesErrors.length}`
  );
}

/**
 * Test Suite 2: Balance Validation
 */
function testBalanceValidation() {
  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║  TEST SUITE 2: BALANCE VALIDATION                              ║');
  console.log('╚════════════════════════════════════════════════════════════════╝');

  // Test 2.1: Perfectly balanced entries
  const test1 = validateAndFixJournalEntries([
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
      enteredCreditAmount: 100,
      convertedDebitAmount: 0,
      convertedCreditAmount: 100
    }
  ]);
  assert(
    test1.isValid &&
    test1.balanceErrors.enteredDifference === 0 &&
    test1.balanceErrors.convertedDifference === 0,
    'Test 2.1: Recognizes perfectly balanced entries',
    `Entered diff: ${test1.balanceErrors.enteredDifference}, Converted diff: ${test1.balanceErrors.convertedDifference}`
  );

  // Test 2.2: Unbalanced - more debits than credits
  const test2 = validateAndFixJournalEntries([
    {
      accountNumber: "3020044",
      enteredDebitAmount: 200,
      enteredCreditAmount: 0,
      convertedDebitAmount: 200,
      convertedCreditAmount: 0
    },
    {
      accountNumber: "5000104",
      enteredDebitAmount: 0,
      enteredCreditAmount: 100,
      convertedDebitAmount: 0,
      convertedCreditAmount: 100
    }
  ]);
  assert(
    !test2.isValid && test2.balanceErrors.enteredDifference === 100,
    'Test 2.2: Detects unbalanced entries (more debits)',
    `Expected diff 100, got ${test2.balanceErrors.enteredDifference}`
  );

  // Test 2.3: Unbalanced - more credits than debits
  const test3 = validateAndFixJournalEntries([
    {
      accountNumber: "3020044",
      enteredDebitAmount: 50,
      enteredCreditAmount: 0,
      convertedDebitAmount: 50,
      convertedCreditAmount: 0
    },
    {
      accountNumber: "5000104",
      enteredDebitAmount: 0,
      enteredCreditAmount: 150,
      convertedDebitAmount: 0,
      convertedCreditAmount: 150
    }
  ]);
  assert(
    !test3.isValid && test3.balanceErrors.enteredDifference === -100,
    'Test 2.3: Detects unbalanced entries (more credits)',
    `Expected diff -100, got ${test3.balanceErrors.enteredDifference}`
  );

  // Test 2.4: Multiple entries that balance
  const test4 = validateAndFixJournalEntries([
    {
      accountNumber: "3020044",
      enteredDebitAmount: 100,
      enteredCreditAmount: 0,
      convertedDebitAmount: 100,
      convertedCreditAmount: 0
    },
    {
      accountNumber: "3020044",
      enteredDebitAmount: 50,
      enteredCreditAmount: 0,
      convertedDebitAmount: 50,
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
      enteredDebitAmount: 0,
      enteredCreditAmount: 75,
      convertedDebitAmount: 0,
      convertedCreditAmount: 75
    }
  ]);
  assert(
    test4.isValid && test4.balanceErrors.enteredDifference === 0,
    'Test 2.4: Multiple entries that balance correctly',
    `Expected balanced, got diff ${test4.balanceErrors.enteredDifference}`
  );
}

/**
 * Test Suite 3: Fix Suggestion Logic
 */
function testFixSuggestionLogic() {
  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║  TEST SUITE 3: FIX SUGGESTION LOGIC                            ║');
  console.log('╚════════════════════════════════════════════════════════════════╝');

  // Test 3.1: Production scenario - suggests correct fix
  const test1 = validateAndFixJournalEntries([
    {
      accountNumber: "3020044",
      enteredDebitAmount: 99,
      enteredCreditAmount: 0,
      convertedDebitAmount: 99,
      convertedCreditAmount: 0
    },
    {
      accountNumber: "5000104",
      enteredDebitAmount: 99,  // WRONG
      enteredCreditAmount: 0,
      convertedDebitAmount: 99,
      convertedCreditAmount: 0
    }
  ]);
  assert(
    test1.suggestedFixes.length > 0,
    'Test 3.1: Generates fix suggestions for production scenario',
    `Expected fixes > 0, got ${test1.suggestedFixes.length}`
  );

  // Test 3.2: No fixes needed for balanced entries
  const test2 = validateAndFixJournalEntries([
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
      enteredCreditAmount: 100,
      convertedDebitAmount: 0,
      convertedCreditAmount: 100
    }
  ]);
  assert(
    test2.suggestedFixes.length === 0,
    'Test 3.2: No fixes suggested for balanced entries',
    `Expected 0 fixes, got ${test2.suggestedFixes.length}`
  );

  // Test 3.3: Partial fixes for complex imbalance
  const test3 = validateAndFixJournalEntries([
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
      accountNumber: "5000104",
      enteredDebitAmount: 50,  // WRONG - causes partial imbalance
      enteredCreditAmount: 0,
      convertedDebitAmount: 50,
      convertedCreditAmount: 0
    }
  ]);
  assert(
    test3.suggestedFixes.length > 0,
    'Test 3.3: Suggests partial fixes for complex imbalance',
    `Expected fixes > 0, got ${test3.suggestedFixes.length}`
  );
}

/**
 * Test Suite 4: Corrected Entries
 */
function testCorrectedEntries() {
  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║  TEST SUITE 4: CORRECTED ENTRIES                               ║');
  console.log('╚════════════════════════════════════════════════════════════════╝');

  // Test 4.1: Production scenario - corrected entries are balanced
  const test1 = validateAndFixJournalEntries([
    {
      accountNumber: "3020044",
      enteredDebitAmount: 99,
      enteredCreditAmount: 0,
      convertedDebitAmount: 99,
      convertedCreditAmount: 0
    },
    {
      accountNumber: "5000104",
      enteredDebitAmount: 99,  // WRONG
      enteredCreditAmount: 0,
      convertedDebitAmount: 99,
      convertedCreditAmount: 0
    }
  ]);

  // Calculate balance of corrected entries
  let correctedDebitTotal = 0;
  let correctedCreditTotal = 0;
  test1.correctedEntries.forEach(entry => {
    correctedDebitTotal += entry.enteredDebitAmount || 0;
    correctedCreditTotal += entry.enteredCreditAmount || 0;
  });

  assert(
    Math.abs(correctedDebitTotal - correctedCreditTotal) < 0.01,
    'Test 4.1: Corrected entries are balanced',
    `Debit: ${correctedDebitTotal}, Credit: ${correctedCreditTotal}, Diff: ${correctedDebitTotal - correctedCreditTotal}`
  );

  // Test 4.2: Corrected entries fix account series errors
  assert(
    test1.correctedEntries[1].enteredCreditAmount === 99 &&
    test1.correctedEntries[1].enteredDebitAmount === 0,
    'Test 4.2: Corrected entries fix 5-series account placement',
    `Entry[1] Debit: ${test1.correctedEntries[1].enteredDebitAmount}, Credit: ${test1.correctedEntries[1].enteredCreditAmount}`
  );

  // Test 4.3: Original entries are not modified
  const originalEntries = [
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
  const test3 = validateAndFixJournalEntries(originalEntries);

  assert(
    originalEntries[1].enteredDebitAmount === 99,
    'Test 4.3: Original entries are not modified',
    `Original entry[1] debit should still be 99, got ${originalEntries[1].enteredDebitAmount}`
  );
}

/**
 * Test Suite 5: Edge Cases
 */
function testEdgeCases() {
  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║  TEST SUITE 5: EDGE CASES                                      ║');
  console.log('╚════════════════════════════════════════════════════════════════╝');

  // Test 5.1: Empty entries array
  const test1 = validateAndFixJournalEntries([]);
  assert(
    test1.isValid,
    'Test 5.1: Handles empty entries array',
    `Expected valid=true for empty array, got ${test1.isValid}`
  );

  // Test 5.2: Single entry
  const test2 = validateAndFixJournalEntries([
    {
      accountNumber: "3020044",
      enteredDebitAmount: 100,
      enteredCreditAmount: 0,
      convertedDebitAmount: 100,
      convertedCreditAmount: 0
    }
  ]);
  assert(
    !test2.isValid && test2.balanceErrors.enteredDifference === 100,
    'Test 5.2: Handles single unbalanced entry',
    `Expected unbalanced, got diff ${test2.balanceErrors.enteredDifference}`
  );

  // Test 5.3: Entry with amounts in both columns
  const test3 = validateAndFixJournalEntries([
    {
      accountNumber: "3020044",
      enteredDebitAmount: 100,
      enteredCreditAmount: 50,  // Has both debit and credit
      convertedDebitAmount: 100,
      convertedCreditAmount: 50
    }
  ]);
  assert(
    !test3.isValid && test3.accountSeriesErrors.length === 1,
    'Test 5.3: Detects 3-series with credit even when it has debit too',
    `Expected 1 account error, got ${test3.accountSeriesErrors.length}`
  );

  // Test 5.4: Zero amounts
  const test4 = validateAndFixJournalEntries([
    {
      accountNumber: "3020044",
      enteredDebitAmount: 0,
      enteredCreditAmount: 0,
      convertedDebitAmount: 0,
      convertedCreditAmount: 0
    },
    {
      accountNumber: "5000104",
      enteredDebitAmount: 0,
      enteredCreditAmount: 0,
      convertedDebitAmount: 0,
      convertedCreditAmount: 0
    }
  ]);
  assert(
    test4.isValid,
    'Test 5.4: Handles zero amounts as balanced',
    `Expected valid=true, got ${test4.isValid}`
  );

  // Test 5.5: Floating point amounts
  const test5 = validateAndFixJournalEntries([
    {
      accountNumber: "3020044",
      enteredDebitAmount: 99.99,
      enteredCreditAmount: 0,
      convertedDebitAmount: 99.99,
      convertedCreditAmount: 0
    },
    {
      accountNumber: "5000104",
      enteredDebitAmount: 0,
      enteredCreditAmount: 99.99,
      convertedDebitAmount: 0,
      convertedCreditAmount: 99.99
    }
  ]);
  assert(
    test5.isValid && Math.abs(test5.balanceErrors.enteredDifference) < 0.01,
    'Test 5.5: Handles floating point amounts correctly',
    `Expected balanced, got diff ${test5.balanceErrors.enteredDifference}`
  );

  // Test 5.6: Large numbers
  const test6 = validateAndFixJournalEntries([
    {
      accountNumber: "3020044",
      enteredDebitAmount: 1000000,
      enteredCreditAmount: 0,
      convertedDebitAmount: 1000000,
      convertedCreditAmount: 0
    },
    {
      accountNumber: "5000104",
      enteredDebitAmount: 0,
      enteredCreditAmount: 1000000,
      convertedDebitAmount: 0,
      convertedCreditAmount: 1000000
    }
  ]);
  assert(
    test6.isValid,
    'Test 5.6: Handles large numbers correctly',
    `Expected valid=true, got ${test6.isValid}`
  );
}

/**
 * Test Suite 6: Independent Entered and Converted Validation
 */
function testIndependentValidation() {
  console.log('\n╔════════════════════════════════════════════════════════════════╗');
  console.log('║  TEST SUITE 6: INDEPENDENT ENTERED/CONVERTED VALIDATION        ║');
  console.log('╚════════════════════════════════════════════════════════════════╝');

  // Test 6.1: Entered balanced, converted unbalanced
  const test1 = validateAndFixJournalEntries([
    {
      accountNumber: "3020044",
      enteredDebitAmount: 100,
      enteredCreditAmount: 0,
      convertedDebitAmount: 150,  // Different converted amount
      convertedCreditAmount: 0
    },
    {
      accountNumber: "5000104",
      enteredDebitAmount: 0,
      enteredCreditAmount: 100,
      convertedDebitAmount: 0,
      convertedCreditAmount: 100  // Unbalanced converted
    }
  ]);
  assert(
    !test1.isValid &&
    test1.balanceErrors.enteredDifference === 0 &&
    test1.balanceErrors.convertedDifference === 50,
    'Test 6.1: Detects when entered is balanced but converted is not',
    `Entered diff: ${test1.balanceErrors.enteredDifference}, Converted diff: ${test1.balanceErrors.convertedDifference}`
  );

  // Test 6.2: Entered unbalanced, converted balanced
  const test2 = validateAndFixJournalEntries([
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
      enteredCreditAmount: 75,  // Unbalanced entered
      convertedDebitAmount: 0,
      convertedCreditAmount: 100  // Balanced converted
    }
  ]);
  assert(
    !test2.isValid &&
    test2.balanceErrors.enteredDifference === 25 &&
    test2.balanceErrors.convertedDifference === 0,
    'Test 6.2: Detects when converted is balanced but entered is not',
    `Entered diff: ${test2.balanceErrors.enteredDifference}, Converted diff: ${test2.balanceErrors.convertedDifference}`
  );
}

/**
 * Run all tests
 */
function runAllTests() {
  console.log('\n' + '='.repeat(70));
  console.log('  JOURNAL ENTRY VALIDATION - COMPREHENSIVE TEST SUITE');
  console.log('='.repeat(70));

  testAccountSeriesValidation();
  testBalanceValidation();
  testFixSuggestionLogic();
  testCorrectedEntries();
  testEdgeCases();
  testIndependentValidation();

  console.log('\n' + '='.repeat(70));
  console.log('  TEST RESULTS SUMMARY');
  console.log('='.repeat(70));
  console.log(`  Total Tests:  ${totalTests}`);
  console.log(`  Passed:       ${passedTests} ✅`);
  console.log(`  Failed:       ${failedTests} ❌`);
  console.log(`  Success Rate: ${((passedTests / totalTests) * 100).toFixed(1)}%`);
  console.log('='.repeat(70) + '\n');

  if (failedTests === 0) {
    console.log('🎉 ALL TESTS PASSED! 🎉\n');
    process.exit(0);
  } else {
    console.log('⚠️  SOME TESTS FAILED ⚠️\n');
    process.exit(1);
  }
}

// Run the test suite
runAllTests();
