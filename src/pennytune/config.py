"""Configuration system - strategy profiles, universe presets, and security.

The config is TOML - read with the stdlib :mod:`tomllib`, written with
``tomli_w`` - and modeled with a pydantic v2 schema that validates ranges and
rejects unknown keys. Contents cover: the EDGAR identity string, provider
cascade order, rate-limit/cache-TTL settings, scoring weights and penalty
magnitudes, the per-preset risk-weighting bundles, the default filters, output
format, the risk-acknowledgment flag, and the active strategy profile /
universe preset.

Security posture (no-secrets requirement): PennyTune uses **no API keys** -
there is no secrets store, no keyring, no key-entry. The only configured
identity is the SEC EDGAR ``User-Agent`` string (name + email), which is not a
secret; it is stored in plain config and redacted in shared output as a
courtesy.

There is **no** ``max_spread_pct`` / tradeability gate - the tool has no price
data (real-time quotes are out of scope). Unbounded band edges use ``±inf``
(TOML-serializable), never ``None``, so the file round-trips.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Literal, cast, get_args

import tomli_w
from pydantic import BaseModel, ConfigDict, Field, field_validator

from pennytune import paths
from pennytune.presets import PRESETS
from pennytune.profiles import PROFILES

__all__ = [
    "ProfileName",
    "PresetName",
    "Weights",
    "Penalties",
    "Filters",
    "PresetRiskBundle",
    "RateLimits",
    "CacheTTL",
    "Config",
    "default_config",
    "load_config",
    "save_config",
    "get_value",
    "set_value",
    "flatten",
    "redact_identity",
    "apply_profile",
    "apply_preset",
]

ProfileName = Literal["trader", "hold", "high-return", "custom"]
PresetName = Literal["penny", "micro", "small-cap-value", "broad", "custom"]

_PROFILE_NAMES: tuple[str, ...] = get_args(ProfileName)
_PRESET_NAMES: tuple[str, ...] = get_args(PresetName)

# validate_assignment → `config set` re-validates on assignment; extra=forbid →
# unknown keys are rejected on load and on set (the config command surface).
_MODEL_CONFIG = ConfigDict(validate_assignment=True, extra="forbid")


class Weights(BaseModel):
    """Positive-contributor scoring weights. Mirror ``profiles.WEIGHT_KEYS``."""

    model_config = _MODEL_CONFIG

    valuation: float = Field(default=1.0, ge=0.0, le=10.0)
    growth: float = Field(default=1.0, ge=0.0, le=10.0)
    fundamental_momentum: float = Field(default=1.0, ge=0.0, le=10.0)
    sentiment: float = Field(default=1.0, ge=0.0, le=10.0)
    insider: float = Field(default=1.0, ge=0.0, le=10.0)
    fin_health: float = Field(default=1.0, ge=0.0, le=10.0)


class Penalties(BaseModel):
    """Penalty-overlay magnitudes. Mirror ``profiles.PENALTY_KEYS``."""

    model_config = _MODEL_CONFIG

    dilution: float = Field(default=1.0, ge=0.0, le=10.0)
    manipulation: float = Field(default=1.0, ge=0.0, le=10.0)
    delisting: float = Field(default=1.0, ge=0.0, le=10.0)
    halt_suspension: float = Field(default=1.0, ge=0.0, le=10.0)
    insider_selling: float = Field(default=1.0, ge=0.0, le=10.0)
    distress: float = Field(default=1.0, ge=0.0, le=10.0)
    beneish: float = Field(default=1.0, ge=0.0, le=10.0)


class Filters(BaseModel):
    """Default universe-construction filters.

    The universe is the SEC-registered NYSE/NASDAQ-listed set; the only filter
    is the listing venue. There is no price, market-cap, enterprise-value, or
    dollar-volume filtering: the tool fetches no live prices, so those metrics
    have no data source and are suppressed downstream rather than imputed.
    """

    model_config = _MODEL_CONFIG

    exchange: Literal["nyse", "nasdaq", "all"] = "all"


class PresetRiskBundle(BaseModel):
    """Per-preset risk-module weights. Keys mirror ``RISK_MODULE_KEYS``."""

    model_config = _MODEL_CONFIG

    # Penny-native modules.
    dilution: float = Field(default=1.0, ge=0.0, le=2.0)
    dilution_velocity: float = Field(default=1.0, ge=0.0, le=2.0)
    delisting: float = Field(default=1.0, ge=0.0, le=2.0)
    manipulation_susceptibility: float = Field(default=1.0, ge=0.0, le=2.0)
    toxic_financing: float = Field(default=1.0, ge=0.0, le=2.0)
    serial_splitter: float = Field(default=1.0, ge=0.0, le=2.0)
    low_float: float = Field(default=1.0, ge=0.0, le=2.0)
    short_interest_ftd: float = Field(default=1.0, ge=0.0, le=2.0)
    # Up-market modules.
    goodwill_impairment: float = Field(default=0.0, ge=0.0, le=2.0)
    multiple_compression: float = Field(default=0.0, ge=0.0, le=2.0)
    leverage_coverage: float = Field(default=0.0, ge=0.0, le=2.0)
    sbc_dilution: float = Field(default=0.0, ge=0.0, le=2.0)
    # Forensic emphasis.
    piotroski: float = Field(default=1.0, ge=0.0, le=2.0)


class RateLimits(BaseModel):
    """Per-provider rate limits. EDGAR hard ceiling is 10/sec."""

    model_config = _MODEL_CONFIG

    edgar_rps: float = Field(default=8.0, gt=0.0, le=10.0)
    gdelt_rps: float = Field(default=1.0, gt=0.0)


class CacheTTL(BaseModel):
    """Per-domain cache TTLs in seconds."""

    model_config = _MODEL_CONFIG

    universe_seconds: int = Field(default=86_400, ge=0)  # 1 day
    edgar_facts_seconds: int = Field(
        default=604_800, ge=0
    )  # fallback; refreshed on new filing
    current_price_seconds: int = Field(default=3_600, ge=0)
    short_interest_seconds: int = Field(default=1_209_600, ge=0)  # ~2 weeks (bimonthly)
    gdelt_seconds: int = Field(default=86_400, ge=0)


def _hold_weights() -> Weights:
    return Weights(**PROFILES["hold"].weights)


def _hold_penalties() -> Penalties:
    return Penalties(**PROFILES["hold"].penalties)


def _default_presets() -> dict[str, PresetRiskBundle]:
    return {
        name: PresetRiskBundle(**preset.risk_weights)
        for name, preset in PRESETS.items()
    }


def _default_cascade() -> dict[str, list[str]]:
    # Only one no-key provider per role (no keyed alternatives exist).
    return {
        "universe": ["sec_listed_companies"],
        "fundamentals": ["edgar"],
        "filings": ["edgar"],
        "news": ["edgar_rss", "gdelt"],
        "fails_to_deliver": ["sec_ftd"],
        "halts_suspensions": ["sec_suspensions"],
    }


def validate_edgar_identity(value: str) -> str:
    """Validate an EDGAR identity ('Name email') for SEC User-Agent compliance.

    Format-only: requires a non-empty name token and an email-like token
    (``local@domain`` with a dotted domain). It does NOT verify the email is
    real or personal - the SEC only requires a contact name + email in the
    request User-Agent. Returns the whitespace-normalized value; raises
    ``ValueError`` for an empty, whitespace-only, name-less, or email-less
    identity (which the SEC may throttle or block).
    """
    text = " ".join(value.split())
    name, _, email = text.rpartition(" ")
    local, at, domain = email.partition("@")
    email_ok = bool(at and local) and "." in domain.strip(".")
    if not name or not email_ok:
        raise ValueError(
            "EDGAR identity must be 'Name email@example.com' - the SEC requires "
            "a contact name and a valid email in the request User-Agent "
            f"(got {value!r})"
        )
    return text


class Config(BaseModel):
    """Top-level PennyTune configuration."""

    model_config = _MODEL_CONFIG

    edgar_identity: str | None = None  # "Name email" - not a secret
    profile: ProfileName = "hold"  # hold is the default strategy profile
    preset: PresetName = "penny"  # default universe preset
    risk_acknowledged: bool = False
    output_format: Literal["csv", "parquet", "json", "markdown"] = "csv"
    output_dir: str | None = None  # None -> paths.results_dir()
    filters: Filters = Field(default_factory=Filters)
    weights: Weights = Field(default_factory=_hold_weights)
    penalties: Penalties = Field(default_factory=_hold_penalties)
    rate_limits: RateLimits = Field(default_factory=RateLimits)
    cache_ttl: CacheTTL = Field(default_factory=CacheTTL)
    presets: dict[str, PresetRiskBundle] = Field(default_factory=_default_presets)
    provider_cascade: dict[str, list[str]] = Field(default_factory=_default_cascade)

    @field_validator("edgar_identity")
    @classmethod
    def _validate_identity(cls, value: str | None) -> str | None:
        """Guard `config set edgar_identity` and config-file load (init also
        pre-checks for a friendlier CLI message)."""
        return None if value is None else validate_edgar_identity(value)


def default_config() -> Config:
    """A fresh config with the default ``hold`` profile and ``penny`` preset."""
    return Config()


def apply_profile(cfg: Config, name: str) -> None:
    """Set the active profile and reset weights/penalties to its bundle.

    ``custom`` keeps the user's current weights; named profiles overwrite them.
    """
    if name not in _PROFILE_NAMES:
        raise ValueError(
            f"invalid profile {name!r}; choose from {list(_PROFILE_NAMES)}"
        )
    cfg.profile = cast(ProfileName, name)
    if name != "custom":
        cfg.weights = Weights(**PROFILES[name].weights)
        cfg.penalties = Penalties(**PROFILES[name].penalties)


def apply_preset(cfg: Config, name: str) -> None:
    """Set the active universe preset.

    A preset now only selects a per-tier risk-weighting bundle (read from
    ``cfg.presets[name]`` by the scorer); it carries no price/size band, since
    the universe is the full SEC-listed set with no price filtering.
    """
    if name not in _PRESET_NAMES:
        raise ValueError(f"invalid preset {name!r}; choose from {list(_PRESET_NAMES)}")
    cfg.preset = cast(PresetName, name)


def load_config(path: Path | None = None) -> Config:
    """Load config from TOML, or return defaults if the file does not exist."""
    target = path or paths.config_file()
    if not target.exists():
        return default_config()
    with target.open("rb") as handle:
        data = tomllib.load(handle)
    return Config.model_validate(data)


def save_config(cfg: Config, path: Path | None = None) -> Path:
    """Write config to TOML (creating parent dirs). Returns the written path."""
    target = path or paths.config_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    # exclude_none: TOML has no null. Only the three string Optionals default to
    # None, so omitting them round-trips to the same None on load (all band
    # edges are floats using +/-inf, never None).
    data = cfg.model_dump(exclude_none=True)
    with target.open("wb") as handle:
        tomli_w.dump(data, handle)
    return target


def flatten(cfg: Config) -> dict[str, Any]:
    """Flatten the config to dotted keys (e.g. ``weights.valuation``)."""
    out: dict[str, Any] = {}

    def _walk(prefix: str, node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                _walk(f"{prefix}.{key}" if prefix else key, value)
        else:
            out[prefix] = node

    _walk("", cfg.model_dump())
    return out


def get_value(cfg: Config, key: str) -> Any:
    """Return the value at a dotted ``key``; raise ``KeyError`` if unknown."""
    node: Any = cfg.model_dump()
    for part in key.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            raise KeyError(key)
    return node


def _coerce(raw: str, current: Any) -> Any:
    """Coerce a CLI string to the type of the existing value."""
    if isinstance(current, bool):
        low = raw.strip().lower()
        if low in ("true", "1", "yes", "on"):
            return True
        if low in ("false", "0", "no", "off"):
            return False
        raise ValueError(f"expected a boolean, got {raw!r}")
    if isinstance(current, int) and not isinstance(current, bool):
        return int(raw)
    if isinstance(current, float):
        return float(raw)
    if isinstance(current, list):
        return [item.strip() for item in raw.split(",") if item.strip()]
    if current is None:
        # Optional field (str | None): try numeric, else keep as string.
        try:
            return float(raw)
        except ValueError:
            return raw
    return raw


def set_value(cfg: Config, key: str, raw: str) -> None:
    """Set a dotted ``key`` from a CLI string, validating the result.

    Raises ``KeyError`` for unknown keys and ``ValueError`` /
    ``pydantic.ValidationError`` for invalid values. Setting ``profile`` or
    ``preset`` applies the matching bundle/band.
    """
    if key == "profile":
        apply_profile(cfg, raw)
        return
    if key == "preset":
        apply_preset(cfg, raw)
        return

    parts = key.split(".")
    parent: Any = cfg
    for part in parts[:-1]:
        if isinstance(parent, BaseModel):
            if part not in type(parent).model_fields:
                raise KeyError(key)
            parent = getattr(parent, part)
        elif isinstance(parent, dict):
            if part not in parent:
                raise KeyError(key)
            parent = parent[part]
        else:
            raise KeyError(key)

    leaf = parts[-1]
    if isinstance(parent, BaseModel):
        if leaf not in type(parent).model_fields:
            raise KeyError(key)
        setattr(parent, leaf, _coerce(raw, getattr(parent, leaf)))
    elif isinstance(parent, dict):
        if leaf not in parent:
            raise KeyError(key)
        parent[leaf] = _coerce(raw, parent[leaf])
    else:
        raise KeyError(key)


def redact_identity(identity: str | None) -> str:
    """Redact the email in an EDGAR identity for shared output."""
    if not identity:
        return "(not set)"
    name, _, email = identity.rpartition(" ")
    if name and "@" in email:
        local, _, domain = email.partition("@")
        masked = f"{local[0]}***" if local else "***"
        return f"{name} <{masked}@{domain}>"
    return identity
