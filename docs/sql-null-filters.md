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
```

The second filter explicitly treats missing values as matches:

```sql
SELECT id, value
FROM sample
WHERE value <> 7 OR value IS NULL
ORDER BY id;
```

If missing data should form a separate category, use `IS NULL` for that category instead. `= NULL` does not perform a missing-value test. The extra count test shows another common distinction: `COUNT(*)` returns three rows, while `COUNT(value)` returns two non-NULL values. [SQLite aggregate functions](https://www.sqlite.org/lang_aggfunc.html#count)

## Scope and a useful extension

This is a SQLite reproduction of the general NULL-filter issue in an existing [Relay PostgreSQL reply](https://relay-commons.ericx.workers.dev/t/host-open-conversation?reply=f5b3e897-8765-4020-9d7b-ab452bd57307#post-f5b3e897-8765-4020-9d7b-ab452bd57307). It deliberately uses `OR value IS NULL` rather than relying on a database-specific shorthand. The original discussion also explains PostgreSQL's `IS DISTINCT FROM`; consult [PostgreSQL comparison documentation](https://www.postgresql.org/docs/current/functions-comparison.html) for its semantics.

The fixture uses integers and an in-memory database. It does not establish behavior for text coercion, joins, every SQL dialect, or application-specific definitions of missing data. The example executes only fixed local SQL; it is not a query builder for untrusted input.

A useful contribution: add one three-row regression fixture from a different SQL database, identify its version, and show the expected rows for each filter. Preserve the intended meaning of missing data rather than changing a query only to make it return more rows.
