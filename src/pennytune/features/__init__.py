"""Feature modules. Each implements one feature's computation.

Every feature treats third-party data as untrusted, per the security
requirements, and stamps its freshness via :mod:`pennytune.freshness`.
"""

from __future__ import annotations
