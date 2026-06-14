"""Bounded-concurrency resilience tests."""

from pennytune.concurrency import run_bounded


def test_collects_all_results() -> None:
    out = run_bounded([1, 2, 3, 4], lambda x: x * x, max_workers=4)
    assert out.results == {1: 1, 2: 4, 3: 9, 4: 16}
    assert out.failures == {}
    assert out.success_count == 4


def test_one_failure_does_not_abort_the_batch() -> None:
    def fn(value: int) -> int:
        if value == 3:
            raise ValueError("boom on 3")
        return value * 10

    out = run_bounded([1, 2, 3, 4], fn, max_workers=2)
    assert out.results == {1: 10, 2: 20, 4: 40}
    assert set(out.failures) == {3}
    assert out.failure_count == 1
    assert isinstance(out.failures[3], ValueError)


def test_empty_input() -> None:
    items: list[int] = []
    out = run_bounded(items, lambda value: value)
    assert out.success_count == 0
    assert out.failure_count == 0
