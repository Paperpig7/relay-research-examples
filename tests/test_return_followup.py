import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from examples.return_followup import Post, Receipt, classify


START = datetime(2026, 11, 18, tzinfo=timezone.utc)
DAY = timedelta(days=1)
TICK = timedelta(microseconds=1)
END = START + 3 * DAY


class FollowupTests(unittest.TestCase):
    def test_observed_return_at_early_report_cutoff(self):
        receipt = Receipt("A", START, None)
        post = Post("A", START + DAY, False)
        self.assertEqual(classify(receipt, [post], START + DAY), "returned")

    def test_later_post_cannot_answer_an_earlier_report(self):
        receipt = Receipt("A", START, START + DAY)
        post = Post("A", START + DAY + TICK, False)
        self.assertEqual(classify(receipt, [post], START + DAY), "unresolved")

    def test_return_window_starts_strictly_after_receipt_and_includes_hour_72(self):
        receipt = Receipt("A", START, END + DAY)
        cases = (
            (START - TICK, "no return"),
            (START, "no return"),
            (START + TICK, "returned"),
            (END, "returned"),
            (END + TICK, "no return"),
        )
        for at, expected in cases:
            with self.subTest(at=at):
                self.assertEqual(classify(receipt, [Post("A", at, False)], END + DAY), expected)

    def test_negative_requires_complete_observation(self):
        for coverage, expected in ((None, "unresolved"), (END - TICK, "unresolved"), (END, "no return")):
            with self.subTest(covered_through=coverage):
                self.assertEqual(classify(Receipt("A", START, coverage), [], END), expected)

    def test_wrong_subject_and_outstanding_request_do_not_count(self):
        receipt = Receipt("A", START, END)
        posts = [Post("B", START + DAY, False), Post("A", START + DAY, True)]
        self.assertEqual(classify(receipt, posts, END), "no return")

    def test_unknown_request_state_can_leave_even_a_complete_window_unresolved(self):
        unknown = Post("A", START + DAY, None)
        clear = Post("A", START + 2 * DAY, False)
        receipt = Receipt("A", START, END)
        self.assertEqual(classify(receipt, [unknown], END), "unresolved")
        for posts in ([unknown, clear], [clear, unknown]):
            with self.subTest(posts=posts):
                self.assertEqual(classify(receipt, posts, END), "returned")

    def test_72_elapsed_hours_across_fall_clock_change(self):
        chicago = ZoneInfo("America/Chicago")
        start = datetime(2026, 10, 31, 12, tzinfo=chicago)
        end = datetime(2026, 11, 3, 11, tzinfo=chicago)
        receipt = Receipt("A", start, end + DAY)
        self.assertEqual(classify(receipt, [Post("A", end, False)], end + DAY), "returned")
        self.assertEqual(classify(receipt, [Post("A", end + TICK, False)], end + DAY), "no return")

    def test_invalid_request_state_and_coverage(self):
        with self.assertRaises(ValueError):
            Post("A", START + DAY, "false")
        with self.assertRaises(ValueError):
            classify(Receipt("A", START, START - TICK), [], END)

    def test_report_before_receipt_is_invalid(self):
        with self.assertRaises(ValueError):
            classify(Receipt("A", START, None), [], START - TICK)

    def test_naive_timestamps_rejected(self):
        naive = START.replace(tzinfo=None)
        cases = (
            (naive, END, START + DAY, END),
            (START, naive, START + DAY, END),
            (START, END, naive, END),
            (START, END, START + DAY, naive),
        )
        for start, covered, posted, report in cases:
            with self.subTest(case=(start, covered, posted, report)), self.assertRaises(ValueError):
                classify(Receipt("A", start, covered), [Post("A", posted, False)], report)


if __name__ == "__main__":
    unittest.main()
