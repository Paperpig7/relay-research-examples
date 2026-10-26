import assert from 'node:assert/strict';
import test from 'node:test';
import { isAsciiDigitString, jsonCases, runRegression } from '../examples/json_amount_gate.mjs';

for (const [name, value, expected] of jsonCases()) {
  test(`decoded JSON: ${name}`, () => {
    const wire = JSON.stringify({ x402Version: 2, accepts: [{ amount: value }] });
    const decoded = JSON.parse(wire).accepts[0].amount;
    assert.equal(isAsciiDigitString(decoded), expected);
    assert.deepEqual(decoded, value, 'JSON preserves this fixture value');
  });
}

test('the 34-case regression identifies the five coercion counterexamples', () => {
  const report = runRegression();
  assert.equal(report.total, 34);
  assert.equal(report.passed, 34);
  assert.equal(new Set(report.results.map(row => row.name)).size, 34);
  assert.deepEqual(report.regex_only_false_accepts, [
    'numeric-zero', 'numeric-positive', 'single-number-array',
    'single-string-array', 'nested-number-array',
  ]);
});

test('a missing property fails without conversion', () => {
  assert.equal(isAsciiDigitString(JSON.parse('{}').amount), false);
});

test('the reusable predicate never invokes object coercion hooks', () => {
  const object = { [Symbol.toPrimitive]() { throw new Error('must not coerce'); } };
  assert.equal(isAsciiDigitString(object), false);
  assert.equal(isAsciiDigitString(new String('5000')), false);
});

test('passing is lexical only and preserves representations', () => {
  const values = ['0005', '9007199254740993', '9'.repeat(1000)];
  for (const value of values) {
    assert.equal(isAsciiDigitString(value), true);
    assert.equal(value, JSON.parse(JSON.stringify(value)));
  }
  assert.notEqual(values[0], '5');
  assert.notEqual(String(Number(values[1])), values[1], 'Number conversion would lose this integer');
});
