import pytest

from valorant_qa.contracts import validate_event


VALID_PURCHASE = {
    "event": "purchase",
    "version": 1,
    "request_id": "req-1",
    "player_id": "p-1",
    "item_id": "rifle",
    "timestamp": "2026-10-30T10:00:00Z",
}


def test_valid_purchase_contract():
    assert validate_event(VALID_PURCHASE) == []


@pytest.mark.parametrize("field", ["event", "version", "request_id", "player_id", "item_id"])
def test_purchase_required_fields(field):
    payload = {**VALID_PURCHASE}
    payload.pop(field)
    assert any("required" in error or "unknown" in error for error in validate_event(payload))


@pytest.mark.parametrize(
    ("field", "value", "fragment"),
    [
        ("version", "1", "version must be int"),
        ("request_id", 123, "request_id must be str"),
        ("player_id", [], "player_id must be str"),
        ("item_id", None, "item_id must be str"),
        ("timestamp", 123, "timestamp must be str"),
    ],
)
def test_purchase_field_types(field, value, fragment):
    assert fragment in validate_event({**VALID_PURCHASE, field: value})


@pytest.mark.parametrize("field", ["request_id", "player_id", "item_id"])
def test_identifiers_cannot_be_blank(field):
    assert any("must not be empty" in error for error in validate_event({**VALID_PURCHASE, field: " "}))


def test_unknown_field_can_be_strict_or_tolerant():
    payload = {**VALID_PURCHASE, "new_server_field": True}
    assert "new_server_field is unknown" in validate_event(payload)
    assert validate_event(payload, reject_unknown=False) == []


@pytest.mark.parametrize("version", [0, 2, 999])
def test_unsupported_versions(version):
    assert "version is unsupported" in validate_event({**VALID_PURCHASE, "version": version})


@pytest.mark.parametrize("winner", ["", "C", "a", 1])
def test_round_winner_contract(winner):
    payload = {
        "event": "round_settlement",
        "version": 1,
        "event_id": "round-1",
        "match_id": "m-1",
        "winner": winner,
    }
    assert validate_event(payload)


@pytest.mark.parametrize("timestamp", ["yesterday", "2026/10/30", "25:00"])
def test_timestamp_contract(timestamp):
    assert "timestamp must be ISO-8601" in validate_event({**VALID_PURCHASE, "timestamp": timestamp})


@pytest.mark.parametrize("payload", [None, [], "event", 1])
def test_payload_must_be_object(payload):
    assert validate_event(payload) == ["payload must be an object"]

