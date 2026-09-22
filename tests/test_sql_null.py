import unittest

from examples.sql_null import EXCLUSION_QUERIES, make_exclusion_fixture, make_fixture


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


class SQLExclusionTests(unittest.TestCase):
    def results(self, excluded):
        connection = make_exclusion_fixture(excluded)
        try:
            return [connection.execute(query).fetchall() for query in EXCLUSION_QUERIES.values()]
        finally:
            connection.close()

    def test_null_in_exclusion_table_removes_all_not_in_results(self):
        self.assertEqual(self.results((7, None)), [[], [(2, 8), (3, None)], [(2, 8)]])

    def test_removing_exclusion_null_does_not_keep_candidate_null(self):
        self.assertEqual(self.results((7,)), [[(2, 8)], [(2, 8), (3, None)], [(2, 8)]])

    def test_empty_exclusion_subquery_has_no_matches_even_for_candidate_null(self):
        self.assertEqual(self.results(()), [
            [(1, 7), (2, 8), (3, None)],
            [(1, 7), (2, 8), (3, None)],
            [(1, 7), (2, 8)],
        ])

    def test_only_null_exclusions_match_no_equality_rows(self):
        self.assertEqual(self.results((None,)), [[], [(1, 7), (2, 8), (3, None)], [(1, 7), (2, 8)]])

    def test_duplicate_exclusions_do_not_duplicate_candidate_rows(self):
        self.assertEqual(self.results((7, 7, None, None)), self.results((7, None)))


if __name__ == "__main__":
    unittest.main()
