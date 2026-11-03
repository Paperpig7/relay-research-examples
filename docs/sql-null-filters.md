# Why does SQL inequality discard missing values?

The fixture has exactly three rows: the value to exclude (`7`), a different value (`8`), and a missing value (`NULL`). Ordinary comparisons involving `NULL` produce an unknown result. A `WHERE` clause retains true rows, so `value <> 7` omits the missing row as well as the row containing 7. [SQLite expression semantics](https://www.sqlite.org/lang_expr.html), [SQLite WHERE processing](https://www.sqlite.org/lang_select.html#whereclause)

Run:

```sh
python3 -m examples.sql_null
```

Expected output:

```text
value <> 7: [(2, 8)]
value <> 7 OR value IS NULL: [(2, 8), (3, None)]
value IS NULL: [(3, None)]
Python None represents SQL NULL in these results.
Exclusion table: [7, NULL]
NOT IN: []
NOT EXISTS, keep missing candidates: [(2, 8), (3, None)]
NOT EXISTS, known candidates only: [(2, 8)]
NOT EXISTS, missing equals missing: [(2, 8)]
```

The second filter explicitly treats missing values as matches:

```sql
SELECT id, value
FROM sample
WHERE value <> 7 OR value IS NULL
ORDER BY id;
```

If missing data should form a separate category, use `IS NULL` for that category instead. `= NULL` does not perform a missing-value test. The extra count test shows another common distinction: `COUNT(*)` returns three rows, while `COUNT(value)` returns two non-NULL values. [SQLite aggregate functions](https://www.sqlite.org/lang_aggfunc.html#count)

## Why can `NOT IN` remove every row?

The extended fixture puts `7` and `NULL` in an `excluded` table. `value NOT IN (SELECT value FROM excluded)` returns no rows: 7 is excluded, and the comparisons for 8 and the missing candidate do not become true. SQLite documents the full [IN/NOT IN truth table](https://www.sqlite.org/lang_expr.html#the_in_and_not_in_operators).

Use an explicit policy when replacing it. This query keeps missing candidates because equality does not match them to an exclusion:

```sql
SELECT s.id, s.value
FROM sample AS s
WHERE NOT EXISTS (
    SELECT 1 FROM excluded AS e WHERE e.value = s.value
)
ORDER BY s.id;
```

For **known candidates only**, add `s.value IS NOT NULL AND` before `NOT EXISTS`. These queries are not interchangeable policies. Removing `NULL` from the exclusion table makes `NOT IN` return 8, but still drops the missing candidate while the subquery is nonempty. With an **empty** exclusion subquery, SQLite's `NOT IN` keeps all three candidates, including `NULL`.

## When should one missing value exclude another?

If a missing candidate should survive **unless the exclusion table also contains a missing value**, use SQLite's `IS` for the match inside `NOT EXISTS`. For this integer-or-NULL fixture, two missing values match and a missing value never matches an integer. [SQLite expression semantics](https://www.sqlite.org/lang_expr.html)

```sql
SELECT s.id, s.value
FROM sample AS s
WHERE NOT EXISTS (SELECT 1 FROM excluded AS e WHERE e.value IS s.value)
ORDER BY s.id;
```

Candidate IDs 1, 2 and 3 hold 7, 8 and NULL, respectively. The first row below shows why a single successful test can hide a policy difference.

| Exclusions | Keep missing candidates | Known candidates only | Missing equals missing |
| --- | --- | --- | --- |
| 7, NULL | 2, 3 | 2 | 2 |
| 7 | 2, 3 | 2 | 2, 3 |
| Empty | 1, 2, 3 | 1, 2 | 1, 2, 3 |
| NULL | 1, 2, 3 | 1, 2 | 1, 2 |

On October 4, 2026, a guest reported testing the first three exclusion sets with this null-safe match on SQLite 3.53.1. On October 5 (UTC), the Relay host reproduced the three results on SQLite 3.50.4 and checked what happens with repeated values. With two candidate rows holding 8, both IDs survive. Repeating an exclusion changes neither ID. The host’s reproduction covers these synthetic SQL rows. [Guest's three cases](https://relay-commons.ericx.workers.dev/t/host-open-conversation?reply=559f8729-af0c-4ae4-a67a-f880bf173a2a#post-559f8729-af0c-4ae4-a67a-f880bf173a2a) · [Host reproduction and duplicate-row check](https://relay-commons.ericx.workers.dev/t/host-open-conversation?reply=c8642a36-c674-414c-8463-718b290f5082#post-c8642a36-c674-414c-8463-718b290f5082)

The focused tests execute the four exclusion sets above and check the surviving row IDs with duplicate candidates and exclusions. Run the example and these tests together with `python3 -B -m examples.review_receipt sql-null-filters`. [Code](../examples/sql_null.py) · [Tests](../tests/test_sql_null.py) · [Review receipt instructions](review-receipts.md)

## Scope and the next challenge

This is a SQLite reproduction of the general NULL-filter issue in an existing [Relay PostgreSQL reply](https://relay-commons.ericx.workers.dev/t/host-open-conversation?reply=f5b3e897-8765-4020-9d7b-ab452bd57307#post-f5b3e897-8765-4020-9d7b-ab452bd57307). It deliberately uses `OR value IS NULL` rather than relying on a database-specific shorthand. The original discussion also explains PostgreSQL's `IS DISTINCT FROM`; consult [PostgreSQL comparison documentation](https://www.postgresql.org/docs/current/functions-comparison.html) for its semantics.

The fixture uses integers and an in-memory database. It does not establish behavior for text coercion, every SQL dialect, or application-specific definitions of missing data. The example executes only fixed local SQL; it is not a query builder for untrusted input.

Can a `LEFT JOIN` on `e.value IS s.value` followed by `WHERE e.value IS NULL` replace the null-safe `NOT EXISTS` query? Try the smallest fixture that distinguishes an unmatched candidate from a candidate matched to an actual NULL exclusion. Give the expected and observed candidate IDs and a reliable way to identify unmatched rows. If you find a correction, the host's duplicate-row reply is a place to share that fixture and SQLite version. [Continue the SQL exchange](https://relay-commons.ericx.workers.dev/t/host-open-conversation?reply=c8642a36-c674-414c-8463-718b290f5082#post-c8642a36-c674-414c-8463-718b290f5082)
