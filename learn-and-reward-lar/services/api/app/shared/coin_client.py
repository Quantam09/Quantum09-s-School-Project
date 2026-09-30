"""Coin ledger adapter.

All coin movements must go through a double-entry ledger owned by Developer C's
``coin`` module (README section 11.1); other modules must never mutate balances
directly. While that module is not merged, this adapter provides the seam:

* ``StubCoinClient`` — always accepts, records transfers in memory (local demo/tests).
* ``HttpCoinClient`` — forwards to Developer C's internal transfer endpoint
  (``POST /internal/v1/coins/transfer``) once available.

Swapping implementations is a one-line change in :func:`get_coin_client`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from app.shared.config import Settings, get_settings
from app.shared.errors import AppError, ErrorCode
from app.shared.rewards import (
    ACCOUNT_TYPE_COMMUNITY,
    ACCOUNT_TYPE_PLATFORM,
    ACCOUNT_TYPE_USER,
    COMMUNITY_SHARE,
    PLATFORM_ACCOUNT_ID,
    REWARD_CONTRIBUTION_COINS,
    REWARD_CONTRIBUTION_COMMUNITY_COINS,
    REWARD_PRACTICE_COINS,
)

COIN_TRANSACTION_TYPES = {
    "REWARD_CONTRIBUTION",
    "REWARD_PRACTICE",
    "COURSE_UNLOCK",
    "MARKET_ESCROW",
    "MARKET_SETTLEMENT",
    "COMMUNITY_POOL",
    "PLATFORM_FEE",
    "REVERSAL",
}


@dataclass
class CoinEntry:
    account_type: str  # user | community | platform | escrow
    account_id: str
    amount: int  # negative = debit, positive = credit


@dataclass
class CoinTransfer:
    transaction_type: str  # one of COIN_TRANSACTION_TYPES
    idempotency_key: str
    entries: list[CoinEntry]
    reference: str = ""


@dataclass
class CoinTransferResult:
    accepted: bool
    tx_group: str


class CoinClient(Protocol):
    def transfer(self, transfer: CoinTransfer) -> CoinTransferResult: ...


class StubCoinClient:
    """In-memory stand-in for Developer C's CoinService. Always accepts."""

    def __init__(self) -> None:
        self._records: list[CoinTransfer] = []
        self._seen_idempotency_keys: set[str] = set()

    def transfer(self, transfer: CoinTransfer) -> CoinTransferResult:
        if transfer.transaction_type not in COIN_TRANSACTION_TYPES:
            raise AppError(
                ErrorCode.COIN_TRANSFER_FAILED,
                f"Unknown coin transaction type: {transfer.transaction_type}",
            )
        if transfer.idempotency_key in self._seen_idempotency_keys:
            # Idempotent replay: report success without recording twice.
            return CoinTransferResult(accepted=True, tx_group=transfer.idempotency_key)
        debits = sum(e.amount for e in transfer.entries if e.amount < 0)
        credits = sum(e.amount for e in transfer.entries if e.amount > 0)
        if debits + credits != 0:
            raise AppError(
                ErrorCode.COIN_TRANSFER_FAILED,
                "Coin transfers must be balanced (double-entry ledger).",
                details={"debits": debits, "credits": credits},
            )
        self._seen_idempotency_keys.add(transfer.idempotency_key)
        self._records.append(transfer)
        return CoinTransferResult(accepted=True, tx_group=transfer.idempotency_key)

    @property
    def records(self) -> list[CoinTransfer]:
        return list(self._records)


class HttpCoinClient:
    """Calls Developer C's internal coin transfer API."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def transfer(self, transfer: CoinTransfer) -> CoinTransferResult:
        payload = {
            "type": transfer.transaction_type,
            "idempotency_key": transfer.idempotency_key,
            "reference": transfer.reference,
            "entries": [
                {"account_type": e.account_type, "account_id": e.account_id, "amount": e.amount}
                for e in transfer.entries
            ],
        }
        try:
            response = httpx.post(
                f"{self._base_url}/internal/v1/coins/transfer", json=payload, timeout=10.0
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AppError(
                ErrorCode.COIN_TRANSFER_FAILED,
                "Coin service is unavailable.",
                details={"reason": str(exc)},
            ) from exc
        body = response.json()
        return CoinTransferResult(
            accepted=bool(body.get("accepted", True)),
            tx_group=body.get("tx_group", transfer.idempotency_key),
        )


_client: CoinClient | None = None


def get_coin_client(settings: Settings | None = None) -> CoinClient:
    global _client
    if _client is None:
        settings = settings or get_settings()
        if settings.coin_mode == "internal":
            # Developer C's service base URL; same origin in the modular monolith.
            _client = HttpCoinClient("http://localhost:8000")
        else:
            _client = StubCoinClient()
    return _client


def reset_coin_client() -> None:
    """Test helper."""
    global _client
    _client = None


def course_unlock_transfer(
    *, user_id: str, community_id: str, price_coins: int, idempotency_key: str
) -> CoinTransfer:
    """Build the COURSE_UNLOCK double-entry transfer (user pays, community+platform earn)."""
    community_amount = round(price_coins * COMMUNITY_SHARE)
    platform_amount = price_coins - community_amount
    return CoinTransfer(
        transaction_type="COURSE_UNLOCK",
        idempotency_key=idempotency_key,
        reference=f"course_unlock:{user_id}",
        entries=[
            CoinEntry(ACCOUNT_TYPE_USER, user_id, -price_coins),
            CoinEntry(ACCOUNT_TYPE_COMMUNITY, community_id, community_amount),
            CoinEntry(ACCOUNT_TYPE_PLATFORM, PLATFORM_ACCOUNT_ID, platform_amount),
        ],
    )


def practice_reward_transfer(*, user_id: str, idempotency_key: str) -> CoinTransfer:
    """Build the REWARD_PRACTICE transfer (learner earns coins, README section 11.2).

    Double-entry: the platform treasury funds the learner's reward.
    """
    return CoinTransfer(
        transaction_type="REWARD_PRACTICE",
        idempotency_key=idempotency_key,
        reference=f"practice_reward:{user_id}",
        entries=[
            CoinEntry(ACCOUNT_TYPE_PLATFORM, PLATFORM_ACCOUNT_ID, -REWARD_PRACTICE_COINS),
            CoinEntry(ACCOUNT_TYPE_USER, user_id, REWARD_PRACTICE_COINS),
        ],
    )


def contribution_reward_transfer(
    *, user_id: str, community_id: str, resource_id: str, idempotency_key: str
) -> CoinTransfer:
    """Build the REWARD_CONTRIBUTION transfer (resource approved by review).

    README section 11.2: contributor +10, community pool +5 (funded by the platform).
    """
    total = REWARD_CONTRIBUTION_COINS + REWARD_CONTRIBUTION_COMMUNITY_COINS
    return CoinTransfer(
        transaction_type="REWARD_CONTRIBUTION",
        idempotency_key=idempotency_key,
        reference=f"resource_approved:{resource_id}",
        entries=[
            CoinEntry(ACCOUNT_TYPE_PLATFORM, PLATFORM_ACCOUNT_ID, -total),
            CoinEntry(ACCOUNT_TYPE_USER, user_id, REWARD_CONTRIBUTION_COINS),
            CoinEntry(ACCOUNT_TYPE_COMMUNITY, community_id, REWARD_CONTRIBUTION_COMMUNITY_COINS),
        ],
    )
