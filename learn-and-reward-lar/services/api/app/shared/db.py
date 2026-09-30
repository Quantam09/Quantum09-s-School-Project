"""Database engine / session management and the declarative base."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.shared.schema_names import SCHEMA_TRANSLATE_MAP


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory: sessionmaker[Session] | None = None


def init_engine(database_url: str, *, force: bool = False) -> None:
    """Create the global engine/session factory.

    Idempotent: calling it again with the same URL is a no-op, so the test suite can
    prepare the database before FastAPI's lifespan runs.
    """
    global _engine, _session_factory
    if _engine is not None and not force:
        return

    connect_args: dict = {}
    engine_kwargs: dict = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        from sqlalchemy.pool import StaticPool

        engine_kwargs["poolclass"] = StaticPool
    elif SCHEMA_TRANSLATE_MAP:
        # PostgreSQL runs with real per-module schemas; translate nothing.
        engine_kwargs["schema_translate_map"] = None

    _engine = create_engine(database_url, connect_args=connect_args, **engine_kwargs)
    _session_factory = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)


def get_engine():
    if _engine is None:
        raise RuntimeError("Database engine is not initialised; call init_engine() first.")
    return _engine


def strip_schemas_for_sqlite() -> None:
    """Drop module schema names from the metadata (SQLite has no schema support).

    Used by the app lifespan for sqlite-based local runs and by the test suite.
    """
    from app.shared.schema_names import CORE_SCHEMA, LEARNING_SCHEMA

    for table in Base.metadata.tables.values():
        if table.schema in (CORE_SCHEMA, LEARNING_SCHEMA):
            table.schema = None


def get_db() -> Generator[Session, None, None]:
    if _session_factory is None:
        raise RuntimeError("Database engine is not initialised; call init_engine() first.")
    db = _session_factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
