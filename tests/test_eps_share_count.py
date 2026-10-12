from decimal import Decimal, localcontext
import unittest

from examples.eps_share_count import basic_eps, weighted_average_shares


class EPSShareCountTests(unittest.TestCase):
    def test_fixed_earnings_with_smaller_full_period_denominator(self):
        earnings = Decimal("100000000")
        before = basic_eps(earnings, Decimal("100000000"))
        after = basic_eps(earnings, Decimal("80000000"))
        self.assertEqual(before, Decimal(1))
        self.assertEqual(after, Decimal("1.25"))
        self.assertEqual((after / before - 1) * 100, Decimal(25))

    def test_half_period_buyback_does_not_use_ending_shares(self):
        average = weighted_average_shares([
            (Decimal("100000000"), Decimal(1)),
            (Decimal("80000000"), Decimal(1)),
        ])
        self.assertEqual(average, Decimal("90000000"))
        self.assertEqual(basic_eps(Decimal("100000000"), average).quantize(Decimal("0.000001")), Decimal("1.111111"))
        self.assertNotEqual(basic_eps(Decimal("100000000"), average), Decimal("1.25"))

    def test_consistent_time_units_and_reordering_do_not_change_average(self):
        periods = [(Decimal(100), Decimal(3)), (Decimal(80), Decimal(1))]
        self.assertEqual(weighted_average_shares(periods), Decimal(95))
        self.assertEqual(weighted_average_shares(reversed(periods)), Decimal(95))
        self.assertEqual(weighted_average_shares([(s, w * 30) for s, w in periods]), Decimal(95))

    def test_zero_duration_does_not_change_denominator(self):
        self.assertEqual(weighted_average_shares([(Decimal(100), Decimal(1)), (Decimal(50), Decimal(0))]), Decimal(100))

    def test_negative_earnings_are_not_a_positive_eps_improvement(self):
        self.assertEqual(basic_eps(Decimal(-100), Decimal(100)), Decimal(-1))
        self.assertEqual(basic_eps(Decimal(-100), Decimal(80)), Decimal("-1.25"))
        self.assertEqual(basic_eps(Decimal(0), Decimal(80)), Decimal(0))

    def test_invalid_or_empty_share_periods_rejected(self):
        for periods in ([], [(Decimal(1), Decimal(0))], [(Decimal(0), Decimal(1))], [(Decimal(-1), Decimal(1))], [(Decimal(1), Decimal(-1))]):
            with self.subTest(periods=periods), self.assertRaises(ValueError):
                weighted_average_shares(periods)
        for shares in (Decimal(0), Decimal(-1)):
            with self.assertRaises(ValueError):
                basic_eps(Decimal(100), shares)

    def test_invalid_numbers_and_binary_float_inputs_rejected(self):
        for number in (Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity")):
            for operation in (
                lambda: basic_eps(number, Decimal(1)),
                lambda: basic_eps(Decimal(1), number),
                lambda: weighted_average_shares([(number, Decimal(1))]),
                lambda: weighted_average_shares([(Decimal(1), number)]),
            ):
                with self.subTest(number=number), self.assertRaises(ValueError):
                    operation()
        for operation in (lambda: basic_eps(100.0, Decimal(100)), lambda: weighted_average_shares([(Decimal(1), 1.0)])):
            with self.assertRaises(TypeError):
                operation()

    def test_does_not_change_callers_decimal_precision(self):
        with localcontext() as context:
            context.prec = 3
            self.assertEqual(basic_eps(Decimal(100), Decimal(90)).quantize(Decimal("0.01")), Decimal("1.11"))
            self.assertEqual(context.prec, 3)


if __name__ == "__main__":
    unittest.main()
