"""Compare wall-clock subtraction with UTC elapsed time across a DST change."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def elapsed(start: datetime, end: datetime) -> timedelta:
    """Subtract aware instants in UTC; local-time validity is the caller's job."""
    for value in (start, end):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timezone-aware datetimes required")
    return end.astimezone(timezone.utc) - start.astimezone(timezone.utc)


def local_time_candidates(wall: datetime, zone: ZoneInfo) -> tuple[datetime, ...]:
    """Return the distinct UTC instants matching an unzoned local clock reading.

    Zero candidates means a gap, one means ordinary time, and two means a
    repeated time. Both folds are examined; the input's fold is not a choice.
    The caller must decide what to do with gaps and repeated times.
    """
    if wall.tzinfo is not None:
        raise ValueError("Pass an unzoned local clock reading")
    if not isinstance(zone, ZoneInfo):
        raise TypeError("Pass a ZoneInfo time zone")
    candidates = set()
    for fold in (0, 1):
        local = wall.replace(tzinfo=zone, fold=fold)
        instant = local.astimezone(timezone.utc)
        round_trip = instant.astimezone(zone)
        if round_trip.replace(tzinfo=None) == wall:
            # Deduplicate UTC instants, not local datetimes: the latter can
            # compare equal even when fold selects two distinct instants.
            candidates.add(instant)
    return tuple(sorted(candidates))


def main() -> None:
    ny = ZoneInfo("America/New_York")
    start = datetime(2024, 3, 10, 1, 30, tzinfo=ny)
    end = datetime(2024, 3, 10, 3, 30, tzinfo=ny)
    print(f"Spring wall-clock difference: {(end - start).total_seconds():.0f} seconds")
    print(f"Spring elapsed time in UTC: {elapsed(start, end).total_seconds():.0f} seconds")

    early = datetime(2024, 11, 3, 1, 30, tzinfo=ny, fold=0)
    late = early.replace(fold=1)
    print(f"Fall wall-clock difference: {(late - early).total_seconds():.0f} seconds")
    print(f"Fall elapsed time in UTC: {elapsed(early, late).total_seconds():.0f} seconds")
    for label, wall in (
        ("Missing spring 02:30", datetime(2024, 3, 10, 2, 30)),
        ("Repeated fall 01:30", datetime(2024, 11, 3, 1, 30)),
    ):
        print(f"{label}: {len(local_time_candidates(wall, ny))} UTC candidates")


if __name__ == "__main__":
    main()
