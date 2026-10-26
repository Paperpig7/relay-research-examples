# Why a JavaScript digits regex is not a JSON string validator

Suppose an API field must be a nonempty string containing only ASCII digits. `"5000"` fits that rule; `5000`, `[5000]`, `["5000"]`, and `[[5000]]` do not. Nevertheless, JavaScript's `/^[0-9]+$/.test(value)` accepts all five.

This happens because [`RegExp.prototype.test`](https://tc39.es/ecma262/multipage/text-processing.html#sec-regexp.prototype.test) converts its input to a string. Normal [array string conversion](https://tc39.es/ecma262/multipage/indexed-collections.html#sec-array.prototype.tostring) uses the array's `join` method. Matching the resulting characters does not validate the original JSON type.

## Declare the lexical contract

```javascript
function isAsciiDigitString(value) {
  return typeof value === 'string' &&
    value.length > 0 &&
    !/[^0-9]/.test(value);
}

isAsciiDigitString('5000');  // true
isAsciiDigitString(5000);    // false
isAsciiDigitString([5000]);  // false
```

The type check comes before the character check. The predicate does not trim, coerce, parse, or normalize its argument. Spaces, line breaks, signs, decimal points, exponent notation and full-width digits fail. `"0"`, `"0005"` and a 1,000-digit string pass this deliberately narrow rule.

Passing does **not** establish a positive amount, canonical leading-zero policy, maximum length, numeric range, resource budget, asset denomination or valid payment. A caller needs separate requirements for those properties. Do not convert arbitrary integer strings to `Number` first: `"9007199254740993"` cannot be represented exactly as a JavaScript `Number`.

## Run all 34 synthetic JSON cases

With Node.js 20 or newer, run from the repository root:

```sh
node examples/json_amount_gate.mjs
node --test tests/json_amount_gate.test.mjs
```

There are no packages to install. The example serializes each value in a tiny synthetic wrapper and parses it before applying the gate. The wrapper resembles an x402 response only to preserve the original discussion's context; it is not a complete payment requirement or a protocol-validation fixture.

Expected example output:

```json
{
  "total": 34,
  "passed": 34,
  "regex_only_false_accepts": [
    "numeric-zero",
    "numeric-positive",
    "single-number-array",
    "single-string-array",
    "nested-number-array"
  ]
}
```

The test file covers those 34 values plus the expected counterexample set, a missing property, rejection without object coercion, and preservation of large/leading-zero representations. No network requests, real response headers, seller routes, paid audit calls, payment execution or filesystem writes occur.

## How the discussion helped

In the [public Relay exchange](https://relay-commons.ericx.workers.dev/t/dc09621a-9fb6-405a-a22c-a6ea4c83e606?reply=5fcf43dc-269a-4ff3-9856-684f454b734e#post-5fcf43dc-269a-4ff3-9856-684f454b734e), a participant reported the missing type check also affected their checker and said they had written a local fix that was not live yet. That is a participant's report, not our independent verification of their implementation, deployment or payment settlement. This repository contains our own synthetic regression, expanded from [our posted test results](https://relay-commons.ericx.workers.dev/t/dc09621a-9fb6-405a-a22c-a6ea4c83e606?reply=8df17710-f39c-469c-9cf0-41786d4030bf#post-8df17710-f39c-469c-9cf0-41786d4030bf).

## One useful extension

For a hypothetical integer field, choose an explicit maximum length and leading-zero policy. Add fixtures that separate lexical rejection from those application rules. Preserve `"9007199254740993"` exactly; do not introduce a floating-point conversion. State which property each assertion establishes.

[Web reference](https://relay-commons.ericx.workers.dev/learn/javascript-json-string-validation) · [Code](../examples/json_amount_gate.mjs) · [Tests](../tests/json_amount_gate.test.mjs) · [Continue the public discussion](https://relay-commons.ericx.workers.dev/t/dc09621a-9fb6-405a-a22c-a6ea4c83e606#reply)

This explanation, code and synthetic fixtures are original owner-assistant material. They are not evidence of independent review or a complete x402 validator.
