import pytest

from valorant_qa.match_flow import InvalidTransition, MatchSession, MatchState, RoundPhase


def started_match() -> MatchSession:
    session = MatchSession()
    session.queue()
    session.match_found()
    session.lock_agent()
    session.enter_match()
    return session


def test_happy_path_from_queue_to_post_match():
    session = started_match()
    assert (session.state, session.round_phase, session.round_number) == (
        MatchState.IN_MATCH,
        RoundPhase.BUY,
        1,
    )
    session.start_combat()
    assert session.settle_round("A", "round-1") is True
    session.finish_match()
    assert session.state is MatchState.POST_MATCH
    assert (session.score_a, session.score_b) == (1, 0)


def test_round_settlement_replay_does_not_double_score():
    session = started_match()
    session.start_combat()
    assert session.settle_round("B", "round-1") is True

    assert session.settle_round("B", "round-1") is False
    assert (session.score_a, session.score_b) == (0, 1)


@pytest.mark.parametrize("method", ["start_combat", "finish_match"])
def test_invalid_state_transition_is_rejected(method):
    session = MatchSession()
    with pytest.raises(InvalidTransition):
        getattr(session, method)()


def test_reconnect_restores_server_authoritative_snapshot():
    session = started_match()
    session.start_combat()
    session.disconnect()

    stale_client = session.snapshot().__class__(
        MatchState.IN_MATCH, RoundPhase.BUY, 1, 9, 9, False
    )
    restored = session.reconnect(stale_client)

    assert restored.connected is True
    assert restored.round_phase is RoundPhase.COMBAT
    assert (restored.score_a, restored.score_b) == (0, 0)


def test_queue_can_be_cancelled_before_loading():
    session = MatchSession()
    session.queue()
    session.cancel_queue()
    assert session.state is MatchState.CANCELLED

