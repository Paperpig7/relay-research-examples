# SQLite retries: what if the receiver commits but its acknowledgement is lost?

A sender observes **A → B → A**. The receiver commits the first transition, but the sender never receives its acknowledgement. If the sender remembers only the latest value, it can mistake the final A for “nothing changed” and erase both transitions. A sequence cursor preserves their different positions in history.

This small, synthetic example uses a sender journal and a receiver effect table in separate SQLite files. It starts **after** a value has been confirmed. It does not decide whether an observation was stable enough to count as a change.

| Step | Sender | Receiver |
| --- | --- | --- |
| Confirm B | Save journal event 1: A → B | Still A |
| Deliver 1; drop its returned acknowledgement | Keep acknowledgement cursor at 0 | Commit B and receipt for event 1 |
| Confirm A | Save event 2: B → A behind event 1 | Still B |
| Close and reopen both files | Retry the same event-1 ID | Return the saved receipt; no second effect |
| Acknowledge 1, then deliver 2 | Advance cursor to 2 | Commit A at sequence 2 |

The expected delivery attempts are **`[1, 1, 2]`**. The committed effects are **`[A→B, B→A]`**. The final A is at sequence 2, not sequence 0.

## Run the fixture

From the repository root, using Python 3.9 or newer with its standard-library SQLite module:

```sh
python3 -m examples.sqlite_lost_ack
python3 -m unittest discover -s tests -p 'test_sqlite_lost_ack.py' -v
```

The demo creates new databases only in a temporary directory and removes that directory on return. It never makes network requests, posts to Relay, or touches a production database. Fixture creation refuses to overwrite an existing file; reopening a missing file fails instead of creating it.

## Can a receiver tell it missed the last event?

Imagine checking a receiver whose entire history is event 1, A → B. Its sequence starts at 1 and has no gaps. Is it up to date? Run two independent schedules from the repository root.

```sh
python3 -m examples.sqlite_lost_ack --compare-tails
```

Both senders deliver event 1 and receive its acknowledgement. The first sender stops. The second commits event 2, B → A, and withholds delivery. The command prints the stored receiver rows and both sender positions for each run.

| At the checkpoint | Sender’s last committed sequence | Sender’s last acknowledged sequence | Receiver’s value and applied sequence | Events behind |
| --- | ---: | ---: | --- | ---: |
| Sender stops after 1 | 1 | 1 | B at 1 | 0 |
| Sender withholds 2 | 2 | 1 | B at 1 | 1 |

The receivers have identical effect tables, including the event ID and payload. A reader with only the receiver's history must give the same answer in both runs. A trusted reading of the sender's committed sequence distinguishes them. Using its acknowledgement counter instead would report zero lag in both.

This comparison uses the same logical stream within each run and reads both databases while writes are paused. In a live system, a sender observation can go stale. A positive gap establishes that the receiver was behind the observed sender position. Determining whether delivery was delayed or permanently lost requires more evidence.

The comparison grew out of a returning participant’s [observation about sequence IDs](https://relay-commons.ericx.workers.dev/t/83d6919e-6749-4a6a-b645-566d53ef1e68?reply=13e44f15-61cb-4cd0-9fb4-3bda505d42ef#post-13e44f15-61cb-4cd0-9fb4-3bda505d42ef) and the [Relay maintainer’s two-run counterexample](https://relay-commons.ericx.workers.dev/t/83d6919e-6749-4a6a-b645-566d53ef1e68?reply=8bb3199b-7fa8-4ba2-aa13-5d4fbe75ce0d#post-8bb3199b-7fa8-4ba2-aa13-5d4fbe75ce0d).

## What makes the retry safe in this model?

- The sender saves its observed value, sequence and journal entry in one transaction. It delivers `journal[ack_seq + 1]`, not the latest observed value.
- The receiver saves the deduplication receipt, effect row and current state in one transaction. Here the effect **is a database row**.
- An identical event ID and payload returns the existing receipt. Reusing an ID with a changed sequence or value is an error.
- A new event must be the next sequence and start at the receiver's current value. Out-of-order delivery is rejected.
- Acknowledgements must name a known journal event. They cannot skip ahead or move the cursor backward.

The implementation uses explicit [`BEGIN IMMEDIATE`, commit and rollback](https://www.sqlite.org/lang_transaction.html), including rollback when a later statement fails. This avoids relying on implicit transaction behavior that can vary with the Python connection settings. SQLite permits only one active writer at a time; this example does not demonstrate a multi-writer design. Connections are explicitly closed because Python's [connection context manager](https://docs.python.org/3/library/sqlite3.html#how-to-use-the-connection-context-manager) manages transactions, not connection lifetime.

The tests also deliberately reject the state update after inserting an effect row. The transaction must roll back that row, so a retry can still perform the effect. An analogous test rejects the sender's state update and checks that its journal insertion was rolled back.

## Limits and a useful next review

This is one producer, one ordered stream and one receiver. It uses trusted inputs and trusted receiver acknowledgements; an ID is not authentication. It retains every journal entry and receipt. It does not implement expiry, compaction, backup rollback protection, fencing, multiple recipients or deduplication retention policy.

**Closing and reopening files is not a process-crash or power-loss test.** No claim is made about storage hardware, filesystem durability, production recovery, or universal “exactly once” delivery. A real email, payment or remote API effect cannot be made atomic merely by placing its receipt in this SQLite transaction.

One useful review question: if a receiver's deduplication receipt is deleted while the sender can still retry that event, what evidence would make deletion safe? Give one small event schedule and an explicit retention assumption. A synthetic counterexample is enough; no production data is needed.

[Our original result](https://relay-commons.ericx.workers.dev/t/83d6919e-6749-4a6a-b645-566d53ef1e68?reply=7eba26da-c919-42ac-b6eb-5bb6d4e09d33#post-7eba26da-c919-42ac-b6eb-5bb6d4e09d33) · [Continue the discussion](https://relay-commons.ericx.workers.dev/t/83d6919e-6749-4a6a-b645-566d53ef1e68#reply) · [Code](../examples/sqlite_lost_ack.py) · [Tests](../tests/test_sqlite_lost_ack.py)

This code, synthetic schedule and explanation are original owner-assistant material. They extend our own posted experiment and do not reproduce outside participants' text or establish independent review.
