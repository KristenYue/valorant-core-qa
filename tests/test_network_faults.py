import pytest

from valorant_qa.network import FaultyChannel, NetworkEvent, NetworkProfile


def events(count=6):
    return [NetworkEvent(f"event-{index}", index * 10, {"sequence": index}) for index in range(1, count + 1)]


@pytest.mark.parametrize("latency_ms", [0, 50, 200, 500])
@pytest.mark.parametrize("drop_every", [0, 3])
@pytest.mark.parametrize("duplicate_every", [0, 2])
@pytest.mark.parametrize("reorder_window", [1, 3])
def test_network_fault_matrix(latency_ms, drop_every, duplicate_every, reorder_window):
    profile = NetworkProfile(latency_ms, drop_every, duplicate_every, reorder_window)
    delivered = FaultyChannel(profile).transmit(events())

    assert all(item.delivered_at_ms == item.event.sent_at_ms + latency_ms for item in delivered)
    if drop_every:
        assert "event-3" not in {item.event.event_id for item in delivered}
        assert "event-6" not in {item.event.event_id for item in delivered}
    if duplicate_every:
        assert any(item.copy_number == 2 for item in delivered)
    else:
        assert all(item.copy_number == 1 for item in delivered)
    if reorder_window == 1:
        unique_ids = list(dict.fromkeys(item.event.event_id for item in delivered))
        assert unique_ids == sorted(unique_ids, key=lambda value: int(value.split("-")[1]))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"latency_ms": -1},
        {"drop_every": -1},
        {"duplicate_every": -1},
        {"reorder_window": 0},
    ],
)
def test_invalid_network_profiles(kwargs):
    with pytest.raises(ValueError):
        NetworkProfile(**kwargs)


def test_invalid_event_rejected():
    channel = FaultyChannel(NetworkProfile())
    with pytest.raises(ValueError, match="event_id"):
        channel.transmit([NetworkEvent("", 0, {})])

