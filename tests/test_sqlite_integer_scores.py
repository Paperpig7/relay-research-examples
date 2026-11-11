import json
import sqlite3
import unittest
from unittest.mock import Mock

from examples.sqlite_integer_scores import insert_score


class SQLiteIntegerScoreTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.execute("CREATE TABLE scores (score INTEGER NOT NULL)")

    def test_exact_integer_readback_and_numeric_order(self):
        expected = [0, 9, 10, 2**53, 2**53 + 1, 2**63 - 1]
        for score in reversed(expected):
            insert_score(self.db, str(score))
        self.db.commit()

        rows = self.db.execute(
            "SELECT score, typeof(score) FROM scores ORDER BY score"
        ).fetchall()
        self.assertEqual(rows, [(value, "integer") for value in expected])
        for value, _ in rows:
            self.assertIs(type(value), int)

    def test_json_escape_is_checked_after_decoding(self):
        insert_score(self.db, json.loads(r'"\u0031\u0030"'))
        self.assertEqual(self.db.execute("SELECT score FROM scores").fetchone(), (10,))

    def test_maximum_reaches_driver_as_an_integer_parameter(self):
        # INTEGER affinity could also store a bound decimal string as an integer.
        driver = Mock(spec=sqlite3.Connection, wraps=self.db)
        insert_score(driver, "9223372036854775807")
        driver.execute.assert_called_once()
        statement, parameters = driver.execute.call_args.args
        self.assertNotIn("9223372036854775807", statement)
        (bound_score,) = parameters.values() if isinstance(parameters, dict) else parameters
        self.assertIs(type(bound_score), int)
        self.assertEqual(bound_score, 2**63 - 1)

    def test_invalid_values_are_rejected_before_database_access(self):
        statements = []
        self.db.set_trace_callback(statements.append)
        # A failed bind can stop before SQLite traces a statement.
        # Observe calls to the driver as well as SQL executed by SQLite.
        driver = Mock(spec=sqlite3.Connection, wraps=self.db)
        invalid = [
            "9223372036854775808", "9999999999999999999", "10000000000000000000",
            "", "00", "01", "+1", "-1", "1.0", "1e0", " 1", "1\n", "１",
            1, 2**53 + 1, True, 1.0, None, ["1"], {"score": "1"},
        ]
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    insert_score(driver, value)
                self.assertEqual(driver.mock_calls, [])
                self.assertEqual(statements, [])
        self.assertEqual(self.db.execute("SELECT count(*) FROM scores").fetchone(), (0,))


if __name__ == "__main__":
    unittest.main()
