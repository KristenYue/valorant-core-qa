"""Small schema/contract validator for simulated game service events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class EventSchema:
    required: dict[str, type]
    optional: dict[str, type]
    allowed_versions: frozenset[int] = frozenset({1})


SCHEMAS = {
    "purchase": EventSchema(
        required={"event": str, "version": int, "request_id": str, "player_id": str, "item_id": str},
        optional={"timestamp": str},
    ),
    "round_settlement": EventSchema(
        required={"event": str, "version": int, "event_id": str, "match_id": str, "winner": str},
        optional={"timestamp": str, "score_a": int, "score_b": int},
    ),
    "reconnect": EventSchema(
        required={"event": str, "version": int, "request_id": str, "match_id": str, "player_id": str},
        optional={"timestamp": str, "client_round": int},
    ),
}


def validate_event(payload: Any, *, reject_unknown: bool = True) -> list[str]:
    if not isinstance(payload, dict):
        return ["payload must be an object"]
    event_name = payload.get("event")
    if event_name not in SCHEMAS:
        return ["event is unknown"]
    schema = SCHEMAS[event_name]
    errors: list[str] = []

    for name, expected_type in schema.required.items():
        if name not in payload:
            errors.append(f"{name} is required")
        elif type(payload[name]) is not expected_type:
            errors.append(f"{name} must be {expected_type.__name__}")

    for name, expected_type in schema.optional.items():
        if name in payload and type(payload[name]) is not expected_type:
            errors.append(f"{name} must be {expected_type.__name__}")

    allowed_fields = set(schema.required) | set(schema.optional)
    if reject_unknown:
        errors.extend(f"{name} is unknown" for name in sorted(set(payload) - allowed_fields))

    version = payload.get("version")
    if type(version) is int and version not in schema.allowed_versions:
        errors.append("version is unsupported")
    for identifier in ("request_id", "event_id", "player_id", "match_id", "item_id"):
        if identifier in payload and isinstance(payload[identifier], str) and not payload[identifier].strip():
            errors.append(f"{identifier} must not be empty")
    if event_name == "round_settlement" and payload.get("winner") not in {"A", "B"}:
        errors.append("winner must be A or B")
    for score in ("score_a", "score_b", "client_round"):
        if score in payload and type(payload[score]) is int and payload[score] < 0:
            errors.append(f"{score} must be non-negative")
    if "timestamp" in payload and isinstance(payload["timestamp"], str):
        try:
            datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))
        except ValueError:
            errors.append("timestamp must be ISO-8601")
    return errors

