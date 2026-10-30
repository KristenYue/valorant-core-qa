import pytest

from valorant_qa.match_flow import MatchSession, MatchState, RoundPhase, Snapshot


def session_at_phase(phase: RoundPhase) -> MatchSession:
    session = MatchSession()
    session.queue()
    session.match_found()
    session.lock_agent()
    session.enter_match()
    if phase in {RoundPhase.COMBAT, RoundPhase.ROUND_END}:
        session.start_combat()
    if phase is RoundPhase.ROUND_END:
        session.settle_round("A", "round-1")
    return session


@pytest.mark.parametrize("phase", [RoundPhase.BUY, RoundPhase.COMBAT, RoundPhase.ROUND_END])
@pytest.mark.parametrize("stale_score", [(0, 0), (9, 9), (99, 0), (0, 99)])
def test_reconnect_matrix_uses_server_authority(phase, stale_score):
    session = session_at_phase(phase)
    expected = session.snapshot()
    session.disconnect()
    stale = Snapshot(MatchState.IN_MATCH, RoundPhase.BUY, 99, *stale_score, False)
    restored = session.reconnect(stale)
    assert restored.round_phase is expected.round_phase
    assert restored.round_number == expected.round_number
    assert (restored.score_a, restored.score_b) == (expected.score_a, expected.score_b)


@pytest.mark.parametrize("reconnect_attempts", [1, 2, 3, 5])
def test_repeated_disconnect_reconnect_cycles_preserve_state(reconnect_attempts):
    session = session_at_phase(RoundPhase.COMBAT)
    expected = session.snapshot()
    for _ in range(reconnect_attempts):
        session.disconnect()
        restored = session.reconnect()
        assert restored.round_phase is expected.round_phase
        assert (restored.score_a, restored.score_b) == (expected.score_a, expected.score_b)

