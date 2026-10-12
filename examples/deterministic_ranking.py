"""Rank exact decimal scores with an explicit tie and missing-value policy."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class Candidate:
    id: str
    score: Optional[Decimal]


def rank_candidates(candidates: Iterable[Candidate]) -> List[Candidate]:
    """Return score descending, None last, and tied IDs ascending.

    IDs must be unique, nonempty strings without surrounding whitespace.
    ID order is Python's case-sensitive Unicode lexicographic order, not locale
    collation. Scores must be finite Decimal values; None alone means missing.
    Input order and the active Decimal arithmetic precision do not break ties.
    The input records are not modified.
    """
    records = list(candidates)
    seen = set()
    for candidate in records:
        if not isinstance(candidate, Candidate):
            raise TypeError("Each record must be a Candidate")
        if not isinstance(candidate.id, str):
            raise TypeError("Candidate IDs must be strings")
        if not candidate.id or candidate.id != candidate.id.strip():
            raise ValueError("Candidate IDs must be nonempty without surrounding whitespace")
        if candidate.id in seen:
            raise ValueError("Duplicate candidate ID: " + candidate.id)
        seen.add(candidate.id)
        if candidate.score is not None:
            if not isinstance(candidate.score, Decimal):
                raise TypeError("Scores must be Decimal values or None")
            if not candidate.score.is_finite():
                raise ValueError("Scores must be finite; use None for missing values")

    # Python's stable sort preserves the ascending ID order within equal scores.
    # Comparing Decimal values directly avoids context-dependent rounding from
    # arithmetic such as negating scores to construct a descending sort key.
    by_id = sorted(records, key=lambda candidate: candidate.id)
    scored = [candidate for candidate in by_id if candidate.score is not None]
    missing = [candidate for candidate in by_id if candidate.score is None]
    return sorted(scored, key=lambda candidate: candidate.score, reverse=True) + missing


def main() -> None:
    candidates = [
        Candidate("gamma", None),
        Candidate("beta", Decimal("0.8")),
        Candidate("alpha", Decimal("0.80")),
        Candidate("delta", Decimal("-1")),
    ]
    for candidate in rank_candidates(candidates):
        print(f"{candidate.id}: {candidate.score if candidate.score is not None else 'missing'}")


if __name__ == "__main__":
    main()
