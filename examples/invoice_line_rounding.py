"""Compare invoice rounding policies and check integer-cent results from an app."""

import argparse
import json
import sys
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP
from pathlib import Path

CENT = Decimal("0.01")
FIXTURE = Path(__file__).with_name("invoice_line_cases.json")
SUBTOTAL_FIXTURE = Path(__file__).with_name("invoice_subtotal_cases.json")


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


def _show_line_comparison():
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


def _check_subtotals(observed, cases):
    if not isinstance(observed, dict):
        return ["Expected a JSON object with split and merged invoice results."]
    errors = []
    for name, case in cases.items():
        result = observed.get(name)
        if not isinstance(result, dict):
            errors.append(f"{name}: supply an object with line_cents and subtotal_cents.")
            continue
        expected = case["expected"]
        lines = result.get("line_cents")
        if not isinstance(lines, list) or any(type(cents) is not int for cents in lines):
            errors.append(f"{name}.line_cents: expected an array of JSON integers.")
        elif lines != expected["line_cents"]:
            errors.append(f"{name}.line_cents: expected {expected['line_cents']}, got {lines}.")
        subtotal = result.get("subtotal_cents")
        if type(subtotal) is not int:
            errors.append(f"{name}.subtotal_cents: expected a JSON integer.")
        elif subtotal != expected["subtotal_cents"]:
            errors.append(f"{name}.subtotal_cents: expected {expected['subtotal_cents']}, got {subtotal}.")
    return errors


def main(argv=()):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-subtotals", type=Path, metavar="PATH",
                        help="compare the app’s split and merged invoice results with the fixture")
    args = parser.parse_args(argv)
    cases = json.loads(SUBTOTAL_FIXTURE.read_text(encoding="utf-8"))
    if args.check_subtotals is None:
        _show_line_comparison()
        print("Expected application outputs in integer cents, before discounts or tax:")
        for name, case in cases.items():
            expected = case["expected"]
            print(f"  {name}: lines {expected['line_cents']}, subtotal {expected['subtotal_cents']}")
        return 0

    try:
        observed = json.loads(args.check_subtotals.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"Could not read invoice results: {error}", file=sys.stderr)
        return 1
    errors = _check_subtotals(observed, cases)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Both invoices match the expected line amounts and subtotals in integer cents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
