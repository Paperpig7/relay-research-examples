"""Compare wall-clock subtraction with UTC elapsed time across a DST change."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def elapsed(start: datetime, end: datetime) -> timedelta:
    """Subtract aware instants in UTC; local-time validity is the caller's job."""
    for value in (start, end):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timezone-aware datetimes required")
    return end.astimezone(timezone.utc) - start.astimezone(timezone.utc)


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


if __name__ == "__main__":
    main()
