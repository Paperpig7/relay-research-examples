"""Illustrate basic EPS arithmetic with explicit, hypothetical share counts."""

from decimal import Decimal, localcontext
from typing import Iterable, Tuple


def _require_decimal(value: Decimal) -> None:
    if not isinstance(value, Decimal):
        raise TypeError("Pass a Decimal, for example Decimal('100000000')")
    if not value.is_finite():
        raise ValueError("A finite value is required")


def weighted_average_shares(periods: Iterable[Tuple[Decimal, Decimal]]) -> Decimal:
    """Average positive share counts by nonnegative time weights.

    Each pair is (shares outstanding, time weight). Weights must describe the
    same reporting period using consistent units, such as days. This function
    does not infer dates, process corporate actions, or calculate diluted EPS.
    """
    periods = list(periods)
    if not periods:
        raise ValueError("At least one period is required")
    for shares, weight in periods:
        _require_decimal(shares)
        _require_decimal(weight)
        if shares <= 0 or weight < 0:
            raise ValueError("Shares must be positive and time weights nonnegative")
    with localcontext() as ctx:
        ctx.prec = 40
        total_weight = sum((weight for _, weight in periods), Decimal(0))
        if not total_weight:
            raise ValueError("At least one positive time weight is required")
        return sum((shares * weight for shares, weight in periods), Decimal(0)) / total_weight


def basic_eps(earnings_available_to_common: Decimal, average_shares: Decimal) -> Decimal:
    """Divide earnings available to common holders by weighted-average shares.

    Negative earnings are permitted. This simplified calculation assumes its
    numerator and denominator have already been prepared for the same period.
    """
    _require_decimal(earnings_available_to_common)
    _require_decimal(average_shares)
    if average_shares <= 0:
        raise ValueError("Weighted-average shares must be positive")
    with localcontext() as ctx:
        ctx.prec = 40
        return earnings_available_to_common / average_shares


def main() -> None:
    earnings = Decimal("100000000")
    before = Decimal("100000000")
    after = Decimal("80000000")
    half_period = weighted_average_shares([(before, Decimal(1)), (after, Decimal(1))])
    print(f"Hypothetical earnings available to common holders: {earnings:,.0f}")
    print(f"100m weighted-average shares: EPS {basic_eps(earnings, before):.2f}")
    print(f"80m weighted-average shares: EPS {basic_eps(earnings, after):.2f}")
    print(f"100m then 80m for equal halves: average shares {half_period:,.0f}")
    print(f"Same earnings with that denominator: EPS {basic_eps(earnings, half_period):.6f}")
    print("No preferred dividends or dilution assumed. Higher EPS alone does not prove value creation.")


if __name__ == "__main__":
    main()
