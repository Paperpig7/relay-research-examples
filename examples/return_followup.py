"""Classify 72-hour returns for a fixed cohort with known receipt times."""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional


@dataclass(frozen=True)
class Receipt:
    subject: str
    at: datetime
    # Last instant of uninterrupted post observation starting at receipt.
    covered_through: Optional[datetime]


@dataclass(frozen=True)
class Post:
    subject: str
    at: datetime
    # Was a request outstanding at the time of this post?
    request_outstanding: Optional[bool]

    def __post_init__(self) -> None:
        if self.request_outstanding is not None and type(self.request_outstanding) is not bool:
            raise ValueError("Request state must be True, False or None")


def utc(value: datetime) -> datetime:
    if value.utcoffset() is None:
        raise ValueError("An observation time needs a UTC offset")
    return value.astimezone(timezone.utc)


def classify(receipt: Receipt, posts: Iterable[Post], as_of: datetime) -> str:
    """Use only posts observed by as_of. The 72-hour endpoint is inclusive."""
    start, cutoff = utc(receipt.at), utc(as_of)
    if cutoff < start:
        raise ValueError("The report cutoff precedes the receipt")
    horizon = start + timedelta(hours=72)
    last_observable = min(cutoff, horizon)
    coverage = utc(receipt.covered_through) if receipt.covered_through is not None else None

    if coverage is not None and coverage < start:
        raise ValueError("Continuous coverage cannot end before the receipt")

    ambiguous_post = False
    for post in posts:
        if post.subject != receipt.subject or not start < utc(post.at) <= last_observable:
            continue
        if post.request_outstanding is False:
            return "returned"
        if post.request_outstanding is None:
            ambiguous_post = True

    if cutoff >= horizon and coverage is not None and coverage >= horizon and not ambiguous_post:
        return "no return"
    return "unresolved"


def main() -> None:
    # Four fictional subjects, each enrolled once upon a known direct response.
    start = datetime(2026, 11, 18, tzinfo=timezone.utc)
    hour = timedelta(hours=1)
    end = start + 96 * hour
    cohort = (
        Receipt("A", start, end),
        Receipt("B", start + hour, end),
        Receipt("C", start + 2 * hour, end),
        Receipt("D", start + 3 * hour, start + 20 * hour),
    )
    posts = (
        Post("A", start + 4 * hour, False),
        Post("B", start + 73 * hour, False),  # Exactly 72 hours after B's receipt.
        Post("C", start + 8 * hour, True),   # A requested reply.
    )
    for cutoff in (start + 24 * hour, end):
        counts = Counter(classify(receipt, posts, cutoff) for receipt in cohort)
        print(f"{cutoff:%Y-%m-%d %H:%M} UTC | returned {counts['returned']} | "
              f"no return {counts['no return']} | unresolved {counts['unresolved']}")


if __name__ == "__main__":
    main()
