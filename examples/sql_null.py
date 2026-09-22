"""A three-row SQLite fixture showing why inequality omits SQL NULL values."""

import sqlite3
from typing import Optional, Sequence


# Fixed educational queries. Each policy deliberately treats candidate NULLs
# differently; neither is a universal replacement for NOT IN.
EXCLUSION_QUERIES = {
    "NOT IN": "SELECT id, value FROM sample WHERE value NOT IN (SELECT value FROM excluded) ORDER BY id",
    "NOT EXISTS, keep missing candidates": """
        SELECT s.id, s.value FROM sample AS s
        WHERE NOT EXISTS (SELECT 1 FROM excluded AS e WHERE e.value = s.value)
        ORDER BY s.id
    """,
    "NOT EXISTS, known candidates only": """
        SELECT s.id, s.value FROM sample AS s
        WHERE s.value IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM excluded AS e WHERE e.value = s.value)
        ORDER BY s.id
    """,
}


def make_fixture() -> sqlite3.Connection:
    """Return a fresh in-memory database; callers must close the connection."""
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value INTEGER)")
    connection.executemany(
        "INSERT INTO sample (id, value) VALUES (?, ?)",
        [(1, 7), (2, 8), (3, None)],
    )
    return connection


def make_exclusion_fixture(values: Sequence[Optional[int]] = (7, None)) -> sqlite3.Connection:
    """Add an exclusion table to the three-row fixture; caller closes it."""
    connection = make_fixture()
    connection.execute("CREATE TABLE excluded (value INTEGER)")
    connection.executemany("INSERT INTO excluded (value) VALUES (?)", [(value,) for value in values])
    return connection


def main() -> None:
    connection = make_fixture()
    try:
        for predicate in ("value <> 7", "value <> 7 OR value IS NULL", "value IS NULL"):
            # These predicates are fixed local examples, never external input.
            rows = connection.execute(
                f"SELECT id, value FROM sample WHERE {predicate} ORDER BY id"
            ).fetchall()
            print(f"{predicate}: {rows}")
        print("Python None represents SQL NULL in these results.")
    finally:
        connection.close()
    connection = make_exclusion_fixture()
    try:
        print("Exclusion table: [7, NULL]")
        for label, query in EXCLUSION_QUERIES.items():
            print(f"{label}: {connection.execute(query).fetchall()}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
