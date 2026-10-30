"""Configurable economy model used to validate game-server invariants.

This is deliberately not a copy of Riot's internal economy service.  Prices and
limits are supplied by the caller so tests remain stable when live balance data
changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PurchaseResult(str, Enum):
    SUCCESS = "success"
    DUPLICATE = "duplicate"
    INSUFFICIENT_CREDITS = "insufficient_credits"
    PHASE_CLOSED = "phase_closed"
    SLOT_OCCUPIED = "slot_occupied"
    UNKNOWN_ITEM = "unknown_item"


@dataclass(frozen=True)
class Item:
    item_id: str
    price: int
    slot: str

    def __post_init__(self) -> None:
        if not self.item_id:
            raise ValueError("item_id must not be empty")
        if self.price < 0:
            raise ValueError("price must be non-negative")


@dataclass(frozen=True)
class Transaction:
    request_id: str
    item_id: str
    delta: int
    balance_after: int
    action: str


@dataclass
class EconomyAccount:
    credits: int
    catalog: dict[str, Item]
    max_credits: int = 9_000
    inventory: dict[str, Item] = field(default_factory=dict)
    transactions: list[Transaction] = field(default_factory=list)
    _handled_requests: dict[str, PurchaseResult] = field(default_factory=dict)
    _purchase_request_by_item: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0 <= self.credits <= self.max_credits:
            raise ValueError("initial credits must be within configured limits")

    def purchase(self, item_id: str, request_id: str, *, buy_phase_open: bool) -> PurchaseResult:
        """Apply one authoritative purchase request.

        A repeated request_id never charges twice.  The original result is
        retained internally, while the outward response is DUPLICATE so a test
        can assert that replay protection was triggered.
        """
        self._validate_request_id(request_id)
        if request_id in self._handled_requests:
            return PurchaseResult.DUPLICATE
        if not buy_phase_open:
            return self._remember(request_id, PurchaseResult.PHASE_CLOSED)

        item = self.catalog.get(item_id)
        if item is None:
            return self._remember(request_id, PurchaseResult.UNKNOWN_ITEM)
        if item.slot in self.inventory:
            return self._remember(request_id, PurchaseResult.SLOT_OCCUPIED)
        if self.credits < item.price:
            return self._remember(request_id, PurchaseResult.INSUFFICIENT_CREDITS)

        self.credits -= item.price
        self.inventory[item.slot] = item
        self._purchase_request_by_item[item_id] = request_id
        self.transactions.append(
            Transaction(request_id, item_id, -item.price, self.credits, "purchase")
        )
        return self._remember(request_id, PurchaseResult.SUCCESS)

    def refund(self, item_id: str, request_id: str, *, buy_phase_open: bool) -> PurchaseResult:
        self._validate_request_id(request_id)
        if request_id in self._handled_requests:
            return PurchaseResult.DUPLICATE
        if not buy_phase_open:
            return self._remember(request_id, PurchaseResult.PHASE_CLOSED)

        owned = next((item for item in self.inventory.values() if item.item_id == item_id), None)
        if owned is None:
            return self._remember(request_id, PurchaseResult.UNKNOWN_ITEM)

        self.inventory.pop(owned.slot)
        self.credits = min(self.max_credits, self.credits + owned.price)
        self.transactions.append(
            Transaction(request_id, item_id, owned.price, self.credits, "refund")
        )
        return self._remember(request_id, PurchaseResult.SUCCESS)

    def award(self, amount: int, request_id: str) -> bool:
        """Award settlement credits once; return False for a replay."""
        self._validate_request_id(request_id)
        if amount < 0:
            raise ValueError("award amount must be non-negative")
        if request_id in self._handled_requests:
            return False
        self.credits = min(self.max_credits, self.credits + amount)
        self.transactions.append(
            Transaction(request_id, "", amount, self.credits, "award")
        )
        self._handled_requests[request_id] = PurchaseResult.SUCCESS
        return True

    def _remember(self, request_id: str, result: PurchaseResult) -> PurchaseResult:
        self._handled_requests[request_id] = result
        return result

    @staticmethod
    def _validate_request_id(request_id: str) -> None:
        if not request_id:
            raise ValueError("request_id must not be empty")

