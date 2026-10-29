from dataclasses import FrozenInstanceError
from fractions import Fraction
from itertools import product
import unittest

from examples.nonresponse_bounds import KnownResponses


class NonresponseBoundsTests(unittest.TestCase):
    def test_original_consultation_and_follow_up(self):
        initial = KnownResponses(1000, 60, 40)
        self.assertEqual(initial.bounds, (Fraction(6, 100), Fraction(96, 100)))
        self.assertEqual(initial.unknown, 900)
        later = initial.follow_up(support=50, oppose=30)
        self.assertEqual((later.support, later.oppose, later.unknown), (110, 70, 820))
        self.assertEqual(later.bounds, (Fraction(11, 100), Fraction(93, 100)))
        self.assertEqual((initial.width, later.width), (Fraction(9, 10), Fraction(82, 100)))
        plug_in = (initial.support + initial.unknown * Fraction(50, 80)) / initial.population
        self.assertEqual(plug_in, Fraction(249, 400))
        self.assertNotEqual(later.bounds, (plug_in, plug_in))

    def test_all_completions_small_populations_attain_both_endpoints(self):
        # Enumerate actual binary assignments, independently of the formula.
        for population in range(1, 8):
            for support in range(population + 1):
                for oppose in range(population - support + 1):
                    known = [1] * support + [0] * oppose
                    unknown = population - len(known)
                    possible = {
                        Fraction(sum(known + list(answers)), population)
                        for answers in product((0, 1), repeat=unknown)
                    }
                    counts = KnownResponses(population, support, oppose)
                    with self.subTest(population=population, support=support, oppose=oppose):
                        self.assertEqual(counts.bounds, (min(possible), max(possible)))
                        self.assertTrue(all(counts.bounds[0] <= p <= counts.bounds[1] for p in possible))
                        self.assertEqual(len(possible), unknown + 1)

    def test_all_valid_small_follow_ups_narrow_bounds_by_observed_count(self):
        for population in range(1, 8):
            for support in range(population + 1):
                for oppose in range(population - support + 1):
                    initial = KnownResponses(population, support, oppose)
                    for new_support in range(initial.unknown + 1):
                        for new_oppose in range(initial.unknown - new_support + 1):
                            later = initial.follow_up(support=new_support, oppose=new_oppose)
                            with self.subTest(initial=initial, new_support=new_support, new_oppose=new_oppose):
                                self.assertLessEqual(initial.bounds[0], later.bounds[0])
                                self.assertLessEqual(later.bounds[0], later.bounds[1])
                                self.assertLessEqual(later.bounds[1], initial.bounds[1])
                                self.assertEqual(initial.width - later.width,
                                                 Fraction(new_support + new_oppose, population))

    def test_no_answers_and_all_known_boundaries(self):
        self.assertEqual(KnownResponses(10, 0, 0).bounds, (Fraction(0), Fraction(1)))
        self.assertEqual(KnownResponses(10, 0, 10).bounds, (Fraction(0), Fraction(0)))
        self.assertEqual(KnownResponses(10, 10, 0).bounds, (Fraction(1), Fraction(1)))
        self.assertEqual(KnownResponses(10, 6, 4).bounds, (Fraction(3, 5), Fraction(3, 5)))
        self.assertEqual(KnownResponses(1, 0, 0).follow_up(support=1, oppose=0).width, 0)

    def test_unanswered_invitations_do_not_narrow_bounds(self):
        initial = KnownResponses(1000, 60, 40)
        self.assertEqual(initial.follow_up(support=0, oppose=0), initial)

    def test_follow_up_is_immutable_and_additions_commute(self):
        initial = KnownResponses(20, 2, 3)
        first = initial.follow_up(support=4, oppose=1).follow_up(support=1, oppose=2)
        reverse = initial.follow_up(support=1, oppose=2).follow_up(support=4, oppose=1)
        self.assertEqual(first, reverse)
        self.assertEqual(initial, KnownResponses(20, 2, 3))
        with self.assertRaises(FrozenInstanceError):
            initial.support = 10

    def test_counts_larger_than_float_precision_remain_exact(self):
        n = 10 ** 30 + 7
        counts = KnownResponses(n, n - 2, 1)
        self.assertEqual(counts.bounds, (Fraction(n - 2, n), Fraction(n - 1, n)))
        self.assertEqual(counts.width, Fraction(1, n))
        self.assertLess(counts.bounds[0], counts.bounds[1])

    def test_invalid_population_and_inconsistent_counts(self):
        for values in ((0, 0, 0), (-1, 0, 0), (10, -1, 0), (10, 0, -1), (10, 6, 5)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                KnownResponses(*values)

    def test_non_integer_counts_and_bools_are_not_coerced(self):
        for bad in (True, False, 1.0, "1", Fraction(1), None):
            for position in range(3):
                values = [10, 1, 1]
                values[position] = bad
                with self.subTest(values=values), self.assertRaises(TypeError):
                    KnownResponses(*values)

    def test_follow_up_rejects_invalid_or_excess_answers(self):
        initial = KnownResponses(10, 6, 3)
        for values in ((2, 0), (0, 2), (1, 1), (-1, 0), (0, -1)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                initial.follow_up(support=values[0], oppose=values[1])
        for bad in (True, False, 1.0, "1", Fraction(1), None):
            for support, oppose in ((bad, 0), (0, bad)):
                with self.subTest(support=support, oppose=oppose), self.assertRaises(TypeError):
                    initial.follow_up(support=support, oppose=oppose)
        with self.assertRaises(ValueError):
            KnownResponses(10, 6, 4).follow_up(support=1, oppose=0)


if __name__ == "__main__":
    unittest.main()
