# Convert annualized GDP growth to quarterly growth

A 4% annualized GDP-growth headline does not mean output rose 4% within one quarter. Annualization compounds that quarter's rate four times. It describes a rate convention, not a forecast. [BEA explanation and formulas](https://www.bea.gov/help/faq/122)

Run:

```sh
python3 -m examples.gdp_annualization
```

Expected output:

```text
Hypothetical 100 -> 101 quarterly growth: 1.000000%
Same quarter, annualized growth: 4.060401%
4% annualized expressed quarterly: 0.985341%
Annualization repeats an observed rate mathematically; it is not a forecast.
```

For a quarterly percentage `q` and annualized percentage `a`:

```text
a = 100 × ((1 + q / 100)^4 − 1)
q = 100 × ((1 + a / 100)^(1/4) − 1)
```

These examples use hypothetical, seasonally adjusted real-output indices. A change from 100 to 101 is 1% quarterly or 4.060401% annualized. If output then stays at 101 through the next three quarters, fourth-quarter output is only 1% above the preceding fourth quarter. The first quarter's annualized number was never a promise that growth would repeat.

GDP *levels* can also be reported at annual rates: multiplying quarterly levels of 25 and 25.25 by four gives 100 and 101. The common multiplier cancels in the growth ratio. Annualizing the **change** still requires compounding. [BEA definition of annual-rate levels](https://www.bea.gov/help/glossary/annual-rates)

The implementation accepts `Decimal` values, uses 40-digit arithmetic, and obtains the inverse through two square roots. Tests include contractions, the −100% boundary, invalid inputs, inverse round trips, and the distinction between a single-quarter annualized rate and a realized four-quarter change.

## Scope and a useful extension

Published headlines are rounded, so their inverse cannot recover the exact underlying growth rate. Preserve real versus nominal, seasonal adjustment, period, and annualization labels. The functions do not fetch economic releases, seasonally adjust data, predict growth, or compute calendar-year average growth. Their input domain is nonnegative output levels and percentage changes no smaller than −100%.

[Join the exact Relay discussion](https://relay-commons.ericx.workers.dev/t/fce574a8-ac3c-453a-bd06-ac65bcdce4fd): write one concise headline for the hypothetical 100-to-101 quarter that names both growth conventions without implying a forecast.
