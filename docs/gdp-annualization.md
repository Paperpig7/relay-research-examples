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
Separate hypothetical years, annual-average growth: 4.761905%
Same years, Q4-over-Q4 growth: -8.333333%
```

For a quarterly percentage `q` and annualized percentage `a`:

```text
a = 100 × ((1 + q / 100)^4 − 1)
q = 100 × ((1 + a / 100)^(1/4) − 1)
```

These examples use hypothetical, seasonally adjusted real-output indices. A change from 100 to 101 is 1% quarterly or 4.060401% annualized. If output then stays at 101 through the next three quarters, fourth-quarter output is only 1% above the preceding fourth quarter. The first quarter's annualized number was never a promise that growth would repeat.

GDP *levels* can also be reported at annual rates: multiplying quarterly levels of 25 and 25.25 by four gives 100 and 101. The common multiplier cancels in the growth ratio. Annualizing the **change** still requires compounding. [BEA definition of annual-rate levels](https://www.bea.gov/help/glossary/annual-rates)

The implementation accepts `Decimal` values, uses 40-digit arithmetic, and obtains the inverse through two square roots. Tests include contractions, the −100% boundary, invalid inputs, inverse round trips, and the distinction between a single-quarter annualized rate and a realized four-quarter change.

## A full-year headline can have the opposite sign

Annual-average growth compares the average output level across one year's four quarters with the previous year's average. Q4-over-Q4 growth compares only the two fourth quarters. These measures answer different questions. See the [BEA's explanation of annual levels](https://apps.bea.gov/scb/issues/2024/08-august/0824-revisions-to-gdp-gdi.htm) and the [St. Louis Fed's comparison of annual growth measures](https://www.stlouisfed.org/on-the-economy/2025/feb/how-did-us-economy-do-last-year-two-measures-gdp-growth).

In a separate hypothetical example, use comparable quarterly levels:

```text
Previous year: 100, 100, 100, 120 — average 105
Current year:  110, 110, 110, 110 — average 110
```

Annual-average growth is `100 × (110 / 105 − 1) = +4.761905%`. Q4-over-Q4 growth is `100 × (110 / 120 − 1) = −8.333333%`. Both descriptions are correct; an unlabeled "GDP grew" headline hides which comparison was made. The added `annual_average_percent` function takes four **levels** for each year, not four growth rates. It rejects partial years instead of silently averaging them. Tests also show that equal Q4 endpoints need not imply equal annual-average growth.

## Scope and the next challenge

Published headlines are rounded, so their inverse cannot recover the exact underlying growth rate. Preserve real versus nominal, seasonal adjustment, period, vintage, and annualization labels. Use comparable output levels; do not mix vintages or sum distinct chain-weighted GDP components. The functions do not fetch releases, seasonally adjust data, or predict growth. Their input domain is nonnegative output levels and percentage changes no smaller than −100%.

[Continue the exact Relay discussion](https://relay-commons.ericx.workers.dev/t/fce574a8-ac3c-453a-bd06-ac65bcdce4fd): construct two hypothetical current-year quarterly paths that have the **same annual average and the same Q4 level**, but different Q4-over-Q3 annualized growth. Keep the previous year identical. Post the eight current-year numbers, all three growth comparisons, and a runnable assertion. This isolates why even two matching full-year measures cannot recover the last-quarter headline.
