import unittest

from examples.sql_null import make_fixture


class SQLNullTests(unittest.TestCase):
    def setUp(self):
        self.connection = make_fixture()

    def tearDown(self):
        self.connection.close()

    def test_comparison_with_null_is_unknown(self):
        self.assertEqual(self.connection.execute("SELECT 7 = NULL, 7 <> NULL").fetchone(), (None, None))

    def test_inequality_drops_missing_values(self):
        result = self.connection.execute("SELECT id FROM sample WHERE value <> 7 ORDER BY id").fetchall()
        self.assertEqual(result, [(2,)])

    def test_explicit_null_branch_keeps_missing_values(self):
        result = self.connection.execute(
            "SELECT id FROM sample WHERE value <> 7 OR value IS NULL ORDER BY id"
        ).fetchall()
        self.assertEqual(result, [(2,), (3,)])

    def test_equals_null_is_not_a_missing_value_test(self):
        self.assertEqual(self.connection.execute("SELECT id FROM sample WHERE value = NULL").fetchall(), [])
        self.assertEqual(self.connection.execute("SELECT id FROM sample WHERE value IS NULL").fetchall(), [(3,)])

    def test_count_value_omits_null_while_count_star_keeps_row(self):
        self.assertEqual(self.connection.execute("SELECT COUNT(*), COUNT(value) FROM sample").fetchone(), (3, 2))


if __name__ == "__main__":
    unittest.main()
