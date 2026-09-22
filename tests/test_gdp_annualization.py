import unittest
from decimal import Decimal, localcontext

from examples.gdp_annualization import annual_average_percent, annualized_percent, growth_from_levels, quarterly_percent


class GDPAnnualizationTests(unittest.TestCase):
    def test_one_percent_quarter_is_4060401_percent_annualized(self):
        growth = growth_from_levels(Decimal("100"), Decimal("101"))
        self.assertEqual(growth, Decimal("1"))
        self.assertEqual(annualized_percent(growth), Decimal("4.060401"))

    def test_four_percent_annualized_is_less_than_one_percent_quarterly(self):
        result = quarterly_percent(Decimal("4"))
        self.assertEqual(result.quantize(Decimal("0.0001")), Decimal("0.9853"))

    def test_contraction_and_boundary(self):
        self.assertEqual(annualized_percent(Decimal("-1")), Decimal("-3.940399"))
        self.assertEqual(annualized_percent(Decimal("-100")), Decimal("-100"))
        self.assertEqual(quarterly_percent(Decimal("-100")), Decimal("-100"))

    def test_zero_and_inverse_round_trips(self):
        for value in ("0", "1", "-1", "10", "-90"):
            with self.subTest(value=value), localcontext() as ctx:
                ctx.prec = 40
                original = Decimal(value)
                recovered = quarterly_percent(annualized_percent(original))
                self.assertLess(abs(recovered - original), Decimal("1e-35"))

    def test_annualized_level_multiplier_cancels_in_ratio(self):
        self.assertEqual(
            growth_from_levels(Decimal("25"), Decimal("25.25")),
            growth_from_levels(Decimal("100"), Decimal("101")),
        )

    def test_flat_later_quarters_do_not_realize_annualized_first_quarter(self):
        levels = [Decimal(v) for v in ("100", "101", "101", "101", "101")]
        growth = [growth_from_levels(a, b) for a, b in zip(levels, levels[1:])]
        self.assertEqual(growth, [Decimal("1"), Decimal("0"), Decimal("0"), Decimal("0")])
        self.assertEqual(growth_from_levels(levels[0], levels[-1]), Decimal("1"))

    def test_invalid_growth_is_rejected(self):
        for function in (annualized_percent, quarterly_percent):
            for value in ("-100.01", "NaN", "Infinity", "-Infinity"):
                with self.subTest(function=function.__name__, value=value), self.assertRaises(ValueError):
                    function(Decimal(value))

    def test_invalid_levels_are_rejected(self):
        for previous, current in (("0", "1"), ("-1", "1"), ("1", "-1"), ("1", "NaN")):
            with self.subTest(previous=previous, current=current), self.assertRaises(ValueError):
                growth_from_levels(Decimal(previous), Decimal(current))

    def test_binary_float_inputs_are_not_silently_converted(self):
        with self.assertRaises(TypeError):
            annualized_percent(0.1)


class AnnualAverageTests(unittest.TestCase):
    def test_annual_average_and_q4_growth_can_have_opposite_signs(self):
        previous = [Decimal(v) for v in ("100", "100", "100", "120")]
        current = [Decimal("110")] * 4
        self.assertEqual(annual_average_percent(previous, current).quantize(Decimal("0.000001")), Decimal("4.761905"))
        self.assertEqual(growth_from_levels(previous[-1], current[-1]).quantize(Decimal("0.000001")), Decimal("-8.333333"))

    def test_same_endpoints_do_not_determine_annual_average(self):
        previous = [Decimal("100")] * 4
        early = [Decimal("110")] * 4
        late = [Decimal(v) for v in ("100", "100", "100", "110")]
        self.assertEqual(growth_from_levels(previous[-1], early[-1]), growth_from_levels(previous[-1], late[-1]))
        self.assertEqual(annual_average_percent(previous, early), Decimal("10"))
        self.assertEqual(annual_average_percent(previous, late), Decimal("2.5"))

    def test_common_annual_rate_level_multiplier_cancels(self):
        previous = [Decimal(v) for v in ("25", "26", "27", "28")]
        current = [Decimal(v) for v in ("28", "29", "30", "31")]
        self.assertEqual(
            annual_average_percent(previous, current),
            annual_average_percent([x * 4 for x in previous], [x * 4 for x in current]),
        )

    def test_partial_years_are_not_silently_averaged(self):
        year = [Decimal("100")] * 4
        for incomplete in ([], year[:3], year + [Decimal("100")]):
            for pair in ((incomplete, year), (year, incomplete)):
                with self.subTest(pair=pair), self.assertRaises(ValueError):
                    annual_average_percent(*pair)

    def test_zero_previous_average_and_invalid_levels_rejected(self):
        year = [Decimal("100")] * 4
        with self.assertRaises(ValueError):
            annual_average_percent([Decimal(0)] * 4, year)
        for value in (Decimal("-1"), Decimal("NaN"), Decimal("Infinity")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                annual_average_percent(year, [value] + year[:3])
        with self.assertRaises(TypeError):
            annual_average_percent(year, [100.0] * 4)
        self.assertEqual(annual_average_percent(year, [Decimal(0)] * 4), Decimal("-100"))


if __name__ == "__main__":
    unittest.main()
