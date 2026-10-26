"""Original synthetic point-in-time EPS selection; no prices fetched or trades made.

Run from the repository root: python3 -m examples.point_in_time_eps
Python 3.9+; standard library only. Output goes to stdout, never a data file.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable, Optional
import json


def _aware(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("Use a timezone-aware datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("An explicit timezone is required")
    # Normalize before comparisons, including timestamps with different offsets.
    return value.astimezone(timezone.utc)


def timestamp(value: str) -> datetime:
    """Parse an ISO timestamp with an explicit offset; return UTC."""
    if not isinstance(value, str):
        raise TypeError("Use an ISO timestamp string")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    return _aware(parsed)


@dataclass(frozen=True)
class EpsVersion:
    """A version in one already-normalized synthetic TTM EPS series.

    Do not mix issuers, currencies, EPS definitions, or fact series. This example
    does not turn individual quarterly facts into TTM EPS or resolve XBRL facts.
    """

    version_id: str
    eps: Decimal
    period_end: date
    public_at: datetime
    first_seen_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.version_id, str) or not self.version_id.strip():
            raise ValueError("A nonempty, unique version ID is required")
        if not isinstance(self.eps, Decimal):
            raise TypeError("EPS must be a Decimal")
        if not self.eps.is_finite():
            raise ValueError("EPS must be finite")
        if not isinstance(self.period_end, date) or isinstance(self.period_end, datetime):
            raise TypeError("period_end must be a date, not an availability timestamp")
        object.__setattr__(self, "public_at", _aware(self.public_at))
        object.__setattr__(self, "first_seen_at", _aware(self.first_seen_at))


def select_as_of(
    versions: Iterable[EpsVersion],
    decision: datetime,
    *,
    processing_delay: timedelta = timedelta(0),
) -> Optional[EpsVersion]:
    """Select the latest-published eligible version under this fixture's rule.

    Eligibility is max(public_at, first_seen_at) + processing_delay <= decision.
    Equality is eligible. Equal publication times use lexicographic version ID
    as a deterministic fixture tie-break, NOT a claim about source precedence.
    Duplicate IDs are rejected, even if their values happen to match.
    """
    cutoff = _aware(decision)
    if not isinstance(processing_delay, timedelta):
        raise TypeError("processing_delay must be a timedelta")
    if processing_delay < timedelta(0):
        raise ValueError("processing_delay cannot be negative")
    seen_ids = set()
    eligible = []
    for version in versions:
        if not isinstance(version, EpsVersion):
            raise TypeError("Every row must be an EpsVersion")
        if version.version_id in seen_ids:
            raise ValueError("Duplicate version ID: " + version.version_id)
        seen_ids.add(version.version_id)
        base = max(version.public_at, version.first_seen_at)
        # Comparing elapsed time avoids overflowing datetime.max for an
        # ineligible future row or a large, otherwise valid processing delay.
        if base <= cutoff and processing_delay <= cutoff - base:
            eligible.append(version)
    return max(eligible, key=lambda row: (row.public_at, row.version_id), default=None)


# Every timestamp, period and value below is invented. An amendment is a new row.
VERSIONS = (
    EpsVersion("v0", Decimal("2"), date(2025, 12, 31),
               timestamp("2026-01-20T14:00:00Z"), timestamp("2026-01-20T14:01:00Z")),
    EpsVersion("v1", Decimal("4"), date(2026, 3, 31),
               timestamp("2026-04-30T20:05:00Z"), timestamp("2026-04-30T20:07:00Z")),
    EpsVersion("v2", Decimal("1"), date(2026, 3, 31),
               timestamp("2026-05-15T14:00:00Z"), timestamp("2026-05-15T14:02:00Z")),
)

CASES = (
    ("before_any_version", "2026-01-20T13:59:59Z", None),
    ("initial_public_but_not_seen", "2026-01-20T14:00:00Z", None),
    ("initial_seen", "2026-01-20T14:01:00Z", "v0"),
    ("period_end_does_not_publish", "2026-03-31T20:00:00Z", "v0"),
    ("before_release", "2026-04-30T20:04:59Z", "v0"),
    ("public_not_yet_seen", "2026-04-30T20:05:00Z", "v0"),
    ("just_before_capture", "2026-04-30T20:06:59Z", "v0"),
    ("at_capture", "2026-04-30T20:07:00Z", "v1"),
    ("before_amendment", "2026-05-15T13:59:59Z", "v1"),
    ("amendment_public_not_seen", "2026-05-15T14:00:00Z", "v1"),
    ("amendment_seen", "2026-05-15T14:02:00Z", "v2"),
)


def toy_lower_pe(eps_a: Decimal) -> str:
    """Rank two invented positive-EPS securities at the same fixed price of 20.

    B has EPS 3. This is arithmetic illustrating changed selections, not a
    valuation recommendation or a rule for zero/negative earnings.
    """
    if not isinstance(eps_a, Decimal):
        raise TypeError("EPS must be a Decimal")
    if not eps_a.is_finite() or eps_a <= 0:
        raise ValueError("This toy ranking requires positive finite EPS")
    # With equal positive prices and positive EPS, larger EPS means lower P/E.
    # Compare the exact values instead of rounding two decimal divisions.
    # Ties select A, matching the stable alphabetical tie-break in the fixture.
    return "A" if eps_a >= Decimal(3) else "B"


def example_results() -> dict:
    observations = []
    for name, decision, expected_id in CASES:
        selected = select_as_of(VERSIONS, timestamp(decision))
        actual_id = selected.version_id if selected else None
        if actual_id != expected_id:
            raise AssertionError((name, actual_id, expected_id))
        observations.append({"case": name, "decision": decision,
                             "version": actual_id, "eps": str(selected.eps) if selected else None})
    return {
        "synthetic": True,
        "timestamp_cases_passed": len(observations),
        "cases": observations,
        "lower_pe_before_capture": toy_lower_pe(VERSIONS[0].eps),
        "lower_pe_at_capture": toy_lower_pe(VERSIONS[1].eps),
        "scope": "Data eligibility and a toy ranking only; no return backtest or execution model.",
    }


if __name__ == "__main__":
    print(json.dumps(example_results(), indent=2))
