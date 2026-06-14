"""Insider & institutional tests. Transaction-code decomposition."""

from typing import Any

from pennytune.features.insider import (
    EdgarInsiderProvider,
    Form144,
    InsiderTransaction,
    InstitutionalPosition,
    OwnershipFiling,
    compute_insider_signal,
    detect_ownership_signals,
    form144s_from_submissions,
    ownership_filings_from_submissions,
    parse_form4_xml,
    raw_ownership_doc,
)
from pennytune.providers.base import ProviderError


def test_code_p_conviction_cluster_and_noise_excluded() -> None:
    transactions = [
        InsiderTransaction(
            "CEO", "P", 100_000, 80_000, "2026-05-12"
        ),  # open-market buy
        InsiderTransaction(
            "CFO", "P", 50_000, 40_000, "2026-05-15"
        ),  # 2nd buyer → cluster
        InsiderTransaction(
            "VP", "F", 5_000, 4_000, "2026-05-10"
        ),  # tax withhold - NEVER a sale
        InsiderTransaction(
            "VP", "M", 10_000, 0.0, "2026-05-10"
        ),  # option exercise - excluded
        InsiderTransaction("Dir", "A", 20_000, 0.0, "2026-05-01"),  # grant - excluded
    ]
    profile = compute_insider_signal(transactions)
    assert profile.distinct_p_buyers == 2
    assert profile.cluster_buy is True
    assert profile.total_buy_value == 120_000
    assert profile.excluded_count == 3  # F, M, A
    assert profile.discretionary_sell_value == 0.0  # F is NOT counted as selling
    assert profile.net_signal == "bullish"
    assert profile.insider_buying is True  # softens a dilution read


def test_sale_codes_split_discretionary_plan_and_exercise_linked() -> None:
    transactions = [
        InsiderTransaction("CEO", "S", 100_000, 90_000, "2026-05-12"),  # discretionary
        InsiderTransaction(
            "CFO", "S", 50_000, 45_000, "2026-05-15", is_10b5_1=True
        ),  # plan
        InsiderTransaction(
            "VP", "S", 30_000, 25_000, "2026-05-10", preceded_by_exercise=True
        ),
    ]
    profile = compute_insider_signal(transactions)
    assert profile.discretionary_sell_value == 90_000
    assert profile.plan_sell_value == 45_000  # 10b5-1, flagged separately
    assert profile.exercise_linked_sell_value == 25_000
    assert profile.net_signal == "bearish"


def test_form_144_cluster_is_overhang() -> None:
    profile = compute_insider_signal(
        [], form144s=[Form144("CEO", "2026-05-01"), Form144("CFO", "2026-05-02")]
    )
    assert profile.form144_count == 2
    assert profile.form144_overhang is True
    assert profile.net_signal == "bearish"


def test_13d_vs_13g_intent_and_conversion() -> None:
    filings = [
        OwnershipFiling("FundA", "SC 13G", "2026-01-10", 6.0),
        OwnershipFiling("FundA", "SC 13D", "2026-05-10", 7.5),  # 13G → 13D conversion
        OwnershipFiling("FundB", "SC 13G", "2026-03-01", 5.5),
    ]
    signals = detect_ownership_signals(filings)
    assert signals.activist_13d == 1
    assert signals.passive_13g == 2
    assert signals.crossings_over_5pct == 3
    assert "FundA" in signals.conversions_13g_to_13d
    assert "FundB" not in signals.conversions_13g_to_13d


def test_institutional_accumulation() -> None:
    profile = compute_insider_signal(
        [],
        institutional=[
            InstitutionalPosition(
                "Inst1", 1_000_000, 1_000_000, "Q1-2026"
            ),  # initiating
            InstitutionalPosition("Inst2", 500_000, -200_000, "Q1-2026"),  # trimming
        ],
    )
    assert profile.institutional_accumulation == 1


def test_no_activity_is_neutral() -> None:
    profile = compute_insider_signal([])
    assert profile.net_signal == "neutral"
    assert profile.insider_buying is False
    assert profile.confidence == "low"


# ---- live fetch boundary: Form 4 XML parsing + submissions-derived 144/13D-G --


def _form4_xml(
    owner: str, txns: list[tuple[str, str, str, str]], *, footnotes: str = ""
) -> str:
    """Build a real-shape Form 4 ownership XML; txns are (code, shares, price, date)."""
    blocks = ""
    for code, shares, price, date in txns:
        blocks += f"""
        <nonDerivativeTransaction>
          <securityTitle><value>Common Stock</value></securityTitle>
          <transactionDate><value>{date}</value></transactionDate>
          <transactionCoding>
            <transactionFormType>4</transactionFormType>
            <transactionCode>{code}</transactionCode>
          </transactionCoding>
          <transactionAmounts>
            <transactionShares><value>{shares}</value></transactionShares>
            <transactionPricePerShare><value>{price}</value></transactionPricePerShare>
            <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
          </transactionAmounts>
        </nonDerivativeTransaction>"""
    return f"""<?xml version="1.0"?>
<ownershipDocument>
  <documentType>4</documentType>
  <reportingOwner>
    <reportingOwnerId><rptOwnerName>{owner}</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship><isOfficer>1</isOfficer><officerTitle>CEO</officerTitle></reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>{blocks}
  </nonDerivativeTable>
  {footnotes}
</ownershipDocument>"""


def test_parse_form4_xml_reads_code_owner_and_value() -> None:
    xml = _form4_xml("Doe Jane", [("P", "10000", "2.50", "2026-05-12")])
    txns = parse_form4_xml(xml.encode("utf-8"))
    assert len(txns) == 1
    t = txns[0]
    assert t.insider == "Doe Jane" and t.role == "CEO"
    assert t.code == "P"
    assert t.shares == 10_000.0
    assert t.value == 25_000.0  # 10000 × 2.50
    assert t.date == "2026-05-12"


def test_parse_form4_distinguishes_p_buy_from_grant_and_tax() -> None:
    # The correctness heart: P is a buy; A (grant) and F (tax) are NOT.
    xml = _form4_xml(
        "Doe Jane",
        [
            ("P", "10000", "2.00", "2026-05-12"),  # open-market BUY → conviction
            ("A", "50000", "0", "2026-05-01"),  # grant — routine comp, noise
            ("F", "3000", "2.00", "2026-05-13"),  # tax withholding — NEVER a sale
        ],
    )
    txns = parse_form4_xml(xml.encode("utf-8"))
    assert [t.code for t in txns] == ["P", "A", "F"]
    profile = compute_insider_signal(txns)
    assert profile.buy_count == 1 and profile.total_buy_value == 20_000.0  # only P
    assert profile.excluded_count == 2  # A + F counted only for transparency
    assert profile.discretionary_sell_value == 0.0  # F is NOT selling
    # one buyer alone is not a cluster, but the grant/tax never inflate buying
    assert profile.distinct_p_buyers == 1


def test_parse_form4_10b5_1_footnote_marks_plan_sale() -> None:
    xml = _form4_xml(
        "Sel Ler",
        [("S", "10000", "3.00", "2026-05-12")],
        footnotes=(
            '<footnotes><footnote id="F1">Shares sold under a Rule 10b5-1 '
            "trading plan adopted earlier.</footnote></footnotes>"
        ),
    )
    txns = parse_form4_xml(xml.encode("utf-8"))
    assert txns[0].is_10b5_1 is True
    profile = compute_insider_signal(txns)
    assert profile.plan_sell_value == 30_000.0
    assert profile.discretionary_sell_value == 0.0  # plan sale ≠ discretionary


def test_parse_form4_holdings_only_and_malformed_are_empty() -> None:
    holdings_only = """<?xml version="1.0"?><ownershipDocument>
      <reportingOwner><reportingOwnerId><rptOwnerName>H</rptOwnerName></reportingOwnerId>
      </reportingOwner><nonDerivativeTable><nonDerivativeHolding>
      <securityTitle><value>Common</value></securityTitle></nonDerivativeHolding>
      </nonDerivativeTable></ownershipDocument>"""
    assert parse_form4_xml(holdings_only) == []  # suppress-not-impute
    assert parse_form4_xml(b"<not-valid-xml") == []  # malformed → empty, no raise


def test_raw_ownership_doc_strips_xsl_render_prefix() -> None:
    assert raw_ownership_doc("xslF345X06/form4.xml") == "form4.xml"
    assert raw_ownership_doc("xslF345X05/wf-form4_123.xml") == "wf-form4_123.xml"
    assert raw_ownership_doc("form4.xml") == "form4.xml"  # already raw


def test_form144s_and_ownership_from_submissions() -> None:
    submissions = {
        "filings": {
            "recent": {
                "form": ["4", "144", "144", "SC 13G", "SC 13D", "8-K"],
                "filingDate": [
                    "2026-05-01",
                    "2026-05-02",
                    "2026-05-03",
                    "2026-04-01",
                    "2026-05-10",
                    "2026-05-11",
                ],
                "accessionNumber": ["a", "b", "c", "d", "e", "f"],
            }
        }
    }
    assert len(form144s_from_submissions(submissions)) == 2  # → overhang
    ownership = ownership_filings_from_submissions(submissions)
    assert [o.form_type for o in ownership] == ["SC 13G", "SC 13D"]
    signals = detect_ownership_signals(ownership)
    assert signals.activist_13d == 1 and signals.passive_13g == 1
    # accession-keyed filers → no spurious 13G→13D conversion across filings
    assert signals.conversions_13g_to_13d == []


class _FakeOwnershipClient:
    """Serves Form 4 XML by raw document name via get_bytes."""

    def __init__(self, xml_by_doc: dict[str, str], error: Exception | None = None):
        self._xml = xml_by_doc
        self._error = error

    def get_bytes(self, url: str, **kwargs: Any) -> bytes:
        if self._error is not None:
            raise self._error
        for doc, xml in self._xml.items():
            if url.endswith(doc):
                return xml.encode("utf-8")
        raise AssertionError(f"unexpected URL {url}")


def test_get_insider_evidence_fetches_form4_and_builds_144_13dg() -> None:
    submissions = {
        "filings": {
            "recent": {
                "form": ["4", "144", "SC 13D"],
                "filingDate": ["2026-05-12", "2026-05-02", "2026-05-10"],
                "accessionNumber": ["0001062993-26-000123", "x", "y"],
                # the XSL-rendered HTML path; the parser must hit the raw XML
                "primaryDocument": ["xslF345X06/form4.xml", "d.htm", "sch.htm"],
            }
        }
    }
    xml = _form4_xml("Doe Jane", [("P", "10000", "2.00", "2026-05-12")])
    client = _FakeOwnershipClient({"000106299326000123/form4.xml": xml})
    provider = EdgarInsiderProvider(client)  # type: ignore[arg-type]
    ev = provider.get_insider_evidence("0000000001", submissions=submissions, now=None)
    assert len(ev.transactions) == 1 and ev.transactions[0].code == "P"
    assert len(ev.form144s) == 1  # the 144 (overhang)
    assert len(ev.ownership_filings) == 1  # the 13D
    profile = compute_insider_signal(
        ev.transactions, form144s=ev.form144s, ownership_filings=ev.ownership_filings
    )
    assert profile.buy_count == 1


def test_get_insider_evidence_degrades_without_submissions() -> None:
    provider = EdgarInsiderProvider(_FakeOwnershipClient({}))  # type: ignore[arg-type]
    ev = provider.get_insider_evidence("0000000001", submissions=None)
    assert ev.transactions == ()
    assert any("submissions unavailable" in note for note in ev.completeness)


def test_get_insider_evidence_skips_unreadable_form4() -> None:
    submissions = {
        "filings": {
            "recent": {
                "form": ["4"],
                "filingDate": ["2026-05-12"],
                "accessionNumber": ["a"],
                "primaryDocument": ["xslF345X06/form4.xml"],
            }
        }
    }
    client = _FakeOwnershipClient({}, error=ProviderError("HTTP 403"))
    provider = EdgarInsiderProvider(client)  # type: ignore[arg-type]
    ev = provider.get_insider_evidence("1", submissions=submissions, now=None)
    assert ev.transactions == ()  # unreadable Form 4 skipped, not raised
