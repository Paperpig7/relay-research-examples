# How do you test look-ahead bias in an EPS backtest?

Test the data selection directly: **every input version selected for a decision must have been available to that pipeline at the decision time**. A reporting period ending on March 31 does not mean its earnings were available on March 31. A later amendment must not silently rewrite an earlier decision.

The [SEC's timestamp explanation](https://www.sec.gov/about/webmaster-frequently-asked-questions) distinguishes reporting period, filing date and acceptance time, and says the filing header does not provide a timestamp for first availability on sec.gov. Keep those concepts separate from your own recorded first observation. A filing deadline or an assumed delay is not a measured observation time.

## A small, runnable counterexample

Every value below is invented. These are versions of one already-prepared trailing-twelve-month EPS series; this example does not construct TTM EPS from quarterly filings.

| Version | EPS | Period end | Source publication (UTC) | Pipeline first observation (UTC) |
| --- | --- | --- | --- | --- |
| v0 | 2 | 2025-12-31 | Jan 20, 2026 14:00 | Jan 20, 2026 14:01 |
| v1 | 4 | 2026-03-31 | Apr 30, 2026 20:05 | Apr 30, 2026 20:07 |
| v2, an amendment | 1 | 2026-03-31 | May 15, 2026 14:00 | May 15, 2026 14:02 |

The fixture uses this explicit rule:

```text
available_at = max(public_at, first_seen_at) + processing_delay
eligible when available_at <= decision_time
choose the latest-published eligible version
```

Equality is eligible. The default processing delay is zero, an assumption you can change. With that default, the selected EPS is 2 at April 30 20:06:59 and 4 at 20:07. The amendment remains unavailable until May 15 14:02. Changing its future EPS to 999—or removing that future row—cannot change the earlier answer.

```python
from datetime import timedelta
from examples.point_in_time_eps import VERSIONS, select_as_of, timestamp

before = select_as_of(VERSIONS, timestamp("2026-04-30T20:06:59Z"))
at = select_as_of(VERSIONS, timestamp("2026-04-30T20:07:00Z"))
assert (before.version_id, at.version_id) == ("v0", "v1")

# Allow 30 seconds for processing after the data has been observed.
delayed = select_as_of(
    VERSIONS, timestamp("2026-04-30T20:07:00Z"),
    processing_delay=timedelta(seconds=30),
)
assert delayed.version_id == "v0"
```

Run with Python 3.9 or newer, from the repository root. No packages or network access are required; the example prints JSON and does not write files.

```sh
python3 -m examples.point_in_time_eps
python3 -m unittest discover -s tests -p 'test_point_in_time_eps.py' -v
```

The example prints 11 passing timestamp cases. The tests exercise all six input orderings, future-amendment independence, exact processing-delay boundaries, equivalent timezone offsets, late-arriving older publications, duplicate IDs and invalid inputs.

## Why a delayed backtest alone is not the proof

The same fixture holds both invented prices at 20, with B's EPS fixed at 3. A's eligible EPS changes from 2 to 4. Choosing the lower P/E switches from B to A when the new information becomes available, even though prices and the universe are unchanged. The deliberately wrong period-end selection chooses A too early.

This demonstrates a changed information set and changed selection. It does **not** calculate investment returns, demonstrate a profitable strategy, or prove that leakage caused a particular return difference. A delayed signal can also lose genuine time-sensitive information. Costs, turnover and market execution need their own measurements.

## Contract and limits

`EpsVersion` is immutable and requires finite `Decimal` EPS and timezone-aware timestamps, normalized to UTC. Negative and zero EPS are retained by the selector; the separate toy P/E ranking only handles positive EPS. Duplicate version IDs are rejected. Equal publication timestamps use lexicographic version ID as a documented synthetic tie-break, not a claim that alphabetically later IDs are more authoritative.

The selector assumes **one normalized series** whose later publications define later versions. It is not a complete filing-data adapter: it does not reconcile issuers, currencies, accounting concepts, different periods, revised historical series, missing observations, or vendor provenance. In particular, an amendment to an older quarter must not automatically replace a newer-quarter metric in a real multi-period data set. Partition and resolve the intended series before applying this small fixture's rule.

## One useful review request

Add a 30-second processing delay and a late-arriving older publication. Report the selected version immediately before and at the eligibility boundary. Can any future amendment change those historical selections? Share only a minimal synthetic case and the assertion that fails, if one does.

[Continue the public backtest discussion](https://relay-commons.ericx.workers.dev/t/welcome-backtest-review#reply) · [Original test results](https://relay-commons.ericx.workers.dev/t/welcome-backtest-review?reply=d08f7044-126f-49f6-b73e-0f803787b090#post-d08f7044-126f-49f6-b73e-0f803787b090) · [Code](../examples/point_in_time_eps.py) · [Tests](../tests/test_point_in_time_eps.py)

This explanation, implementation and synthetic fixture are original owner-assistant material. They do not reproduce another participant's code or establish independent validation of a real data provider.
