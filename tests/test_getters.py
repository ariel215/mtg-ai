"""
Tests for getters: the deferred-value helpers actions use to postpone
choosing players, cards, zones, and subsets until the action is performed.
"""
import pytest

from mtg_ai import decklist, game, getters, zones


# ---------------------------------------------------------------------------
# Get descriptor
# ---------------------------------------------------------------------------

class Widget:
    value = getters.Get()

    def __init__(self, value):
        self.value = value


class Unset:
    value = getters.Get()


class Defaulted:
    value = getters.Get(default_value=7)


def test_get_plain_value_is_returned_on_call():
    assert Widget(5).value(object()) == 5


def test_get_callable_is_invoked_with_game_state():
    widget = Widget(lambda gs: gs["key"])
    assert widget.value({"key": 42}) == 42


def test_get_unset_yields_none():
    assert Unset().value(object()) is None


def test_get_honors_default_value():
    assert Defaulted().value(object()) == 7


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

def test_controller_returns_zone_owner():
    gs = game.GameState([0])
    forest = decklist.Forest(gs)
    forest.zone = zones.Field(0)
    assert getters.Controller(forest)(gs) == 0


def test_controller_accepts_getter_for_card():
    gs = game.GameState([0])
    forest = decklist.Forest(gs)
    forest.zone = zones.Hand(0)
    assert getters.Controller(lambda _gs: forest)(gs) == 0


def test_controller_resolves_card_in_copied_state():
    gs = game.GameState([0])
    forest = decklist.Forest(gs)
    forest.zone = zones.Field(0)
    copy = gs.copy()
    assert getters.Controller(forest)(copy) == 0


# ---------------------------------------------------------------------------
# Zone getter
# ---------------------------------------------------------------------------

def test_zone_getter_with_owner_getter():
    zone = getters.Zone(zones.Deck(), getters.ActivePlayer())
    assert zone(game.GameState([3])) == zones.Deck(3)


def test_zone_getter_with_plain_owner():
    zone = getters.Zone(zones.Hand(), 1)
    assert zone(game.GameState([0])) == zones.Hand(1)


def test_zone_getter_preserves_position():
    zone = getters.Zone(zones.Deck(), 0, zones.BOTTOM)
    assert zone(game.GameState([0])) == zones.Deck(0, zones.BOTTOM)


def test_zone_getter_exposes_position_attribute():
    # the constructor stores this under a misspelled attribute, so the
    # documented public name is currently missing
    zone = getters.Zone(zones.Deck(), 0, zones.BOTTOM)
    assert zone.position == zones.BOTTOM


# ---------------------------------------------------------------------------
# FromZone
# ---------------------------------------------------------------------------

def deck_of(gs, n):
    """n Forests in player 0's deck, positions 0..n-1 (top = highest)."""
    cards = [decklist.Forest(gs) for _ in range(n)]
    for i, card in enumerate(cards):
        card.zone = zones.Deck(0, i)
    return cards


def test_from_zone_returns_whole_zone():
    gs = game.GameState([0])
    cards = deck_of(gs, 3)
    extra = decklist.Forest(gs)
    extra.zone = zones.Field(0)
    found = getters.FromZone(getters.Zone(zones.Deck(0)))(gs)
    assert found == cards


def test_from_zone_accepts_plain_zone():
    gs = game.GameState([0])
    cards = deck_of(gs, 2)
    found = getters.FromZone(zones.Deck(0))(gs)
    assert found == cards


def test_from_zone_top_returns_top_n_cards():
    gs = game.GameState([0])
    cards = deck_of(gs, 5)
    found = getters.FromZone(getters.Zone(zones.Deck(0)), top=2)(gs)
    assert found == [cards[3], cards[4]]


def test_from_zone_top_of_short_zone_returns_all():
    gs = game.GameState([0])
    cards = deck_of(gs, 3)
    found = getters.FromZone(getters.Zone(zones.Deck(0)), top=10)(gs)
    assert found == cards


def test_from_zone_bottom_returns_bottom_n_cards():
    gs = game.GameState([0])
    cards = deck_of(gs, 5)
    found = getters.FromZone(getters.Zone(zones.Deck(0)), bottom=2)(gs)
    assert found == [cards[0], cards[1]]


# ---------------------------------------------------------------------------
# ActivePlayer
# ---------------------------------------------------------------------------

def test_active_player_defaults_to_first_player():
    assert getters.ActivePlayer()(game.GameState([7, 8])) == 7


def test_active_player_follows_active_counter():
    gs = game.GameState([7, 8])
    gs.active_player = 1
    assert getters.ActivePlayer()(gs) == 8


# ---------------------------------------------------------------------------
# UpTo
# ---------------------------------------------------------------------------

def test_upto_lists_all_subset_sizes():
    result = list(getters.UpTo(2, lambda _: True)(["a", "b", "c"]))
    assert result == [("a", "b"), ("a", "c"), ("b", "c"),
                      ("a",), ("b",), ("c",), {}]


def test_upto_filters_by_predicate():
    result = list(getters.UpTo(2, lambda x: x % 2 == 0)([1, 2, 3, 4]))
    assert result == [(2, 4), (2,), (4,), {}]


def test_upto_orders_most_choices_first():
    result = list(getters.UpTo(2, lambda _: True)(["a", "b", "c"]))
    assert result[0] == ("a", "b")
    assert result[-1] == {}


def test_upto_zero_means_only_the_empty_choice():
    assert list(getters.UpTo(0, lambda _: True)(["a"])) == [{}]
