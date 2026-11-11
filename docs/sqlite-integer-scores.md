# Can SQLite distinguish 2⁵³ from 2⁵³ + 1?

Yes. Send the scores as JSON strings, convert each validated string directly to a Python integer, and bind that integer to SQLite. In this example, SQL ranks `9007199254740993` ahead of `9007199254740992` after a commit. Both read back exactly, as does SQLite’s largest signed integer, `9223372036854775807`.

The original Relay discussion proposed a wire format for nonnegative scores. On October 27, a follow-up left one question open about the database driver. This example checks Python’s standard-library `sqlite3` driver against an in-memory database. [October 27 storage question](https://relay-commons.ericx.workers.dev/t/5eb4d591-6901-47f0-83ce-cb8b0f9ad6b8?reply=60fa09dd-375f-4251-82e6-36efd9583993#post-60fa09dd-375f-4251-82e6-36efd9583993)

## Run it

From the repository root, run the fixture and its focused tests together.

```sh
python3 -B -m examples.review_receipt sqlite-integer-scores
```

The example itself runs with `python3 -B -m examples.sqlite_integer_scores`. It prints the rejected input first, then the committed scores in descending order alongside SQLite’s `typeof(score)`.

```text
Rejected 9223372036854775808: score exceeds the signed 64-bit maximum
9223372036854775807  integer
9007199254740993  integer
9007199254740992  integer
```

## Which inputs fit?

| JSON score on the wire | Wire format | SQLite example |
| --- | --- | --- |
| `"9007199254740993"` | Valid | Stores and returns the exact integer |
| `"9223372036854775807"` | Valid | Stores the largest accepted score |
| `"9223372036854775808"` | Valid | Rejects before calling the driver |
| `"09"` or `"1\n"` | Invalid | Rejects the leading zero or trailing newline |
| `9007199254740993` | Invalid | Requires a JSON string |

The wire format accepts `"0"` or one to nineteen ASCII digits beginning with 1–9. The format applies after JSON decoding, so `"\u0031"` and `"1"` supply the same string. The SQLite consumer adds a ceiling of 2⁶³−1. Checking the grammar first bounds the conversion to at most nineteen digits, and Python’s `int` compares them exactly. The accepted value goes into a `?` parameter. [Code](../examples/sqlite_integer_scores.py) · [Tests](../tests/test_sqlite_integer_scores.py) · [Python’s SQLite type mappings](https://docs.python.org/3/library/sqlite3.html#sqlite-and-python-types)

## Why check the bound in the application?

An ordinary SQLite column declared `INTEGER` can store an out-of-range decimal string as a floating-point `REAL`. Try these two consecutive scores directly in a scratch database.

```sql
CREATE TABLE raw (score INTEGER);
INSERT INTO raw VALUES ('9223372036854775808'), ('9223372036854775809');
SELECT typeof(score), count(*), count(DISTINCT score)
FROM raw GROUP BY typeof(score);
```

The result is `real | 2 | 1`. Two rows survived, but they hold one distinct value. A row-count check alone would miss the lost point. The Python fixture checks the range before insertion and its tests inspect both the readback values and their SQLite storage class. [SQLite type affinity](https://sqlite.org/datatype3.html#type_affinity)

For another driver, try the same adjacent pair and upper boundary, then inspect the returned values and runtime types. A client that converts the result to floating point can still lose a point after SQLite returns the exact integer.
