"""Bounded concurrency for enrichment.

Runs a function over many items with a worker cap (the rate limiters are the
real throttle), collecting per-item results and failures separately so a single
ticker's error never aborts the whole scan - failures are counted and listed.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Generic, TypeVar

__all__ = ["BoundedResult", "run_bounded"]

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


@dataclass
class BoundedResult(Generic[K, V]):
    """Outcome of a bounded run: successes keyed by item, failures keyed by item."""

    results: dict[K, V] = field(default_factory=dict)
    failures: dict[K, Exception] = field(default_factory=dict)

    @property
    def failure_count(self) -> int:
        return len(self.failures)

    @property
    def success_count(self) -> int:
        return len(self.results)


def run_bounded(
    items: Sequence[K], fn: Callable[[K], V], *, max_workers: int = 8
) -> BoundedResult[K, V]:
    """Apply ``fn`` to each item with bounded concurrency, isolating failures."""
    result: BoundedResult[K, V] = BoundedResult()
    if not items:
        return result
    workers = max(1, min(max_workers, len(items)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_item = {pool.submit(fn, item): item for item in items}
        for future, item in future_to_item.items():
            try:
                result.results[item] = future.result()
            except Exception as exc:  # noqa: BLE001 - isolate per-item failures
                result.failures[item] = exc
    return result
