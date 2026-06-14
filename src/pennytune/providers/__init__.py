"""Data-provider abstraction layer: the provider interface and cascade.

A single, swappable interface per data role so the engine never hard-codes a
vendor, with a cascade/fallback runner (``base.cascade``) that falls through to
the next configured provider on failure. The shared HTTP client (``http``)
enforces the security posture: safe parsing (no eval/pickle, size caps,
timeouts) and HTTPS-only egress to an allow-list of documented domains, with
TLS verification.

There is intentionally **no** price-history / OHLCV provider role - price
history and technicals are out of scope (no price history, no API keys).
"""

from __future__ import annotations
