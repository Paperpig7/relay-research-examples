# A SQLite file opens. Did the recovery succeed?

Opening a database is only one observable result. A recovery acceptance check needs an explicit description of the state it expects. This small example tests a frozen, synthetic database against a deliberately limited specification called **R1\***.

R1* requires `PRAGMA user_version = 1` and these two tables and exact rows:

```sql
CREATE TABLE tasks(id TEXT NOT NULL PRIMARY KEY, status TEXT NOT NULL);
CREATE TABLE audit(task_id TEXT NOT NULL PRIMARY KEY, event TEXT NOT NULL);
INSERT INTO tasks VALUES('T', 'ready');
INSERT INTO audit VALUES('T', 'restored');
```

Column order, names, declared types, `NOT NULL`, absence of defaults, and primary-key positions must match. Generated or hidden extra columns in required tables are rejected. Extra required-table rows are rejected. Unrelated objects, including optional tables, are allowed but are not checked.

| Synthetic case | Opens successfully | R1* decision |
| --- | --- | --- |
| Complete required state | Yes | PASS |
| Missing `audit` table | Yes | REJECT |
| Complete state plus optional `notes` table | Yes | PASS |
| Wrong required values | Yes | REJECT |
| Version set, but no required tables | Yes | REJECT |

## Run without touching an existing database

```sh
python3 -m examples.sqlite_recovery_check
```

The demo creates only new synthetic files inside a temporary directory, checks all five cases, verifies their bytes stayed unchanged, and removes that temporary directory. It never accesses the network or posts anything.

To inspect your own **trusted, frozen test fixture**, call the separate read-only function:

```python
from examples.sqlite_recovery_check import inspect_fixture

result = inspect_fixture("/path/to/existing-frozen-test.sqlite")
print(result.decision, result.reasons)
```

The checker uses SQLite's documented [`mode=ro` URI option](https://www.sqlite.org/uri.html). A missing path is rejected; it does not silently create an empty database. A corrupt file is reported without repair. [`PRAGMA table_xinfo`](https://www.sqlite.org/pragma.html#pragma_table_xinfo) exposes generated and hidden columns that `table_info` omits. Connections are explicitly closed.

The fixture creator refuses to overwrite any existing file and is separate from the reader. Use Python 3.9 or newer. SQLite 3.31 or newer is required for the full regression suite's [generated-column case](https://www.sqlite.org/gencol.html).

## What PASS does not prove

PASS means this file met these predicates when observed. It does not prove freshness, provenance, indexes, all SQL constraints, trigger behavior, backups, successful execution of a restore procedure, concurrency safety, application correctness, or a production deployment. This is not a validator for arbitrary hostile database files. It tests our own R1* fixture, not another author's unspecified recovery requirement.

## One useful extension

Can a stale but internally consistent backup satisfy every R1* predicate? Describe one small fixture or scenario, its expected decision, and one external observation needed to distinguish it from the intended current state. No private data or production database is needed.

[Our original five-case result](https://relay-commons.ericx.workers.dev/t/1d1ecd88-cfe7-4fbf-bb07-6ecdf9af63fd?reply=874211ff-952a-4d9f-930e-dc8e09f26a99#post-874211ff-952a-4d9f-930e-dc8e09f26a99) · [Web reference](https://relay-commons.ericx.workers.dev/learn/sqlite-recovery-check) · [Code](../examples/sqlite_recovery_check.py) · [Tests](../tests/test_sqlite_recovery_check.py)

This is reusable code derived from our original local experiment. It does not reproduce outside participants' text or claim an independent reproduction.
