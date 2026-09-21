import unittest
from datetime import datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo

from examples.dst_elapsed import elapsed


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


if __name__ == "__main__":
    unittest.main()
