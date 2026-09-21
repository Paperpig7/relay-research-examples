"""A three-row SQLite fixture showing why inequality omits SQL NULL values."""

import sqlite3


def make_fixture() -> sqlite3.Connection:
    """Return a fresh in-memory database; callers must close the connection."""
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value INTEGER)")
    connection.executemany(
        "INSERT INTO sample (id, value) VALUES (?, ?)",
        [(1, 7), (2, 8), (3, None)],
    )
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


if __name__ == "__main__":
    main()
