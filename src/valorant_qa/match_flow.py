"""Finite-state model for matchmaking, rounds, disconnect and settlement."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MatchState(str, Enum):
    IDLE = "idle"
    QUEUED = "queued"
    AGENT_SELECT = "agent_select"
    LOADING = "loading"
    IN_MATCH = "in_match"
    POST_MATCH = "post_match"
    CANCELLED = "cancelled"


class RoundPhase(str, Enum):
    NOT_STARTED = "not_started"
    BUY = "buy"
    COMBAT = "combat"
    ROUND_END = "round_end"


class InvalidTransition(ValueError):
    pass


@dataclass(frozen=True)
class Snapshot:
    match_state: MatchState
    round_phase: RoundPhase
    round_number: int
    score_a: int
    score_b: int
    connected: bool


@dataclass
class MatchSession:
    state: MatchState = MatchState.IDLE
    round_phase: RoundPhase = RoundPhase.NOT_STARTED
    round_number: int = 0
    score_a: int = 0
    score_b: int = 0
    connected: bool = True
    _settled_round_ids: set[str] = field(default_factory=set)
    _authoritative_snapshot: Snapshot | None = None

    def queue(self) -> None:
        self._require_state(MatchState.IDLE)
        self.state = MatchState.QUEUED

    def match_found(self) -> None:
        self._require_state(MatchState.QUEUED)
        self.state = MatchState.AGENT_SELECT

    def lock_agent(self) -> None:
        self._require_state(MatchState.AGENT_SELECT)
        self.state = MatchState.LOADING

    def enter_match(self) -> None:
        self._require_state(MatchState.LOADING)
        self.state = MatchState.IN_MATCH
        self.start_round()

    def start_round(self) -> None:
        self._require_state(MatchState.IN_MATCH)
        if self.round_phase not in {RoundPhase.NOT_STARTED, RoundPhase.ROUND_END}:
            raise InvalidTransition(f"cannot start a round from {self.round_phase}")
        self.round_number += 1
        self.round_phase = RoundPhase.BUY
        self._capture_authoritative_state()

    def start_combat(self) -> None:
        self._require_state(MatchState.IN_MATCH)
        self._require_phase(RoundPhase.BUY)
        self.round_phase = RoundPhase.COMBAT
        self._capture_authoritative_state()

    def settle_round(self, winner: str, round_event_id: str) -> bool:
        """Settle at most once; False means duplicate server event ignored."""
        self._require_state(MatchState.IN_MATCH)
        if round_event_id in self._settled_round_ids:
            return False
        self._require_phase(RoundPhase.COMBAT)
        if winner not in {"A", "B"}:
            raise ValueError("winner must be A or B")
        if winner == "A":
            self.score_a += 1
        else:
            self.score_b += 1
        self._settled_round_ids.add(round_event_id)
        self.round_phase = RoundPhase.ROUND_END
        self._capture_authoritative_state()
        return True

    def finish_match(self) -> None:
        self._require_state(MatchState.IN_MATCH)
        self._require_phase(RoundPhase.ROUND_END)
        self.state = MatchState.POST_MATCH
        self._capture_authoritative_state()

    def cancel_queue(self) -> None:
        if self.state not in {MatchState.QUEUED, MatchState.AGENT_SELECT}:
            raise InvalidTransition(f"cannot cancel from {self.state}")
        self.state = MatchState.CANCELLED

    def disconnect(self) -> None:
        self._require_state(MatchState.IN_MATCH)
        self._capture_authoritative_state()
        self.connected = False

    def reconnect(self, client_snapshot: Snapshot | None = None) -> Snapshot:
        """Restore server-authoritative state, ignoring stale client state."""
        self._require_state(MatchState.IN_MATCH)
        if self.connected:
            raise InvalidTransition("session is already connected")
        if self._authoritative_snapshot is None:
            raise InvalidTransition("no authoritative snapshot available")

        server = self._authoritative_snapshot
        self.state = server.match_state
        self.round_phase = server.round_phase
        self.round_number = server.round_number
        self.score_a = server.score_a
        self.score_b = server.score_b
        self.connected = True
        return self.snapshot()

    def snapshot(self) -> Snapshot:
        return Snapshot(
            self.state,
            self.round_phase,
            self.round_number,
            self.score_a,
            self.score_b,
            self.connected,
        )

    def _capture_authoritative_state(self) -> None:
        self._authoritative_snapshot = self.snapshot()

    def _require_state(self, expected: MatchState) -> None:
        if self.state is not expected:
            raise InvalidTransition(f"expected {expected}, got {self.state}")

    def _require_phase(self, expected: RoundPhase) -> None:
        if self.round_phase is not expected:
            raise InvalidTransition(f"expected {expected}, got {self.round_phase}")

