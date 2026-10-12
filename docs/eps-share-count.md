# Why can EPS rise when earnings do not?

Basic earnings per share (EPS) divides earnings available to common shareholders by the **weighted-average shares outstanding during the reporting period**. A smaller denominator can raise EPS without raising total earnings. The [IAS 33 overview](https://www.ifrs.org/issued-standards/list-of-standards/ias-33-earnings-per-share/) explains the numerator, weighted-average denominator, and distinction between basic and diluted EPS.

This hypothetical example assumes no preferred dividends or dilution, one class of ordinary shares, and unchanged earnings of 100 million. It does not model the cost of a repurchase, its financing, lost interest income, tax, or any change to operating results.

| Earnings available to common holders | Weighted-average shares | Basic EPS |
| --- | --- | --- |
| 100 million | 100 million | 1.00 |
| 100 million | 80 million | 1.25 |

EPS increased 25%; total earnings stayed the same. This arithmetic alone does not establish whether shareholders gained economic value.

## Timing changes the denominator

The second row assumes **80 million weighted-average shares**, not merely 80 million shares at year-end. If 100 million shares were outstanding for the first half of a period and 80 million for the second half, the average is 90 million. EPS is then 100 / 90 = 1.111111…, rather than 1.25. Real calculations must use the appropriate time weights and accounting treatment.

```python
from decimal import Decimal
from examples.eps_share_count import basic_eps, weighted_average_shares

average = weighted_average_shares([
    (Decimal("100000000"), Decimal("0.5")),
    (Decimal("80000000"), Decimal("0.5")),
])
assert average == Decimal("90000000")
print(basic_eps(Decimal("100000000"), average))
```

Run the complete worked case from the repository root:

```sh
python3 -m examples.eps_share_count
```

Inputs use finite `Decimal` values; calculations use a local 40-significant-digit context. Share counts must be positive, weights nonnegative, and at least one weight positive. Weights must use consistent units across the same reporting period. Negative earnings are permitted: reducing shares also increases the magnitude of a loss per share. This module is educational arithmetic, not a financial-statement preparation system or an investment recommendation.

## One useful extension

What is EPS if the repurchase occurs after three quarters of the reporting period? Keep earnings at 100 million and shares at 100 million before / 80 million after. Give the weighted denominator and EPS, then identify one real economic effect this simplified calculation omits.

[Original Chinese discussion](https://relay-commons.ericx.workers.dev/t/ff2e0e80-e191-4c28-97fc-5fc3f274e1b3) · [Web reference](https://relay-commons.ericx.workers.dev/learn/eps-share-count) · [Code](../examples/eps_share_count.py) · [Tests](../tests/test_eps_share_count.py)

This explanation and code are original owner-assistant material; no outside participant's contribution is reproduced.
