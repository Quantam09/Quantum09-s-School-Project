"""Shared pagination helpers (README section 9.1: limit/offset)."""

from __future__ import annotations

from fastapi import Query


class PageParams:
    def __init__(
        self,
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> None:
        self.limit = limit
        self.offset = offset


def page_payload(items: list, total: int, *, limit: int, offset: int) -> dict:
    return {"items": items, "total": total, "limit": limit, "offset": offset}
