"""Security & privacy invariants, asserted as tests.

These lock the non-negotiables in place so a regression fails CI: no key/secret
mechanism anywhere, no keyed/price providers or scraped sources, safe parsing -
no eval/pickle/unsafe-XML, HTTPS-only egress to documented domains, no
telemetry, and the mandatory disclaimer + GDELT attribution shipping in the
product.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pennytune import disclaimer
from pennytune.config import Config, flatten
from pennytune.features.news import GDELT_ATTRIBUTION
from pennytune.providers.base import DisallowedDomainError
from pennytune.providers.http import ALLOWED_DOMAIN_SUFFIXES, SafeHttpClient

SRC = Path(__file__).resolve().parent.parent / "src" / "pennytune"
_PY_FILES = sorted(SRC.rglob("*.py"))

# No secrets store, no keyed/price/scraped providers anywhere.
_FORBIDDEN_IMPORT_ROOTS = frozenset(
    {
        "keyring",  # no credential store (the tool is keyless)
        "pickle",  # never unpickle untrusted data
        "yfinance",  # scraped / ToS-ambiguous, dropped
        "stooq",
        "pandas_datareader",
        "finnhub",  # keyed providers - none exist in a no-key tool
        "databento",
        "alpaca",
        "alpaca_trade_api",
        "polygon",
        "iexfinance",
        "xml",  # stdlib XML is unsafe; use defusedxml
    }
)


def _import_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize("path", _PY_FILES, ids=lambda p: p.name)
def test_no_forbidden_imports(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offending = _import_roots(tree) & _FORBIDDEN_IMPORT_ROOTS
    assert not offending, f"{path.name} imports forbidden module(s): {offending}"


@pytest.mark.parametrize("path", _PY_FILES, ids=lambda p: p.name)
def test_no_eval_exec_or_os_system(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                assert func.id not in {"eval", "exec"}, f"{path.name}: {func.id}()"
            if isinstance(func, ast.Attribute) and func.attr in {"system", "popen"}:
                base = func.value
                assert not (isinstance(base, ast.Name) and base.id == "os"), (
                    f"{path.name}: os.{func.attr}()"
                )


@pytest.mark.parametrize("path", _PY_FILES, ids=lambda p: p.name)
def test_no_plaintext_http_urls(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert "http://" not in node.value, f"{path.name}: insecure http:// URL"


# ---- config exposes no key/secret surface ------------------------------------


def test_config_has_no_secret_fields() -> None:
    keys = " ".join(flatten(Config())).lower()
    for banned in ("api_key", "apikey", "token", "secret", "password", "keyring"):
        assert banned not in keys, f"config exposes a {banned!r}-like field"


# ---- egress allow-list is the documented no-key domains only -----------------


def test_egress_allowlist_is_documented_no_key_domains() -> None:
    assert set(ALLOWED_DOMAIN_SUFFIXES) == {
        "sec.gov",
        "gdeltproject.org",
    }
    # No keyed/price-vendor domains may be present.
    joined = " ".join(ALLOWED_DOMAIN_SUFFIXES)
    for vendor in ("alpaca", "polygon", "finnhub", "iex", "yahoo", "stooq"):
        assert vendor not in joined


def test_http_client_rejects_non_https_and_off_allowlist() -> None:
    client = SafeHttpClient()
    try:
        with pytest.raises(DisallowedDomainError):
            client.get_bytes("http://data.sec.gov/x", retry=False)  # not HTTPS
        with pytest.raises(DisallowedDomainError):
            client.get_bytes("https://evil.example.com/x", retry=False)  # off-list
    finally:
        client.close()


# ---- disclaimer + GDELT attribution ship -------------------------------------


def test_full_disclaimer_has_all_twelve_sections() -> None:
    text = disclaimer.FULL_DISCLAIMER
    assert "NOT INVESTMENT ADVICE" in text.upper()
    for section in range(1, 13):
        assert f"{section}." in text, f"disclaimer missing section {section}"


def test_gdelt_attribution_credits_the_project() -> None:
    assert "GDELT Project" in GDELT_ATTRIBUTION
    assert "gdeltproject.org" in GDELT_ATTRIBUTION


# ---- .gitignore keeps secrets and downloaded data out of the repo ------------


def test_gitignore_excludes_secrets_and_data() -> None:
    gitignore = (SRC.parent.parent / ".gitignore").read_text(encoding="utf-8")
    for pattern in (".env", "config.toml", "results/", "cache/", "*.duckdb"):
        assert pattern in gitignore, f".gitignore missing {pattern!r}"
