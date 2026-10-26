from dataclasses import replace
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from examples.sqlite_lost_ack import (
    Event, acknowledge, confirm, create_receiver, create_sender,
    head, receive, reopen, run_demo,
)


class SQLiteLostAckTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory(prefix="relay-lost-ack-test-")
        self.addCleanup(self.directory.cleanup)
        self.sender_path = Path(self.directory.name) / "sender.sqlite"
        self.receiver_path = Path(self.directory.name) / "receiver.sqlite"
        self.sender = create_sender(self.sender_path)
        self.receiver = create_receiver(self.receiver_path)
        # Lambdas also close replacement connections used by the reopen test.
        self.addCleanup(lambda: self.sender.close())
        self.addCleanup(lambda: self.receiver.close())

    def state(self, db):
        return dict(db.execute("SELECT * FROM state WHERE id=1").fetchone())

    def effects(self):
        return [dict(row) for row in self.receiver.execute("SELECT * FROM effects ORDER BY seq")]

    def test_lost_ack_reopen_and_return_to_a_keep_both_transitions(self):
        first = confirm(self.sender, "B")
        receive(self.receiver, first)
        second = confirm(self.sender, "A")
        self.assertEqual(self.state(self.sender)["ack_seq"], 0)
        self.assertEqual(self.state(self.receiver)["value"], "B")
        self.assertEqual(head(self.sender), first)
        self.sender.close()
        self.receiver.close()
        self.sender, self.receiver = reopen(self.sender_path), reopen(self.receiver_path)
        self.assertEqual(head(self.sender), first)
        acknowledge(self.sender, receive(self.receiver, head(self.sender)))
        self.assertEqual(len(self.effects()), 1)
        self.assertEqual(head(self.sender), second)
        acknowledge(self.sender, receive(self.receiver, head(self.sender)))
        self.assertIsNone(head(self.sender))
        self.assertEqual([(r["old"], r["new"]) for r in self.effects()],
                         [("A", "B"), ("B", "A")])
        self.assertEqual(self.state(self.receiver), {"id": 1, "value": "A", "applied_seq": 2})
        self.assertEqual(self.state(self.sender)["ack_seq"], 2)
        self.assertEqual(self.sender.execute("SELECT COUNT(*) FROM journal").fetchone()[0], 2)

    def test_duplicate_retry_after_later_event_returns_receipt_without_rewind(self):
        first = confirm(self.sender, "B")
        acknowledge(self.sender, receive(self.receiver, first))
        second = confirm(self.sender, "A")
        acknowledge(self.sender, receive(self.receiver, second))
        before = self.state(self.receiver), self.effects()
        self.assertEqual(receive(self.receiver, first), first.event_id)
        acknowledge(self.sender, first.event_id)
        self.assertEqual((self.state(self.receiver), self.effects()), before)
        self.assertEqual(self.state(self.sender)["ack_seq"], 2)

    def test_duplicate_id_with_each_conflicting_field_is_rejected(self):
        first = confirm(self.sender, "B")
        receive(self.receiver, first)
        before = self.state(self.receiver), self.effects()
        for changed in (replace(first, seq=2), replace(first, old="C"), replace(first, new="C")):
            with self.subTest(event=changed):
                with self.assertRaisesRegex(ValueError, "different payload"):
                    receive(self.receiver, changed)
                self.assertEqual((self.state(self.receiver), self.effects()), before)

    def test_same_sequence_with_different_id_is_not_a_new_effect(self):
        first = confirm(self.sender, "B")
        receive(self.receiver, first)
        with self.assertRaisesRegex(ValueError, "noncontiguous"):
            receive(self.receiver, replace(first, event_id="another-id"))
        self.assertEqual(len(self.effects()), 1)

    def test_reordered_delivery_and_wrong_old_value_are_rejected(self):
        first = confirm(self.sender, "B")
        second = confirm(self.sender, "A")
        for bad in (second, replace(first, old="C")):
            with self.subTest(event=bad):
                with self.assertRaisesRegex(ValueError, "noncontiguous"):
                    receive(self.receiver, bad)
        self.assertEqual(self.effects(), [])
        self.assertEqual(self.state(self.receiver)["applied_seq"], 0)

    def test_unknown_and_skipped_acknowledgements_do_not_advance(self):
        first = confirm(self.sender, "B")
        second = confirm(self.sender, "A")
        for receipt in ("unknown", second.event_id):
            with self.subTest(receipt=receipt):
                with self.assertRaises(ValueError):
                    acknowledge(self.sender, receipt)
                self.assertEqual(self.state(self.sender)["ack_seq"], 0)
                self.assertEqual(head(self.sender), first)

    def test_failed_receiver_update_rolls_back_effect_and_receipt(self):
        first = confirm(self.sender, "B")
        self.receiver.execute("""CREATE TRIGGER reject_update BEFORE UPDATE ON state
            BEGIN SELECT RAISE(ABORT, 'synthetic rejection'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            receive(self.receiver, first)
        self.assertEqual(self.effects(), [])
        self.assertEqual(self.state(self.receiver)["value"], "A")
        self.assertFalse(self.receiver.in_transaction)
        self.receiver.execute("DROP TRIGGER reject_update")
        receive(self.receiver, first)
        self.assertEqual(len(self.effects()), 1)

    def test_failed_sender_update_rolls_back_journal_entry(self):
        self.sender.execute("""CREATE TRIGGER reject_update BEFORE UPDATE ON state
            BEGIN SELECT RAISE(ABORT, 'synthetic rejection'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            confirm(self.sender, "B")
        self.assertEqual(self.sender.execute("SELECT COUNT(*) FROM journal").fetchone()[0], 0)
        self.assertEqual(self.state(self.sender)["observed"], "A")
        self.assertFalse(self.sender.in_transaction)

    def test_unchanged_confirmation_does_not_create_an_event(self):
        self.assertIsNone(confirm(self.sender, "A"))
        first = confirm(self.sender, "B")
        self.assertIsNone(confirm(self.sender, "B"))
        self.assertEqual(head(self.sender), first)
        self.assertEqual(self.state(self.sender)["seq"], 1)

    def test_caller_transaction_is_not_silently_committed(self):
        self.sender.execute("BEGIN")
        with self.assertRaisesRegex(ValueError, "already active"):
            confirm(self.sender, "B")
        self.assertTrue(self.sender.in_transaction)
        self.sender.rollback()

    def test_missing_database_is_not_created_and_existing_is_not_overwritten(self):
        missing = Path(self.directory.name) / "missing.sqlite"
        with self.assertRaises(sqlite3.OperationalError):
            reopen(missing)
        self.assertFalse(missing.exists())
        before = self.sender_path.read_bytes()
        with self.assertRaises(FileExistsError):
            create_sender(self.sender_path)
        self.assertEqual(self.sender_path.read_bytes(), before)

    def test_event_contract_rejects_invalid_sequences_values_and_nontransitions(self):
        for seq in (0, -1, True, 1.5, "1"):
            with self.subTest(seq=seq):
                with self.assertRaises(ValueError):
                    Event(seq, "id", "A", "B")
        for args in ((1, "", "A", "B"), (1, "id", None, "B"), (1, "id", "A", "A")):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    Event(*args)
        with self.assertRaises(ValueError):
            confirm(self.sender, 1)
        with self.assertRaises(TypeError):
            receive(self.receiver, {"seq": 1})

    def test_demo_reports_attempts_not_fictitious_extra_effects(self):
        result = run_demo()
        self.assertEqual(result["delivery_attempt_sequences"], [1, 1, 2])
        self.assertEqual(len(result["committed_effects"]), 2)
        self.assertEqual(result["receiver"], {"value": "A", "applied_seq": 2})
        self.assertTrue(result["temporary_databases_removed_on_return"])


if __name__ == "__main__":
    unittest.main()
