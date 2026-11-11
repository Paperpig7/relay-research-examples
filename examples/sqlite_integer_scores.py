"""Round-trip decimal-string scores through Python's sqlite3 driver."""

from contextlib import closing
import json
import re
import sqlite3


DECIMAL_SCORE = re.compile(r"(?:0|[1-9][0-9]{0,18})")
SQLITE_INTEGER_MAX = 2**63 - 1


def insert_score(db: sqlite3.Connection, decoded_score: object) -> None:
    """Store one nonnegative, signed-64 score from a decoded JSON value."""
    if not isinstance(decoded_score, str) or not DECIMAL_SCORE.fullmatch(decoded_score):
        raise ValueError("expected a canonical string of 1 to 19 ASCII digits")
    score = int(decoded_score)
    if score > SQLITE_INTEGER_MAX:
        raise ValueError("score exceeds the signed 64-bit maximum")
    db.execute("INSERT INTO scores (score) VALUES (?)", (score,))


def main() -> None:
    wire = '["9007199254740992", "9007199254740993", "9223372036854775807", "9223372036854775808"]'
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute("CREATE TABLE scores (score INTEGER NOT NULL)")
        for score in json.loads(wire):
            try:
                insert_score(db, score)
            except ValueError as error:
                print(f"Rejected {score}: {error}")
        db.commit()
        for value, storage in db.execute("SELECT score, typeof(score) FROM scores ORDER BY score DESC"):
            print(f"{value}  {storage}")


if __name__ == "__main__":
    main()
