import unittest
from datetime import datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo

from examples.dst_elapsed import elapsed, local_time_candidates


class NoOffset(tzinfo):
    def utcoffset(self, value):
        return None


class ElapsedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ny = ZoneInfo("America/New_York")

    def test_spring_labels_two_hours_apart_represent_one_elapsed_hour(self):
        start = datetime(2024, 3, 10, 1, 30, tzinfo=self.ny)
        end = datetime(2024, 3, 10, 3, 30, tzinfo=self.ny)
        self.assertEqual(end - start, timedelta(hours=2))
        self.assertEqual(elapsed(start, end), timedelta(hours=1))

    def test_repeated_hour_with_equal_clock_labels_is_one_hour_apart(self):
        early = datetime(2024, 11, 3, 1, 30, tzinfo=self.ny, fold=0)
        late = early.replace(fold=1)
        self.assertEqual(late - early, timedelta(0))
        self.assertEqual(elapsed(early, late), timedelta(hours=1))

    def test_different_zones_can_identify_the_same_instant(self):
        local = datetime(2024, 1, 15, 12, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        utc = datetime(2024, 1, 15, 6, 30, tzinfo=timezone.utc)
        self.assertEqual(elapsed(local, utc), timedelta(0))

    def test_reverse_order_preserves_negative_duration(self):
        start = datetime(2024, 3, 10, 1, 30, tzinfo=self.ny)
        end = datetime(2024, 3, 10, 3, 30, tzinfo=self.ny)
        self.assertEqual(elapsed(end, start), timedelta(hours=-1))

    def test_naive_input_rejected_in_either_position(self):
        naive = datetime(2024, 1, 1)
        aware = naive.replace(tzinfo=timezone.utc)
        for pair in ((naive, aware), (aware, naive)):
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                elapsed(*pair)

    def test_non_none_tzinfo_without_offset_is_still_naive(self):
        invalid = datetime(2024, 1, 1, tzinfo=NoOffset())
        with self.assertRaises(ValueError):
            elapsed(invalid, datetime(2024, 1, 1, tzinfo=timezone.utc))

    def test_zoneinfo_construction_does_not_validate_a_missing_local_time(self):
        missing = datetime(2024, 3, 10, 2, 30, tzinfo=self.ny)
        round_trip = missing.astimezone(timezone.utc).astimezone(self.ny)
        self.assertNotEqual(round_trip.replace(tzinfo=None), missing.replace(tzinfo=None))


class LocalTimeCandidateTests(unittest.TestCase):
    def test_gap_has_no_candidate_for_either_input_fold(self):
        for fold in (0, 1):
            wall = datetime(2024, 3, 10, 2, 30, fold=fold)
            self.assertEqual(local_time_candidates(wall, ZoneInfo("America/New_York")), ())

    def test_fold_returns_two_exact_instants_not_equal_local_labels(self):
        result = local_time_candidates(datetime(2024, 11, 3, 1, 30), ZoneInfo("America/New_York"))
        self.assertEqual(result, (
            datetime(2024, 11, 3, 5, 30, tzinfo=timezone.utc),
            datetime(2024, 11, 3, 6, 30, tzinfo=timezone.utc),
        ))
        self.assertEqual([instant.astimezone(ZoneInfo("America/New_York")).fold for instant in result], [0, 1])

    def test_ordinary_time_is_deduplicated(self):
        self.assertEqual(
            local_time_candidates(datetime(2024, 1, 15, 12), ZoneInfo("America/New_York")),
            (datetime(2024, 1, 15, 17, tzinfo=timezone.utc),),
        )

    def test_lord_howe_fold_is_thirty_minutes_not_one_hour(self):
        result = local_time_candidates(datetime(2024, 4, 7, 1, 45), ZoneInfo("Australia/Lord_Howe"))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1] - result[0], timedelta(minutes=30))

    def test_lord_howe_thirty_minute_gap(self):
        zone = ZoneInfo("Australia/Lord_Howe")
        self.assertEqual(local_time_candidates(datetime(2024, 10, 6, 2, 15), zone), ())
        self.assertEqual(len(local_time_candidates(datetime(2024, 10, 6, 2, 30), zone)), 1)

    def test_apia_skipped_entire_day(self):
        self.assertEqual(local_time_candidates(datetime(2011, 12, 30, 12), ZoneInfo("Pacific/Apia")), ())

    def test_aware_clock_input_and_non_zoneinfo_are_rejected(self):
        with self.assertRaises(ValueError):
            local_time_candidates(datetime(2024, 1, 1, tzinfo=timezone.utc), ZoneInfo("UTC"))
        with self.assertRaises(TypeError):
            local_time_candidates(datetime(2024, 1, 1), timezone.utc)


if __name__ == "__main__":
    unittest.main()
