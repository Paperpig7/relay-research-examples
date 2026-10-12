"""Read-only acceptance checks for a small frozen SQLite recovery fixture.

This is an illustrative predicate, not a production restore or safety tool.
"""

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from typing import Tuple, Union


@dataclass(frozen=True)
class AcceptanceResult:
    opened: bool
    decision: str
    reasons: Tuple[str, ...]


REQUIRED_TABLES = {
    "tasks": (
        (("id", "TEXT", 1, None, 1, 0), ("status", "TEXT", 1, None, 0, 0)),
        (("T", "ready"),),
    ),
    "audit": (
        (("task_id", "TEXT", 1, None, 1, 0), ("event", "TEXT", 1, None, 0, 0)),
        (("T", "restored"),),
    ),
}
EXPECTED_CASES = {
    "complete": "PASS",
    "missing_audit": "REJECT",
    "extra_optional": "PASS",
    "wrong_values": "REJECT",
    "open_only": "REJECT",
}


def inspect_fixture(path: Union[str, Path]) -> AcceptanceResult:
    """Inspect an existing frozen DB with mode=ro; never repair or create it.

    Accept only user_version=1 and the exact declared column descriptors and
    rows below. Extra unrelated objects are not checked. This does not establish
    freshness, provenance, all SQL constraints, or a working restore procedure.
    """
    reasons = []
    opened = False
    database = Path(path).resolve()
    try:
        # as_uri escapes URI punctuation in filenames; mode=ro prevents SQLite's
        # usual behavior of creating an empty file when a database is missing.
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as connection:
            opened = True
            connection.execute("BEGIN")
            if connection.execute("PRAGMA user_version").fetchone()[0] != 1:
                reasons.append("user_version differs")
            objects = dict(connection.execute("SELECT name,type FROM sqlite_master"))
            for name, (required_columns, required_rows) in REQUIRED_TABLES.items():
                if objects.get(name) != "table":
                    reasons.append("required table " + name + " missing")
                    continue
                # Names are only our two constants, never caller-supplied SQL.
                # table_xinfo includes generated/hidden columns that table_info
                # omits; each declared column must have hidden=0 here.
                columns = tuple(row[1:] for row in connection.execute("PRAGMA table_xinfo(" + name + ")"))
                if columns != required_columns:
                    reasons.append(name + " column schema differs")
                    continue
                # Only two rows are needed to detect any extra required-table
                # rows; avoid loading an arbitrarily large table into memory.
                rows = tuple(connection.execute("SELECT * FROM " + name + " ORDER BY 1 LIMIT 2"))
                if rows != required_rows:
                    reasons.append(name + " row set differs")
            connection.rollback()
    except (OSError, sqlite3.Error) as exc:
        reasons.append("SQLite read failure: " + type(exc).__name__ + ": " + str(exc))
    return AcceptanceResult(opened, "REJECT" if reasons else "PASS", tuple(reasons))


def create_fixture(path: Union[str, Path], case: str) -> None:
    """Create a named synthetic fixture in a NEW file; refuse any existing file.

    Intended for a caller-owned disposable directory. This is deliberately
    separate from inspect_fixture, which only reads existing files.
    """
    if case not in EXPECTED_CASES:
        raise ValueError("Unknown fixture case: " + case)
    database = Path(path)
    # Exclusive creation prevents silently overwriting an existing database.
    with database.open("xb"):
        pass
    with closing(sqlite3.connect(database)) as connection:
        with connection:
            connection.execute("PRAGMA user_version=1")
            if case == "open_only":
                return
            connection.execute("CREATE TABLE tasks(id TEXT NOT NULL PRIMARY KEY,status TEXT NOT NULL)")
            status = "blocked" if case == "wrong_values" else "ready"
            connection.execute("INSERT INTO tasks VALUES('T',?)", (status,))
            if case != "missing_audit":
                connection.execute("CREATE TABLE audit(task_id TEXT NOT NULL PRIMARY KEY,event TEXT NOT NULL)")
                task_id = "U" if case == "wrong_values" else "T"
                connection.execute("INSERT INTO audit VALUES(?,'restored')", (task_id,))
            if case == "extra_optional":
                connection.execute("CREATE TABLE notes(body TEXT)")
                connection.execute("INSERT INTO notes VALUES('optional synthetic note')")


def main() -> None:
    with TemporaryDirectory(prefix="relay-sqlite-example-") as directory:
        for case, expected in EXPECTED_CASES.items():
            database = Path(directory) / (case + ".sqlite")
            create_fixture(database, case)
            before = database.read_bytes()
            result = inspect_fixture(database)
            unchanged = before == database.read_bytes()
            print(f"{case}: opened={result.opened}, decision={result.decision}, unchanged={unchanged}")
            if result.decision != expected or not unchanged:
                raise RuntimeError("Unexpected fixture result: " + case)
    print("Only temporary synthetic files were created; they have been removed.")
    print("Passing this predicate does not prove freshness or production recovery.")


if __name__ == "__main__":
    main()
