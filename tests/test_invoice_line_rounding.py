"""Regression checks for the two worked invoice lines."""

import json
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from io import StringIO

from examples.invoice_line_rounding import FIXTURE, _amounts, main


class InvoiceLineRoundingTests(unittest.TestCase):
    def setUp(self):
        self.cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.lines = [_amounts(case["quantity"], case["unit_price"]) for case in self.cases]

    def test_fixture_expected_cents(self):
        self.assertEqual([(row["quantity"], row["unit_price"]) for row in self.cases],
                         [(3, "0.345"), (3, "0.335")])
        for case, line in zip(self.cases, self.lines):
            with self.subTest(case=case):
                self.assertIs(type(case["quantity"]), int)
                self.assertIs(type(case["half_up_cents"]), int)
                self.assertIs(type(case["half_even_cents"]), int)
                self.assertEqual(line.half_up * 100, case["half_up_cents"])
                self.assertEqual(line.half_even * 100, case["half_even_cents"])

    def test_unit_first_controls(self):
        self.assertEqual([line.unit_first_up * 100 for line in self.lines], [105, 102])
        self.assertEqual([line.unit_first_even * 100 for line in self.lines], [102, 102])

    def test_binary_rounding_disagreements_cancel(self):
        binary_cents = [Decimal(str(line.binary)) * 100 for line in self.lines]
        even_cents = [line.half_even * 100 for line in self.lines]
        self.assertEqual(binary_cents, [103, 101])
        self.assertEqual(even_cents, [104, 100])
        self.assertEqual(sum(binary_cents), sum(even_cents))

    def test_line_and_combined_totals(self):
        output = StringIO()
        with redirect_stdout(output):
            main()
        self.assertIn("Sum of rounded lines: half-up 2.05, half-even 2.04.", output.getvalue())
        self.assertIn("2.040 -> 2.04 (half-up), 2.04 (half-even).", output.getvalue())
