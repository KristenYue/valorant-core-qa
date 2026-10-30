import pytest

from valorant_qa.economy import EconomyAccount, Item, PurchaseResult


@pytest.fixture
def account():
    catalog = {
        "sidearm": Item("sidearm", 300, "weapon"),
        "rifle": Item("rifle", 2_900, "weapon"),
        "armor": Item("armor", 1_000, "armor"),
    }
    return EconomyAccount(credits=3_500, catalog=catalog)


@pytest.mark.parametrize(
    ("item_id", "credits", "expected"),
    [
        ("rifle", 2_900, PurchaseResult.SUCCESS),
        ("rifle", 2_899, PurchaseResult.INSUFFICIENT_CREDITS),
        ("missing", 9_000, PurchaseResult.UNKNOWN_ITEM),
    ],
)
def test_purchase_boundaries(item_id, credits, expected, account):
    account.credits = credits
    result = account.purchase(item_id, "buy-1", buy_phase_open=True)
    assert result is expected
    assert 0 <= account.credits <= account.max_credits


def test_duplicate_purchase_does_not_charge_twice(account):
    assert account.purchase("rifle", "buy-1", buy_phase_open=True) is PurchaseResult.SUCCESS
    balance_after_first = account.credits

    assert account.purchase("rifle", "buy-1", buy_phase_open=True) is PurchaseResult.DUPLICATE
    assert account.credits == balance_after_first
    assert len(account.transactions) == 1


def test_purchase_outside_buy_phase_is_rejected_without_side_effect(account):
    original = account.credits
    assert account.purchase("rifle", "buy-closed", buy_phase_open=False) is PurchaseResult.PHASE_CLOSED
    assert account.credits == original
    assert account.inventory == {}


def test_refund_restores_balance_during_buy_phase(account):
    account.purchase("armor", "buy-armor", buy_phase_open=True)
    assert account.refund("armor", "refund-armor", buy_phase_open=True) is PurchaseResult.SUCCESS
    assert account.credits == 3_500
    assert "armor" not in account.inventory


def test_settlement_award_is_idempotent(account):
    assert account.award(1_000, "round-settlement-1") is True
    once = account.credits
    assert account.award(1_000, "round-settlement-1") is False
    assert account.credits == once


def test_empty_request_id_fails_before_any_side_effect(account):
    original = account.credits
    with pytest.raises(ValueError, match="request_id"):
        account.purchase("rifle", "", buy_phase_open=True)
    assert account.credits == original
    assert account.inventory == {}
    assert account.transactions == []

