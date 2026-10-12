from decimal import Decimal, localcontext
from itertools import permutations
import unittest

from examples.deterministic_ranking import Candidate, rank_candidates


class DeterministicRankingTests(unittest.TestCase):
    def test_ties_and_missing_values_are_permutation_invariant(self):
        records = [Candidate("z", None), Candidate("b", Decimal("0.8")), Candidate("a", Decimal("0.80")), Candidate("d", Decimal(-1))]
        for order in permutations(records):
            self.assertEqual([record.id for record in rank_candidates(order)], ["a", "b", "d", "z"])

    def test_all_missing_and_empty_inputs(self):
        self.assertEqual([record.id for record in rank_candidates([Candidate("z", None), Candidate("a", None)])], ["a", "z"])
        self.assertEqual(rank_candidates([]), [])

    def test_zero_and_missing_are_distinct(self):
        ranked = rank_candidates([Candidate("a", None), Candidate("b", Decimal(0)), Candidate("c", Decimal(-1))])
        self.assertEqual([record.id for record in ranked], ["b", "c", "a"])

    def test_tie_order_is_case_sensitive_unicode_lexicographic(self):
        ids = ["中", "a", "A", "é"]
        records = [Candidate(identifier, Decimal(1)) for identifier in ids]
        self.assertEqual([record.id for record in rank_candidates(records)], ["A", "a", "é", "中"])

    def test_duplicate_ids_rejected_even_when_scores_differ(self):
        with self.assertRaises(ValueError):
            rank_candidates([Candidate("same", Decimal(1)), Candidate("same", None)])

    def test_invalid_ids_rejected(self):
        for identifier in ("", " ", " a", "a\n"):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                rank_candidates([Candidate(identifier, Decimal(1))])
        with self.assertRaises(TypeError):
            rank_candidates([Candidate(1, Decimal(1))])

    def test_nonfinite_or_unsupported_scores_rejected(self):
        for score in (Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity")):
            with self.subTest(score=score), self.assertRaises(ValueError):
                rank_candidates([Candidate("a", score)])
        for score in (0.8, 1, True, "0.8"):
            with self.subTest(score=score), self.assertRaises(TypeError):
                rank_candidates([Candidate("a", score)])
        with self.assertRaises(TypeError):
            rank_candidates([{"id": "a", "score": Decimal(1)}])

    def test_sorting_does_not_round_scores_under_low_decimal_precision(self):
        records = [Candidate("a", Decimal("1.000000000000001")), Candidate("z", Decimal("1.000000000000002"))]
        with localcontext() as context:
            context.prec = 3
            self.assertEqual([record.id for record in rank_candidates(records)], ["z", "a"])

    def test_input_records_and_order_are_preserved(self):
        records = [Candidate("b", Decimal(1)), Candidate("a", Decimal(1))]
        original = records.copy()
        result = rank_candidates(records)
        self.assertEqual(records, original)
        self.assertIsNot(result, records)
        self.assertIs(result[0], records[1])


if __name__ == "__main__":
    unittest.main()
