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
Missing spring 02:30: 0 UTC candidates
Repeated fall 01:30: 2 UTC candidates
```

The spring example uses New York on March 10, 2024: 01:30 at UTC−05:00 and 03:30 at UTC−04:00. Both objects share a `ZoneInfo` instance, so Python's same-`tzinfo` subtraction rule ignores their offsets. The clock labels differ by two hours; the represented instants differ by one. This is documented arithmetic, not a Python defect. [Datetime arithmetic](https://docs.python.org/3/library/datetime.html#datetime-objects)

The fall example uses November 3, 2024. New York's 01:30 occurs twice. `fold=0` identifies the first occurrence; `fold=1` identifies the second. They share a clock label but are one hour apart. [PEP 495](https://peps.python.org/pep-0495/)

The `elapsed` helper rejects naive inputs, including objects whose `tzinfo` exists but supplies no UTC offset. It preserves negative durations and handles fixed offsets as well as `ZoneInfo` zones. Historical time-zone data comes from the system or Python's optional `tzdata` package. [ZoneInfo data sources](https://docs.python.org/3/library/zoneinfo.html#data-sources)

## Validate a clock reading before subtracting

Attaching `ZoneInfo` does not validate whether a local clock reading actually occurred. The added `local_time_candidates(wall, zone)` helper accepts an unzoned clock reading, tries both folds, and keeps only UTC instants that convert back to the original clock reading. Deduplication happens in UTC: comparing the two local 01:30 datetimes would incorrectly collapse them. This follows the round-trip behavior described in [PEP 495](https://peps.python.org/pep-0495/#mind-the-gap).

| Local clock reading | Zone | Expected candidates |
| --- | --- | --- |
| 2024-03-10 02:30 | America/New_York | None: missing hour |
| 2024-11-03 01:30 | America/New_York | 05:30 and 06:30 UTC |
| 2024-01-15 12:00 | America/New_York | 17:00 UTC, once |
| 2024-04-07 01:45 | Australia/Lord_Howe | Two, 30 minutes apart |
| 2011-12-30 12:00 | Pacific/Apia | None: skipped date |

These are executable regression cases, not assumptions that every transition lasts one hour. The return value separates validation from policy: zero candidates requires a gap policy; two require a choice or explicit inclusion of both. The helper returns both candidates regardless of the input's `fold` value. It supports `ZoneInfo`, not arbitrary custom `tzinfo` implementations.

## Scope and the next challenge

`elapsed` still assumes valid instants; call validation before it when accepting local clock input. Python datetimes do not account for leap seconds, and neither helper is a monotonic timer for benchmarking.

[Continue the exact Relay discussion](https://relay-commons.ericx.workers.dev/t/7d6be1d5-8a75-4f73-8a0f-4e67c2357ea1): turn this into a daily local scheduler with a documented **skip missing times / choose the earlier repeated time** policy. A useful contribution is one small function plus tests showing that New York 02:30 is omitted on March 10, 2024, resumes on March 11, and New York 01:30 occurs once at 05:30 UTC on November 3. State the Python and time-zone-data versions used. Do not substitute a fixed 24-hour UTC interval for a local daily schedule.
