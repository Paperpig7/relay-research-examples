"""Exact worst-case support bounds for a fixed, finite, binary population.

These are logical bounds, not confidence intervals. Known support and opposition
must refer to distinct members of the same population with stable answers to the
same question. Counts cannot verify membership, disjointness or truthful answers.
No probability model, sampling weights or assumption about nonrespondents is used.
"""

from dataclasses import dataclass
from fractions import Fraction
from typing import Tuple


def _require_count(name: str, value: int) -> None:
    # bool is an int subclass; silently counting True as one obscures bad input.
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer count, not a bool or converted value")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")


@dataclass(frozen=True)
class KnownResponses:
    """Counts of distinct known answers in one positive finite population."""

    population: int
    support: int
    oppose: int

    def __post_init__(self) -> None:
        for name in ("population", "support", "oppose"):
            _require_count(name, getattr(self, name))
        if self.population == 0:
            raise ValueError("population must be positive")
        if self.support + self.oppose > self.population:
            raise ValueError("Known answers cannot exceed the population")

    @property
    def unknown(self) -> int:
        return self.population - self.support - self.oppose

    @property
    def bounds(self) -> Tuple[Fraction, Fraction]:
        """Attainable endpoints when every unknown answer is allowed either way."""
        return (Fraction(self.support, self.population),
                Fraction(self.support + self.unknown, self.population))

    @property
    def width(self) -> Fraction:
        return Fraction(self.unknown, self.population)

    def follow_up(self, *, support: int, oppose: int) -> "KnownResponses":
        """Add newly known answers from distinct previously unknown members.

        Invitations and refusals add no known answers. The caller must ensure
        these people are not counted twice; this arithmetic cannot detect overlap.
        """
        _require_count("support", support)
        _require_count("oppose", oppose)
        if support + oppose > self.unknown:
            raise ValueError("New answers cannot exceed previously unknown members")
        return KnownResponses(self.population, self.support + support,
                              self.oppose + oppose)


def main() -> None:
    initial = KnownResponses(population=1000, support=60, oppose=40)
    # Of 100 recontacted people, 80 answer. The 20 refusals stay unknown,
    # along with the 800 people not recontacted. No identities are collected.
    later = initial.follow_up(support=50, oppose=30)
    for label, counts in (("Initial", initial), ("After follow-up", later)):
        lower, upper = counts.bounds
        print(f"{label}: support={counts.support}, oppose={counts.oppose}, "
              f"unknown={counts.unknown}")
        print(f"  Exact population support bounds: {lower} to {upper} "
              f"({100 * lower}% to {100 * upper}%)")
        print(f"  Width: {counts.width} ({100 * counts.width} percentage points)")

    plug_in = (initial.support + initial.unknown * Fraction(50, 80)) / initial.population
    print(f"Unsupported extrapolation of 50/80 to all 900 initial nonrespondents: "
          f"{plug_in} ({100 * plug_in}% = 62.25%)")
    print("Randomly inviting 100 people does not make their 80 respondents representative.")
    print("Synthetic counts only. Logical bounds are not sampling confidence intervals.")


if __name__ == "__main__":
    main()
