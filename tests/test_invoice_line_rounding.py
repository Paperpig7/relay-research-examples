"""Regression checks for invoice line rounding and application subtotals."""

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from examples.invoice_line_rounding import FIXTURE, SUBTOTAL_FIXTURE, _amounts, main


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


class InvoiceSubtotalTests(unittest.TestCase):
    def setUp(self):
        self.cases = json.loads(SUBTOTAL_FIXTURE.read_text(encoding="utf-8"))
        self.actual = {
            "split": {"line_cents": [104, 104], "subtotal_cents": 208},
            "merged": {"line_cents": [207], "subtotal_cents": 207},
        }

    def check_file(self, text):
        stdout, stderr = StringIO(), StringIO()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "observed.json"
            path.write_text(text, encoding="utf-8")
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(["--check-subtotals", str(path)])
        return status, stdout.getvalue() + stderr.getvalue()

    def test_split_and_merged_under_both_policies(self):
        self.assertEqual(set(self.cases), {"split", "merged"})
        for name, case in self.cases.items():
            amounts = [row["quantity"] * Decimal(row["unit_price"]) for row in case["lines"]]
            self.assertEqual(amounts, [Decimal("1.035")] * 2 if name == "split" else [Decimal("2.070")])
            self.assertEqual(case["expected"], self.actual[name])
            for policy in (ROUND_HALF_UP, ROUND_HALF_EVEN):
                with self.subTest(case=name, policy=policy):
                    cents = [int(amount.quantize(Decimal(".01"), rounding=policy) * 100) for amount in amounts]
                    self.assertEqual(cents, case["expected"]["line_cents"])
                    self.assertEqual(sum(cents), case["expected"]["subtotal_cents"])
                    rounded_once = sum(amounts).quantize(Decimal(".01"), rounding=policy)
                    self.assertEqual(rounded_once * 100, 207)

    def test_app_outputs_match(self):
        status, message = self.check_file(json.dumps(self.actual))
        self.assertEqual(status, 0, message)

    def test_reported_subtotal_is_checked_even_when_lines_match(self):
        self.actual["split"]["subtotal_cents"] = 207
        status, message = self.check_file(json.dumps(self.actual))
        self.assertNotEqual(status, 0)
        self.assertIn("split.subtotal_cents: expected 208, got 207", message)

    def test_lines_are_checked_even_when_subtotal_matches(self):
        self.actual["split"]["line_cents"] = [103, 105]
        status, message = self.check_file(json.dumps(self.actual))
        self.assertNotEqual(status, 0)
        self.assertIn("split.line_cents: expected [104, 104], got [103, 105]", message)

    def test_only_integer_cent_fields_are_accepted(self):
        for field, value in [("line_cents", [104.0, 104]), ("line_cents", [True, 104]),
                             ("subtotal_cents", 208.0), ("subtotal_cents", "208")]:
            with self.subTest(field=field, value=value):
                case = dict(self.actual["split"], **{field: value})
                status, message = self.check_file(json.dumps(dict(self.actual, split=case)))
                self.assertNotEqual(status, 0)
                self.assertIn("split." + field, message)

    def test_missing_case_and_bad_json(self):
        del self.actual["merged"]
        status, message = self.check_file(json.dumps(self.actual))
        self.assertNotEqual(status, 0)
        self.assertIn("merged", message)
        status, message = self.check_file("{")
        self.assertNotEqual(status, 0)
        self.assertIn("Could not read invoice results", message)
