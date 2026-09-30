"""Per-module database schema names.

The repo convention (README section 7.4 / 15.2) is one database schema per developer
module: ``core`` (Developer C), ``learning`` (Developer B), ``resource`` / ``ai_voice``
(Developer A), ``coin`` / ``market`` / ``governance`` (Developer C).

PostgreSQL (the target platform) uses real named schemas. SQLite (used for lightweight
local development and the test suite) has no schema support, so the schema names are
dropped via ``schema_translate_map`` on the engine. The dialect is resolved at import
time from ``DATABASE_URL`` (env var first, then the local ``.env`` file).
"""

from __future__ import annotations

import os
from pathlib import Path

CORE_SCHEMA = "core"
LEARNING_SCHEMA = "learning"

_FALLBACK_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def _database_url_at_import() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if url:
        return url
    if _FALLBACK_ENV_FILE.exists():
        for line in _FALLBACK_ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip()
    return ""


def using_sqlite() -> bool:
    return _database_url_at_import().startswith("sqlite")


SCHEMA_TRANSLATE_MAP: dict[str | None, str | None] | None = (
    {CORE_SCHEMA: None, LEARNING_SCHEMA: None} if using_sqlite() else None
)
