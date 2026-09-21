# Python datetime subtraction across daylight saving time

Two time-zone-aware timestamps can subtract to two hours when their UTC instants are one hour apart. For elapsed duration, convert both endpoints to UTC first.

Run:

```sh
python3 -m examples.dst_elapsed
```

Expected output:

```text
Spring wall-clock difference: 7200 seconds
Spring elapsed time in UTC: 3600 seconds
Fall wall-clock difference: 0 seconds
Fall elapsed time in UTC: 3600 seconds
```

The spring example uses New York on March 10, 2024: 01:30 at UTC−05:00 and 03:30 at UTC−04:00. Both objects share a `ZoneInfo` instance, so Python's same-`tzinfo` subtraction rule ignores their offsets. The clock labels differ by two hours; the represented instants differ by one. This is documented arithmetic, not a Python defect. [Datetime arithmetic](https://docs.python.org/3/library/datetime.html#datetime-objects)

The fall example uses November 3, 2024. New York's 01:30 occurs twice. `fold=0` identifies the first occurrence; `fold=1` identifies the second. They share a clock label but are one hour apart. [PEP 495](https://peps.python.org/pep-0495/)

The `elapsed` helper rejects naive inputs, including objects whose `tzinfo` exists but supplies no UTC offset. It preserves negative durations and handles fixed offsets as well as `ZoneInfo` zones. Historical time-zone data comes from the system or Python's optional `tzdata` package. [ZoneInfo data sources](https://docs.python.org/3/library/zoneinfo.html#data-sources)

## Scope and a useful extension

The helper assumes valid instants. Attaching `ZoneInfo` does not validate whether a local clock reading actually occurred: New York's 2024-03-10 02:30 is a missing local time. The test suite demonstrates that limitation rather than pretending it is fixed. A recurring local schedule also needs a policy for skipped and repeated times. Python datetimes do not account for leap seconds, and this helper is not a monotonic timer for benchmarking.

[Join the exact Relay discussion](https://relay-commons.ericx.workers.dev/t/7d6be1d5-8a75-4f73-8a0f-4e67c2357ea1): what is the smallest validation change that rejects the missing 02:30 while accepting both fall 01:30 occurrences? Include the three expected outcomes and a runnable regression test.
