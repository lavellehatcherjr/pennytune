"""Documentation claims that the code can be asked to confirm.

Prose drifts away from code silently. These pin the handful of documented
claims that are mechanically checkable, so the next behaviour change breaks a
test instead of quietly turning the README into fiction.

The affirmation count is the motivating case: ``init`` tells the user how many
disclaimer sections they are agreeing to, and that number has to be the number
of sections the disclaimer actually has.
"""

from __future__ import annotations

import re
from pathlib import Path

from pennytune.cli import RISK_FLAG_AFFIRMATION
from pennytune.disclaimer import FULL_DISCLAIMER
from pennytune.features.quant_scores import DISTRESS_ZONE_MAX, SAFE_ZONE_MIN
from pennytune.output import result_to_records
from pennytune.scoring import RankedResult, ScoreBreakdown

_README = Path(__file__).resolve().parents[1] / "README.md"

# A disclaimer section opens a line as "<n>. <SHOUTED TITLE>". Body lines wrap
# and are never numbered, so this cannot over-count.
_SECTION = re.compile(r"^(\d+)\. [A-Z]", re.MULTILINE)


def _disclaimer_sections() -> list[int]:
    return [int(n) for n in _SECTION.findall(FULL_DISCLAIMER)]


def test_disclaimer_sections_are_numbered_consecutively_from_one() -> None:
    """A gap or a repeat would make any count meaningless."""
    numbers = _disclaimer_sections()
    assert numbers == list(range(1, len(numbers) + 1)), (
        f"disclaimer section numbering is not 1..n: {numbers}"
    )


def test_affirmation_states_the_real_section_count() -> None:
    """What the user affirms must be the disclaimer they are shown."""
    actual = len(_disclaimer_sections())
    claimed = re.search(r"all (\d+) sections", RISK_FLAG_AFFIRMATION)
    assert claimed is not None, (
        "the affirmation no longer states a section count; if that is "
        f"deliberate, delete this test. Text: {RISK_FLAG_AFFIRMATION!r}"
    )
    assert int(claimed.group(1)) == actual, (
        f"the affirmation asks the user to accept {claimed.group(1)} sections "
        f"but the disclaimer has {actual}"
    )


def test_readme_names_the_export_columns_that_exist() -> None:
    """The README tells a spreadsheet reader which columns to look for."""
    breakdown = ScoreBreakdown(ticker="X", composite=0.0)
    record = result_to_records(RankedResult(ranked=[breakdown]))[0]
    readme = _README.read_text(encoding="utf-8")
    for column in (
        "suppressed",
        "suppressed_count",
        "evidence_complete",
        "completeness",
    ):
        assert f"`{column}`" in readme, f"README does not mention the {column} column"
        assert column in record, (
            f"README promises a {column!r} export column; export keys are "
            f"{sorted(record)}"
        )


def test_readme_quotes_the_solvency_cutoffs_the_code_uses() -> None:
    """The re-anchored cutoffs are the README's headline calibration claim."""
    readme = _README.read_text(encoding="utf-8")
    quoted = f"**{DISTRESS_ZONE_MAX:.1f} and {SAFE_ZONE_MIN:.1f}**"
    assert quoted in readme, f"README does not state the live cutoffs {quoted}"
