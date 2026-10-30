"""Deterministic network fault simulator for repeatable automated tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NetworkEvent:
    event_id: str
    sent_at_ms: int
    payload: dict


@dataclass(frozen=True)
class Delivery:
    event: NetworkEvent
    delivered_at_ms: int
    copy_number: int = 1


@dataclass(frozen=True)
class NetworkProfile:
    latency_ms: int = 0
    drop_every: int = 0
    duplicate_every: int = 0
    reorder_window: int = 1

    def __post_init__(self) -> None:
        if self.latency_ms < 0 or self.drop_every < 0 or self.duplicate_every < 0:
            raise ValueError("network profile values must be non-negative")
        if self.reorder_window <= 0:
            raise ValueError("reorder_window must be positive")


class FaultyChannel:
    """Apply a deterministic fault profile; suitable for CI and reproduction."""

    def __init__(self, profile: NetworkProfile):
        self.profile = profile

    def transmit(self, events: list[NetworkEvent]) -> list[Delivery]:
        accepted: list[NetworkEvent] = []
        for index, event in enumerate(events, start=1):
            if not event.event_id:
                raise ValueError("event_id must not be empty")
            if event.sent_at_ms < 0:
                raise ValueError("sent_at_ms must be non-negative")
            if self.profile.drop_every and index % self.profile.drop_every == 0:
                continue
            accepted.append(event)

        reordered: list[NetworkEvent] = []
        window = self.profile.reorder_window
        for start in range(0, len(accepted), window):
            reordered.extend(reversed(accepted[start : start + window]))

        deliveries: list[Delivery] = []
        for original_index, event in enumerate(reordered, start=1):
            delivered_at = event.sent_at_ms + self.profile.latency_ms
            deliveries.append(Delivery(event, delivered_at, 1))
            if self.profile.duplicate_every and original_index % self.profile.duplicate_every == 0:
                deliveries.append(Delivery(event, delivered_at, 2))
        return deliveries

