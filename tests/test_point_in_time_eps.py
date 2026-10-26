from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext
from itertools import permutations
import unittest

from examples.point_in_time_eps import (
    CASES, VERSIONS, EpsVersion, example_results, select_as_of, timestamp, toy_lower_pe,
)


class PointInTimeEPSTests(unittest.TestCase):
    def test_eleven_publication_capture_and_amendment_boundaries(self):
        for name, decision, expected in CASES:
            with self.subTest(case=name):
                selected = select_as_of(VERSIONS, timestamp(decision))
                self.assertEqual(selected.version_id if selected else None, expected)

    def test_every_input_permutation_preserves_all_eleven_answers(self):
        for ordering in permutations(VERSIONS):
            for name, decision, expected in CASES:
                with self.subTest(order=[r.version_id for r in ordering], case=name):
                    selected = select_as_of(ordering, timestamp(decision))
                    self.assertEqual(selected.version_id if selected else None, expected)

    def test_future_amendment_value_cannot_change_past_selection(self):
        cutoff = timestamp("2026-04-30T20:07:00Z")
        amended = VERSIONS[:2] + (replace(VERSIONS[2], eps=Decimal(999)),)
        self.assertEqual(select_as_of(amended, cutoff), VERSIONS[1])

    def test_future_amendment_presence_cannot_change_past_selection(self):
        cutoff = timestamp("2026-04-30T20:07:00Z")
        self.assertEqual(select_as_of(VERSIONS[:2], cutoff), select_as_of(VERSIONS, cutoff))

    def test_period_end_negative_control_uses_unavailable_version(self):
        selected = select_as_of(VERSIONS, timestamp("2026-03-31T20:00:00Z"))
        self.assertEqual(toy_lower_pe(selected.eps), "B")
        self.assertEqual(toy_lower_pe(VERSIONS[1].eps), "A")

    def test_information_change_can_change_selection_with_fixed_prices(self):
        before = select_as_of(VERSIONS, timestamp("2026-04-30T20:06:59Z"))
        at = select_as_of(VERSIONS, timestamp("2026-04-30T20:07:00Z"))
        self.assertEqual((toy_lower_pe(before.eps), toy_lower_pe(at.eps)), ("B", "A"))

    def test_processing_delay_has_an_exact_boundary(self):
        delay = timedelta(seconds=30)
        before = timestamp("2026-04-30T20:07:29.999999Z")
        at = timestamp("2026-04-30T20:07:30Z")
        self.assertEqual(select_as_of(VERSIONS, before, processing_delay=delay), VERSIONS[0])
        self.assertEqual(select_as_of(VERSIONS, at, processing_delay=delay), VERSIONS[1])

    def test_far_future_row_does_not_overflow_or_change_a_past_selection(self):
        cutoff = timestamp("2026-04-30T20:07:30Z")
        delay = timedelta(seconds=30)
        future = replace(VERSIONS[2], version_id="far-future",
                         public_at=datetime.max.replace(tzinfo=timezone.utc),
                         first_seen_at=datetime.max.replace(tzinfo=timezone.utc))
        self.assertEqual(select_as_of(VERSIONS + (future,), cutoff, processing_delay=delay),
                         select_as_of(VERSIONS, cutoff, processing_delay=delay))

    def test_huge_valid_processing_delay_returns_no_eligible_version(self):
        self.assertIsNone(select_as_of(
            VERSIONS, datetime.max.replace(tzinfo=timezone.utc),
            processing_delay=timedelta.max,
        ))

    def test_capture_before_publication_does_not_allow_early_selection(self):
        row = replace(VERSIONS[1], first_seen_at=timestamp("2026-04-30T20:00:00Z"))
        self.assertIsNone(select_as_of([row], timestamp("2026-04-30T20:04:59Z")))
        self.assertEqual(select_as_of([row], row.public_at), row)

    def test_late_arriving_older_publication_does_not_overwrite_newer_version(self):
        late = replace(VERSIONS[0], first_seen_at=timestamp("2026-05-16T12:00:00Z"))
        selected = select_as_of((VERSIONS[2], late, VERSIONS[1]), late.first_seen_at)
        self.assertEqual(selected, VERSIONS[2])

    def test_equal_publication_times_have_explicit_stable_id_tie_break(self):
        a = replace(VERSIONS[1], version_id="tie-a")
        b = replace(VERSIONS[1], version_id="tie-b", eps=Decimal(7))
        for rows in ((a, b), (b, a)):
            self.assertEqual(select_as_of(rows, a.first_seen_at), b)

    def test_missing_history_returns_none_and_generators_work(self):
        cutoff = timestamp("2026-06-01T00:00:00Z")
        self.assertIsNone(select_as_of([], cutoff))
        self.assertEqual(select_as_of((r for r in VERSIONS), cutoff), VERSIONS[2])

    def test_timezone_offsets_represent_the_same_instant(self):
        utc = timestamp("2026-04-30T20:07:00Z")
        offset = timestamp("2026-04-30T16:07:00-04:00")
        self.assertEqual(utc, offset)
        self.assertEqual(select_as_of(VERSIONS, utc), select_as_of(VERSIONS, offset))
        row = replace(VERSIONS[1], public_at=datetime(2026, 4, 30, 16, 5,
                      tzinfo=timezone(timedelta(hours=-4))))
        self.assertEqual(row.public_at, VERSIONS[1].public_at)

    def test_naive_dates_do_not_silently_inherit_the_machine_timezone(self):
        naive = datetime(2026, 4, 30, 20, 7)
        for operation in (
            lambda: timestamp("2026-04-30"),
            lambda: timestamp("2026-04-30T20:07:00"),
            lambda: select_as_of(VERSIONS, naive),
            lambda: replace(VERSIONS[1], public_at=naive),
            lambda: replace(VERSIONS[1], first_seen_at=naive),
        ):
            with self.assertRaises(ValueError):
                operation()

    def test_duplicate_version_ids_rejected_instead_of_order_sensitive_choice(self):
        cutoff = timestamp("2026-06-01T00:00:00Z")
        for rows in ([VERSIONS[1], VERSIONS[1]],
                     [VERSIONS[1], replace(VERSIONS[1], eps=Decimal(100))]):
            with self.assertRaises(ValueError):
                select_as_of(rows, cutoff)

    def test_versions_are_immutable_and_selection_does_not_mutate_input(self):
        with self.assertRaises(FrozenInstanceError):
            VERSIONS[1].eps = Decimal(99)
        rows = list(reversed(VERSIONS))
        original = rows[:]
        select_as_of(rows, timestamp("2026-06-01T00:00:00Z"))
        self.assertEqual(rows, original)

    def test_invalid_types_and_negative_processing_delays_rejected(self):
        for operation in (
            lambda: timestamp(datetime.now(timezone.utc)),
            lambda: select_as_of(VERSIONS, "2026-01-01T00:00:00Z"),
            lambda: select_as_of([{}], timestamp("2026-01-01T00:00:00Z")),
            lambda: select_as_of(VERSIONS, timestamp("2026-01-01T00:00:00Z"), processing_delay=1),
            lambda: replace(VERSIONS[0], eps=2.0),
            lambda: replace(VERSIONS[0], period_end=datetime(2025, 12, 31)),
            lambda: replace(VERSIONS[0], period_end="2025-12-31"),
        ):
            with self.assertRaises(TypeError):
                operation()
        with self.assertRaises(ValueError):
            select_as_of(VERSIONS, timestamp("2026-01-01T00:00:00Z"),
                         processing_delay=timedelta(microseconds=-1))

    def test_nonfinite_eps_and_empty_identifiers_rejected(self):
        for value in ("NaN", "sNaN", "Infinity", "-Infinity"):
            with self.assertRaises(ValueError):
                replace(VERSIONS[0], eps=Decimal(value))
        for value in ("", " ", None):
            with self.assertRaises(ValueError):
                replace(VERSIONS[0], version_id=value)

    def test_selector_preserves_zero_or_negative_eps_without_ranking_it(self):
        for value in (Decimal(0), Decimal(-1)):
            row = replace(VERSIONS[0], eps=value)
            self.assertEqual(select_as_of([row], row.first_seen_at).eps, value)
            with self.assertRaises(ValueError):
                toy_lower_pe(value)

    def test_toy_ranking_rejects_nonfinite_and_float_inputs(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.assertRaises(ValueError):
                toy_lower_pe(Decimal(value))
        with self.assertRaises(TypeError):
            toy_lower_pe(3.0)

    def test_toy_ranking_does_not_modify_callers_decimal_context(self):
        with localcontext() as context:
            context.prec = 3
            self.assertEqual(toy_lower_pe(Decimal(4)), "A")
            self.assertEqual(context.prec, 3)

    def test_toy_ranking_does_not_round_near_ties_into_ties(self):
        with localcontext() as context:
            context.prec = 3
            self.assertEqual(toy_lower_pe(Decimal("2." + "9" * 60)), "B")
            self.assertEqual(toy_lower_pe(Decimal("3." + "0" * 60 + "1")), "A")
            self.assertEqual(toy_lower_pe(Decimal(3)), "A")

    def test_example_results_are_repeatable_and_state_the_scope(self):
        first = example_results()
        self.assertEqual(first, example_results())
        self.assertTrue(first["synthetic"])
        self.assertEqual(first["timestamp_cases_passed"], 11)
        self.assertEqual(first["lower_pe_before_capture"], "B")
        self.assertEqual(first["lower_pe_at_capture"], "A")


if __name__ == "__main__":
    unittest.main()
