import pytest

from valorant_qa.combat import Ability, Combatant, CombatResult


@pytest.mark.parametrize(
    ("health", "armor", "damage", "expected_health", "expected_armor", "absorbed"),
    [
        (100, 0, 0, 100, 0, 0),
        (100, 0, 1, 99, 0, 0),
        (100, 25, 10, 100, 15, 10),
        (100, 25, 25, 100, 0, 25),
        (100, 25, 26, 99, 0, 25),
        (100, 25, 125, 0, 0, 25),
        (100, 25, 126, 0, 0, 25),
        (1, 0, 1, 0, 0, 0),
    ],
)
def test_damage_boundaries(health, armor, damage, expected_health, expected_armor, absorbed):
    player = Combatant(health=health, armor=armor)
    outcome = player.apply_damage(damage, f"hit-{health}-{armor}-{damage}")
    assert outcome.result is CombatResult.SUCCESS
    assert (player.health, player.armor) == (expected_health, expected_armor)
    assert outcome.absorbed == absorbed


@pytest.mark.parametrize("damage", [-1, -50])
def test_negative_damage_rejected(damage):
    with pytest.raises(ValueError, match="damage"):
        Combatant().apply_damage(damage, "bad-hit")


def test_duplicate_damage_event_does_not_apply_twice():
    player = Combatant(health=100, armor=25)
    player.apply_damage(40, "hit-1")
    snapshot = (player.health, player.armor)
    duplicate = player.apply_damage(40, "hit-1")
    assert duplicate.result is CombatResult.DUPLICATE
    assert (player.health, player.armor) == snapshot


@pytest.fixture
def ability_player():
    abilities = {
        "dash": Ability("dash", max_charges=2, cooldown_ticks=3),
        "single": Ability("single", max_charges=1),
    }
    return Combatant(abilities=abilities)


def test_cast_consumes_charge(ability_player):
    assert ability_player.cast("dash", "cast-1", tick=0) is CombatResult.SUCCESS
    assert ability_player.charges["dash"] == 1


def test_cast_during_cooldown_has_no_side_effect(ability_player):
    ability_player.cast("dash", "cast-1", tick=1)
    assert ability_player.cast("dash", "cast-2", tick=3) is CombatResult.ON_COOLDOWN
    assert ability_player.charges["dash"] == 1


def test_cast_at_cooldown_boundary_succeeds(ability_player):
    ability_player.cast("dash", "cast-1", tick=1)
    assert ability_player.cast("dash", "cast-2", tick=4) is CombatResult.SUCCESS


def test_no_charge_and_unknown_ability(ability_player):
    ability_player.cast("single", "cast-1", tick=0)
    assert ability_player.cast("single", "cast-2", tick=1) is CombatResult.NO_CHARGES
    assert ability_player.cast("missing", "cast-3", tick=1) is CombatResult.UNKNOWN_ABILITY


def test_dead_player_cannot_cast(ability_player):
    ability_player.apply_damage(100, "fatal")
    assert ability_player.cast("dash", "cast-dead", tick=10) is CombatResult.DEAD


def test_duplicate_cast_is_idempotent(ability_player):
    ability_player.cast("dash", "same-cast", tick=0)
    assert ability_player.cast("dash", "same-cast", tick=99) is CombatResult.DUPLICATE
    assert ability_player.charges["dash"] == 1

