"""An ordered SQLite retry fixture with a deliberately lost acknowledgement.

Run: python3 -m examples.sqlite_lost_ack
Only new temporary synthetic databases are used by the demo. No network calls.
Closing and reopening connections is not a process-crash or power-loss test.
"""

from contextlib import closing, contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory


@dataclass(frozen=True)
class Event:
    seq: int
    event_id: str
    old: str
    new: str

    def __post_init__(self):
        if type(self.seq) is not int or self.seq < 1:
            raise ValueError("sequence must be a positive integer")
        if any(type(value) is not str or not value
               for value in (self.event_id, self.old, self.new)):
            raise ValueError("event ID and values must be nonempty strings")
        if self.old == self.new:
            raise ValueError("an event must describe a transition")


@contextmanager
def transaction(db):
    """Own one explicit transaction; do not silently commit a caller's work."""
    if db.in_transaction:
        raise ValueError("a transaction is already active")
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
        db.commit()
    except BaseException:
        db.rollback()
        raise


def reopen(path):
    """Open an existing trusted fixture, never create a missing database."""
    uri = Path(path).resolve().as_uri() + "?mode=rw"
    db = sqlite3.connect(uri, uri=True, isolation_level=None)
    db.row_factory = sqlite3.Row
    return db


def _create(path, schema):
    # Refuse to overwrite a file. Call only in a disposable, caller-owned folder.
    with Path(path).open("xb"):
        pass
    db = reopen(path)
    try:
        db.executescript("BEGIN IMMEDIATE;\n" + schema + "\nCOMMIT;")
    except BaseException:
        db.rollback()
        db.close()
        raise
    return db


def create_sender(path):
    return _create(path, """
        CREATE TABLE state (
            id INTEGER PRIMARY KEY CHECK(id=1),
            observed TEXT NOT NULL, seq INTEGER NOT NULL, ack_seq INTEGER NOT NULL
        );
        INSERT INTO state VALUES(1, 'A', 0, 0);
        CREATE TABLE journal (
            seq INTEGER PRIMARY KEY, event_id TEXT NOT NULL UNIQUE,
            old TEXT NOT NULL, new TEXT NOT NULL
        );
    """)


def create_receiver(path):
    return _create(path, """
        CREATE TABLE state (
            id INTEGER PRIMARY KEY CHECK(id=1),
            value TEXT NOT NULL, applied_seq INTEGER NOT NULL
        );
        INSERT INTO state VALUES(1, 'A', 0);
        CREATE TABLE effects (
            seq INTEGER PRIMARY KEY, event_id TEXT NOT NULL UNIQUE,
            old TEXT NOT NULL, new TEXT NOT NULL
        );
    """)


def confirm(sender, new):
    """Journal a confirmed transition. Sampling/debounce is outside this demo."""
    if type(new) is not str or not new:
        raise ValueError("confirmed value must be a nonempty string")
    with transaction(sender):
        state = sender.execute("SELECT * FROM state WHERE id=1").fetchone()
        if new == state["observed"]:
            return None
        seq = state["seq"] + 1
        event = Event(seq, "synthetic-stream:" + str(seq), state["observed"], new)
        sender.execute("INSERT INTO journal VALUES (?, ?, ?, ?)",
                       (event.seq, event.event_id, event.old, event.new))
        sender.execute("UPDATE state SET observed=?, seq=? WHERE id=1", (new, seq))
    return event


def head(sender):
    """Return the first unacknowledged journal entry, not the latest value."""
    row = sender.execute("""
        SELECT j.* FROM journal AS j JOIN state AS s ON j.seq=s.ack_seq+1
        WHERE s.id=1
    """).fetchone()
    return Event(**dict(row)) if row else None


def receive(receiver, event):
    """Commit a database effect and its dedup receipt together, then return ID."""
    if not isinstance(event, Event):
        raise TypeError("event must be an Event")
    with transaction(receiver):
        known = receiver.execute("SELECT * FROM effects WHERE event_id=?",
                                 (event.event_id,)).fetchone()
        if known:
            if Event(**dict(known)) != event:
                raise ValueError("same event ID, different payload")
            return event.event_id
        state = receiver.execute("SELECT * FROM state WHERE id=1").fetchone()
        if event.seq != state["applied_seq"] + 1 or event.old != state["value"]:
            raise ValueError("noncontiguous event")
        receiver.execute("INSERT INTO effects VALUES (?, ?, ?, ?)",
                         (event.seq, event.event_id, event.old, event.new))
        receiver.execute("UPDATE state SET value=?, applied_seq=? WHERE id=1",
                         (event.new, event.seq))
    return event.event_id


def acknowledge(sender, event_id):
    """Apply a trusted receiver receipt without skipping or rewinding the cursor."""
    with transaction(sender):
        row = sender.execute("SELECT seq FROM journal WHERE event_id=?",
                             (event_id,)).fetchone()
        ack = sender.execute("SELECT ack_seq FROM state WHERE id=1").fetchone()[0]
        if row is None or row["seq"] > ack + 1:
            raise ValueError("unknown or noncontiguous acknowledgement")
        if row["seq"] == ack + 1:
            sender.execute("UPDATE state SET ack_seq=? WHERE id=1", (row["seq"],))


def run_demo():
    attempts = []
    with TemporaryDirectory(prefix="relay-lost-ack-") as folder:
        sender_path = Path(folder) / "sender.sqlite"
        receiver_path = Path(folder) / "receiver.sqlite"
        with closing(create_sender(sender_path)) as sender:
            with closing(create_receiver(receiver_path)) as receiver:
                first = confirm(sender, "B")
                attempts.append(first.seq)
                receive(receiver, first)  # Drop the returned receipt, after commit.
                confirm(sender, "A")      # Keep A→B and B→A as separate entries.
                if head(sender) != first:
                    raise RuntimeError("lost acknowledgement skipped event 1")

        with closing(reopen(sender_path)) as sender:
            with closing(reopen(receiver_path)) as receiver:
                while head(sender) is not None:
                    event = head(sender)
                    attempts.append(event.seq)
                    acknowledge(sender, receive(receiver, event))
                acknowledge(sender, first.event_id)  # A late receipt cannot rewind.
                effects = [dict(row) for row in receiver.execute(
                    "SELECT * FROM effects ORDER BY seq")]
                receiver_state = dict(receiver.execute(
                    "SELECT value,applied_seq FROM state WHERE id=1").fetchone())
                ack_seq = sender.execute("SELECT ack_seq FROM state WHERE id=1").fetchone()[0]
                if (attempts != [1, 1, 2] or ack_seq != 2
                        or [(row["old"], row["new"]) for row in effects]
                        != [("A", "B"), ("B", "A")]
                        or receiver_state != {"value": "A", "applied_seq": 2}):
                    raise RuntimeError("unexpected retry outcome")
                result = {
                    "delivery_attempt_sequences": attempts,
                    "committed_effects": effects,
                    "receiver": receiver_state,
                    "sender_ack_seq": ack_seq,
                    "temporary_databases_removed_on_return": True,
                }
    return result


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
