"""Convert hypothetical quarterly and annualized growth using Decimal values."""

from decimal import Decimal, localcontext
from typing import Sequence


def _require_finite_decimal(value: Decimal) -> None:
    if not isinstance(value, Decimal):
        raise TypeError("Pass a Decimal, for example Decimal('4.0')")
    if not value.is_finite():
        raise ValueError("A finite value is required")


def _require_growth(percent: Decimal) -> None:
    _require_finite_decimal(percent)
    if percent < -100:
        raise ValueError("Growth cannot be below -100 percent")


def annualized_percent(quarterly_percent: Decimal) -> Decimal:
    """Annualize a percentage by compounding the same quarterly rate four times."""
    _require_growth(quarterly_percent)
    with localcontext() as ctx:
        ctx.prec = 40
        ratio = 1 + quarterly_percent / 100
        return (ratio**4 - 1) * 100


def quarterly_percent(annualized: Decimal) -> Decimal:
    """Invert annualization with a fourth root, including the -100% boundary."""
    _require_growth(annualized)
    with localcontext() as ctx:
        ctx.prec = 40
        ratio = 1 + annualized / 100
        return (ratio.sqrt().sqrt() - 1) * 100


def growth_from_levels(previous: Decimal, current: Decimal) -> Decimal:
    """Return period-to-period percentage growth from nonnegative output levels."""
    _require_finite_decimal(previous)
    _require_finite_decimal(current)
    if previous <= 0 or current < 0:
        raise ValueError("Previous level must be positive; current must be nonnegative")
    with localcontext() as ctx:
        ctx.prec = 40
        return (current / previous - 1) * 100


def annual_average_percent(
    previous_year: Sequence[Decimal], current_year: Sequence[Decimal]
) -> Decimal:
    """Compare averages of four comparable quarterly output levels per year.

    Inputs are levels in the same units, not quarterly percentage growth rates.
    This does not revise vintages, seasonally adjust, or aggregate GDP components.
    """
    for year in (previous_year, current_year):
        if len(year) != 4:
            raise ValueError("Exactly four quarterly levels are required per year")
        for level in year:
            _require_finite_decimal(level)
            if level < 0:
                raise ValueError("Output levels must be nonnegative")
    with localcontext() as ctx:
        ctx.prec = 40
        previous_mean = sum(previous_year, Decimal(0)) / 4
        current_mean = sum(current_year, Decimal(0)) / 4
        return growth_from_levels(previous_mean, current_mean)


def main() -> None:
    growth = growth_from_levels(Decimal("100"), Decimal("101"))
    print(f"Hypothetical 100 -> 101 quarterly growth: {growth:.6f}%")
    print(f"Same quarter, annualized growth: {annualized_percent(growth):.6f}%")
    print(f"4% annualized expressed quarterly: {quarterly_percent(Decimal('4')):.6f}%")
    print("Annualization repeats an observed rate mathematically; it is not a forecast.")
    previous = tuple(Decimal(v) for v in ("100", "100", "100", "120"))
    current = (Decimal("110"),) * 4
    print(f"Separate hypothetical years, annual-average growth: {annual_average_percent(previous, current):.6f}%")
    print(f"Same years, Q4-over-Q4 growth: {growth_from_levels(previous[-1], current[-1]):.6f}%")


if __name__ == "__main__":
    main()
