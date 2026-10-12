from contextlib import closing
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from examples.sqlite_recovery_check import EXPECTED_CASES, create_fixture, inspect_fixture


class SQLiteRecoveryCheckTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory(prefix="relay-sqlite-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def fixture(self, name="complete"):
        path = self.root / (name + ".sqlite")
        create_fixture(path, name)
        return path

    def edit(self, path, statements):
        with closing(sqlite3.connect(path)) as connection:
            with connection:
                connection.executescript(statements)

    def test_five_cases_open_but_only_two_meet_the_predicate(self):
        for case, expected in EXPECTED_CASES.items():
            path = self.fixture(case)
            before = path.read_bytes()
            files_before = sorted(self.root.iterdir())
            result = inspect_fixture(path)
            with self.subTest(case=case):
                self.assertTrue(result.opened)
                self.assertEqual(result.decision, expected)
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(sorted(self.root.iterdir()), files_before)

    def test_missing_database_rejected_without_creating_anything(self):
        path = self.root / "not-created.sqlite"
        result = inspect_fixture(path)
        self.assertFalse(result.opened)
        self.assertEqual(result.decision, "REJECT")
        self.assertFalse(path.exists())
        self.assertEqual(list(self.root.iterdir()), [])

    def test_uri_punctuation_in_filename_is_not_interpreted_as_parameters(self):
        path = self.root / "fixture ?#&=.sqlite"
        create_fixture(path, "complete")
        self.assertEqual(inspect_fixture(path).decision, "PASS")

    def test_wrong_version_rejected(self):
        path = self.fixture()
        self.edit(path, "PRAGMA user_version=2;")
        self.assertIn("user_version differs", inspect_fixture(path).reasons)

    def test_required_view_is_not_accepted_as_a_table(self):
        path = self.fixture()
        self.edit(path, "DROP TABLE audit; CREATE VIEW audit AS SELECT 'T' AS task_id,'restored' AS event;")
        self.assertEqual(inspect_fixture(path).decision, "REJECT")

    def test_schema_mismatch_rejected_even_with_correct_rows(self):
        path = self.fixture()
        self.edit(path, "DROP TABLE audit; CREATE TABLE audit(task_id TEXT PRIMARY KEY,event TEXT); INSERT INTO audit VALUES('T','restored');")
        self.assertIn("audit column schema differs", inspect_fixture(path).reasons)

    def test_generated_extra_column_is_not_hidden_from_checker(self):
        path = self.fixture()
        self.edit(path, "ALTER TABLE tasks ADD COLUMN generated_status TEXT GENERATED ALWAYS AS (status) VIRTUAL;")
        self.assertIn("tasks column schema differs", inspect_fixture(path).reasons)

    def test_extra_or_missing_required_rows_rejected(self):
        path = self.fixture()
        self.edit(path, "INSERT INTO tasks VALUES('U','ready');")
        self.assertIn("tasks row set differs", inspect_fixture(path).reasons)
        self.edit(path, "DELETE FROM tasks;")
        self.assertIn("tasks row set differs", inspect_fixture(path).reasons)

    def test_corrupt_file_is_not_repaired(self):
        path = self.root / "corrupt.sqlite"
        contents = b"not a sqlite database"
        path.write_bytes(contents)
        self.assertEqual(inspect_fixture(path).decision, "REJECT")
        self.assertEqual(path.read_bytes(), contents)

    def test_fixture_creation_refuses_to_overwrite(self):
        path = self.fixture()
        original = path.read_bytes()
        with self.assertRaises(FileExistsError):
            create_fixture(path, "wrong_values")
        self.assertEqual(path.read_bytes(), original)

    def test_unknown_fixture_name_creates_no_file(self):
        path = self.root / "unknown.sqlite"
        with self.assertRaises(ValueError):
            create_fixture(path, "typo")
        self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
