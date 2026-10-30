"""Configurable combat/ability model for boundary and idempotency testing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CombatResult(str, Enum):
    SUCCESS = "success"
    DUPLICATE = "duplicate"
    DEAD = "dead"
    UNKNOWN_ABILITY = "unknown_ability"
    NO_CHARGES = "no_charges"
    ON_COOLDOWN = "on_cooldown"


@dataclass(frozen=True)
class Ability:
    ability_id: str
    max_charges: int
    cooldown_ticks: int = 0

    def __post_init__(self) -> None:
        if not self.ability_id:
            raise ValueError("ability_id must not be empty")
        if self.max_charges < 0 or self.cooldown_ticks < 0:
            raise ValueError("charges and cooldown must be non-negative")


@dataclass(frozen=True)
class DamageOutcome:
    result: CombatResult
    health_after: int
    armor_after: int
    absorbed: int
    health_damage: int


@dataclass
class Combatant:
    health: int = 100
    armor: int = 0
    abilities: dict[str, Ability] = field(default_factory=dict)
    charges: dict[str, int] = field(default_factory=dict)
    _last_cast_tick: dict[str, int] = field(default_factory=dict)
    _processed_events: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.health <= 0 or self.armor < 0:
            raise ValueError("initial health must be positive and armor non-negative")
        for ability_id, ability in self.abilities.items():
            self.charges.setdefault(ability_id, ability.max_charges)

    @property
    def alive(self) -> bool:
        return self.health > 0

    def apply_damage(self, amount: int, event_id: str) -> DamageOutcome:
        if not event_id:
            raise ValueError("event_id must not be empty")
        if amount < 0:
            raise ValueError("damage must be non-negative")
        if event_id in self._processed_events:
            return DamageOutcome(CombatResult.DUPLICATE, self.health, self.armor, 0, 0)
        self._processed_events.add(event_id)
        if not self.alive:
            return DamageOutcome(CombatResult.DEAD, self.health, self.armor, 0, 0)

        absorbed = min(self.armor, amount)
        health_damage = min(self.health, amount - absorbed)
        self.armor -= absorbed
        self.health -= health_damage
        return DamageOutcome(
            CombatResult.SUCCESS, self.health, self.armor, absorbed, health_damage
        )

    def cast(self, ability_id: str, event_id: str, tick: int) -> CombatResult:
        if not event_id:
            raise ValueError("event_id must not be empty")
        if tick < 0:
            raise ValueError("tick must be non-negative")
        if event_id in self._processed_events:
            return CombatResult.DUPLICATE
        self._processed_events.add(event_id)
        if not self.alive:
            return CombatResult.DEAD
        ability = self.abilities.get(ability_id)
        if ability is None:
            return CombatResult.UNKNOWN_ABILITY
        if self.charges[ability_id] <= 0:
            return CombatResult.NO_CHARGES
        last_tick = self._last_cast_tick.get(ability_id)
        if last_tick is not None and tick - last_tick < ability.cooldown_ticks:
            return CombatResult.ON_COOLDOWN

        self.charges[ability_id] -= 1
        self._last_cast_tick[ability_id] = tick
        return CombatResult.SUCCESS

