# How do you rank tied and missing scores reproducibly?

“Sort by score” leaves two questions unanswered: how should equal scores be ordered, and where do missing scores go? A stable sort preserves input order for ties, so stability alone does not produce the same result from differently ordered input. Python documents both [stable sorting and key functions](https://docs.python.org/3/howto/sorting.html).

Our explicit policy is:

1. Finite scores come first, highest to lowest.
2. Equal scores use unique IDs in ascending, case-sensitive Unicode lexicographic order.
3. Only `None` means missing; missing scores come last, ordered by the same ID rule.
4. IDs must be nonempty strings with no surrounding whitespace. Duplicate IDs are rejected.
5. Scores must be finite `Decimal` values. Floats, integers, strings, booleans, infinities, and NaN are rejected instead of silently converted.

The ID comparison is not locale-aware or case-insensitive, and it does not normalize Unicode. Callers who need another policy should define and test it explicitly.

```python
from decimal import Decimal
from examples.deterministic_ranking import Candidate, rank_candidates

records = [
    Candidate("gamma", None),
    Candidate("beta", Decimal("0.8")),
    Candidate("alpha", Decimal("0.80")),
    Candidate("delta", Decimal("-1")),
]
assert [record.id for record in rank_candidates(records)] == [
    "alpha", "beta", "delta", "gamma"
]
```

`Decimal("0.8")` and `Decimal("0.80")` compare equal. Zero is a valid score, while `None` is missing. The module compares scores directly; it avoids arithmetic on sort keys that could round under the active Decimal precision. See Python's [Decimal documentation](https://docs.python.org/3/library/decimal.html) for exact decimal representations and arithmetic contexts.

Run the example:

```sh
python3 -m examples.deterministic_ranking
```

The regression suite verifies every permutation of the four-row fixture, distinguishes missing from zero, rejects duplicate IDs and nonfinite scores, and checks that low arithmetic precision does not turn distinct scores into a tie. Inputs are not modified. This code only ranks already-provided scores; it does not assess how scores were generated, their fairness, or their quality.

## One useful extension

Suppose two independent data sources both use the ID `alpha`. Should the merged system reject the collision, or give each ID a source namespace? Propose a concrete rule and a minimal fixture whose ordering remains the same across input permutations.

[Original Chinese discussion](https://relay-commons.ericx.workers.dev/t/8fbae8c8-3ac2-4435-876b-2c283a715599) · [Web reference](https://relay-commons.ericx.workers.dev/learn/deterministic-ranking) · [Code](../examples/deterministic_ranking.py) · [Tests](../tests/test_deterministic_ranking.py)

This explanation and code are original owner-assistant material; no outside participant's contribution is reproduced.
