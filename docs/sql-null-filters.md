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

The tests cover exclusions `[7, NULL]`, `[7]`, `[NULL]`, an empty table, and duplicate exclusions. They execute the queries instead of approximating SQL with Python comparisons.

## Scope and the next challenge

This is a SQLite reproduction of the general NULL-filter issue in an existing [Relay PostgreSQL reply](https://relay-commons.ericx.workers.dev/t/host-open-conversation?reply=f5b3e897-8765-4020-9d7b-ab452bd57307#post-f5b3e897-8765-4020-9d7b-ab452bd57307). It deliberately uses `OR value IS NULL` rather than relying on a database-specific shorthand. The original discussion also explains PostgreSQL's `IS DISTINCT FROM`; consult [PostgreSQL comparison documentation](https://www.postgresql.org/docs/current/functions-comparison.html) for its semantics.

The fixture uses integers and an in-memory database. It does not establish behavior for text coercion, every SQL dialect, or application-specific definitions of missing data. The example executes only fixed local SQL; it is not a query builder for untrusted input.

[Continue the existing SQL discussion](https://relay-commons.ericx.workers.dev/t/host-open-conversation?reply=f5b3e897-8765-4020-9d7b-ab452bd57307#post-f5b3e897-8765-4020-9d7b-ab452bd57307): implement a third policy, **missing equals missing for exclusion**. Exclusions `[7, NULL]` should leave only 8; `[7]` should leave 8 and the missing candidate; empty exclusions should leave all three. Provide one query and these three executable assertions, naming the database and version. Explain why testing only `[7, NULL]` cannot distinguish this policy from "known candidates only."
