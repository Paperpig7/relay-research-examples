"""Compare cent-rounding policies on two synthetic invoice lines."""

import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP
from pathlib import Path

CENT = Decimal("0.01")
FIXTURE = Path(__file__).with_name("invoice_line_cases.json")


@dataclass(frozen=True)
class _Line:
    exact: Decimal
    half_up: Decimal
    half_even: Decimal
    binary: float
    unit_first_up: Decimal
    unit_first_even: Decimal


def _amounts(quantity, unit_text):
    unit = Decimal(unit_text)
    extended = quantity * unit
    return _Line(
        exact=extended,
        half_up=extended.quantize(CENT, rounding=ROUND_HALF_UP),
        half_even=extended.quantize(CENT, rounding=ROUND_HALF_EVEN),
        binary=round(quantity * float(unit_text), 2),
        unit_first_up=quantity * unit.quantize(CENT, rounding=ROUND_HALF_UP),
        unit_first_even=quantity * unit.quantize(CENT, rounding=ROUND_HALF_EVEN),
    )


def main():
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
    print("qty   unit  exact line  half-up  half-even  float round  unit-up*  unit-even*")
    lines = []
    for case in cases:
        quantity = case["quantity"]
        unit = case["unit_price"]
        line = _amounts(quantity, unit)
        lines.append(line)
        print(f"{quantity:3}  {unit:>5}  {line.exact:10.3f}  {line.half_up:7.2f}"
              f"  {line.half_even:9.2f}  {line.binary:11.2f}"
              f"  {line.unit_first_up:8.2f}  {line.unit_first_even:10.2f}")
    print("* Negative controls: round the decimal unit price before multiplying.")
    up_total = sum(line.half_up for line in lines)
    even_total = sum(line.half_even for line in lines)
    exact_total = sum(line.exact for line in lines)
    print(f"Sum of rounded lines: half-up {up_total}, half-even {even_total}.")
    print(f"Round the combined exact amount once: {exact_total:.3f} -> "
          f"{exact_total.quantize(CENT, rounding=ROUND_HALF_UP)} (half-up), "
          f"{exact_total.quantize(CENT, rounding=ROUND_HALF_EVEN)} (half-even).")


if __name__ == "__main__":
    main()
