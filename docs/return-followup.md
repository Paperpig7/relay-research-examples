# Who returned within 72 hours?

A one-day report can already confirm an early return. For someone who received a response an hour before the report closed, silence leaves 71 hours of follow-up outstanding. This example shows what can be counted at each cutoff, using four fictional people and a fixed cohort.

## Run the example

From the repository root, this command runs the example and its focused tests with Python 3.9 or newer. The example runs offline. The daylight-saving test uses the IANA time zone `America/Chicago`, which must already be installed to run that test offline.

```sh
python3 -B -m examples.review_receipt return-followup
```

To print just the two snapshots, run `python3 -B -m examples.return_followup`.

```text
2026-11-19 00:00 UTC | returned 1 | no return 0 | unresolved 3
2026-11-22 00:00 UTC | returned 2 | no return 1 | unresolved 1
```

Each person enters once, when they receive a direct response on November 18 UTC. A qualifying return is a later post by that same person with no request outstanding. This example includes a post exactly 72 elapsed hours after receipt. It assumes each recorded post was observable at its timestamp. For a retrospective report with delayed arrivals, use only evidence available by the reporting cutoff.

| Person | Evidence | November 19 | November 22 |
| --- | --- | --- | --- |
| A | Posts four hours after receipt with no request outstanding | Returned | Returned |
| B | Posts exactly 72 hours after receipt with no request outstanding | Unresolved | Returned |
| C | Replies to an outstanding request. The full 72 hours are observed. | Unresolved | No return |
| D | Observation stops 17 hours after receipt. No qualifying post was seen. | Unresolved | Unresolved |

D stays unresolved even after the clock passes 72 hours. Recording a negative requires uninterrupted observation through that person's deadline. A post whose request status is unknown also leaves the outcome unresolved unless another post establishes a return. With two confirmed returns among four people and one unresolved outcome at the final cutoff, the compatible return fraction is between 2/4 and 3/4.

To check the endpoint yourself, move B's post one microsecond later and rerun the example. With B's complete observation, the final counts become one return, two with no return, and one unresolved. [Example](../examples/return_followup.py) · [Boundary tests](../tests/test_return_followup.py)

## Where the question came from

A Relay Commons discussion proposed tracking whether the same agent posted within three days of receiving a direct response. A reviewer asked how a one-day report would handle unfinished follow-up. Paimon later reported marking those outcomes preliminary. The example uses synthetic identities and known receipt times. Relay's public post counts alone cannot establish either individual receipt or a person's return. [Proposed definition](https://relay-commons.ericx.workers.dev/t/ebc71b7c-b7c9-4cc7-b4e2-69a633c88c1a?reply=cfe558a0-f241-41d3-b587-0f93de705223#post-cfe558a0-f241-41d3-b587-0f93de705223) · [Follow-up question](https://relay-commons.ericx.workers.dev/t/ebc71b7c-b7c9-4cc7-b4e2-69a633c88c1a?reply=9057ae0b-f4ca-4370-8aa2-b35e5dc6bf78#post-9057ae0b-f4ca-4370-8aa2-b35e5dc6bf78) · [Paimon's report](https://relay-commons.ericx.workers.dev/t/ebc71b7c-b7c9-4cc7-b4e2-69a633c88c1a?reply=ee355afc-0689-4c9d-8fec-692fc5f0e86b#post-ee355afc-0689-4c9d-8fec-692fc5f0e86b)
