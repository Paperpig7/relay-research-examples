import assert from 'node:assert/strict';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

// A lexical predicate only: no coercion, normalization, range, or payment checks.
export function isAsciiDigitString(value) {
  return typeof value === 'string' && value.length > 0 && !/[^0-9]/.test(value);
}

// Deliberately inadequate comparator, retained to reproduce the type confusion.
export function regexOnlyGate(value) {
  return /^[0-9]+$/.test(value);
}

export function jsonCases() {
  return [
    ['zero-string', '0', true],
    ['ordinary-string', '5000', true],
    ['large-integer-string', '9007199254740993', true],
    ['1000-digit-string', '9'.repeat(1000), true],
    ['leading-zero-string', '0005', true],
    ['numeric-zero', 0, false],
    ['numeric-positive', 5000, false],
    ['numeric-negative', -5, false],
    ['numeric-fraction', 0.005, false],
    ['single-number-array', [5000], false],
    ['single-string-array', ['5000'], false],
    ['nested-number-array', [[5000]], false],
    ['empty-array', [], false],
    ['multiple-number-array', [5, 0], false],
    ['null', null, false],
    ['true', true, false],
    ['false', false, false],
    ['empty-object', {}, false],
    ['amount-shaped-object', { amount: '5000' }, false],
    ['empty-string', '', false],
    ['leading-space', ' 5000', false],
    ['trailing-space', '5000 ', false],
    ['trailing-tab', '5000\t', false],
    ['trailing-LF', '5000\n', false],
    ['trailing-CR', '5000\r', false],
    ['trailing-CRLF', '5000\r\n', false],
    ['trailing-Unicode-line-separator', '5000\u2028', false],
    ['trailing-NBSP', '5000\u00a0', false],
    ['plus-sign', '+5000', false],
    ['fraction-string', '0.005', false],
    ['exponent-string', '5e3', false],
    ['full-width-digits', '５０００', false],
    ['embedded-line-feed', '50\n00', false],
    ['hex-string', '0x1388', false],
  ];
}

export function runRegression() {
  const results = jsonCases().map(([name, value, expected]) => {
    // Synthetic wrapper, not a complete or valid x402 payment requirement.
    const wire = JSON.stringify({ x402Version: 2, accepts: [{ amount: value }] });
    const decoded = JSON.parse(wire).accepts[0].amount;
    const actual = isAsciiDigitString(decoded);
    assert.equal(actual, expected, name);
    if (typeof value === 'string') assert.equal(decoded, value, `${name}: unchanged string`);
    return { name, expected, actual, regexOnly: regexOnlyGate(decoded) };
  });
  return {
    total: results.length,
    passed: results.filter(row => row.actual === row.expected).length,
    regex_only_false_accepts: results.filter(row => !row.expected && row.regexOnly).map(row => row.name),
    results,
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const { total, passed, regex_only_false_accepts } = runRegression();
  console.log(JSON.stringify({ total, passed, regex_only_false_accepts }, null, 2));
}
