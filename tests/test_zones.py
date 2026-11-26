"""
Tests for zones: containment and identity semantics.

A Zone is both "where a card is" and "a set of cards": contains() matches
on zone type plus owner and position, where None acts as a wildcard.
"""
from mtg_ai import decklist, game, zones


def card_in(gs, zone):
    card = decklist.Forest(gs)
    card.zone = zone
    return card


# ---------------------------------------------------------------------------
# contains
# ---------------------------------------------------------------------------

def test_contains_requires_same_zone_type():
    gs = game.GameState([0])
    assert zones.Field(0).contains(card_in(gs, zones.Field(0)))
    assert not zones.Field(0).contains(card_in(gs, zones.Hand(0)))


def test_contains_matches_owner():
    gs = game.GameState([0])
    assert zones.Field(0).contains(card_in(gs, zones.Field(0)))
    assert not zones.Field(0).contains(card_in(gs, zones.Field(1)))


def test_none_owner_matches_any_owner():
    gs = game.GameState([0])
    assert zones.Field().contains(card_in(gs, zones.Field(0)))
    assert zones.Field().contains(card_in(gs, zones.Field(1)))


def test_contains_matches_position():
    gs = game.GameState([0])
    assert zones.Deck(0, 2).contains(card_in(gs, zones.Deck(0, 2)))
    assert not zones.Deck(0, 2).contains(card_in(gs, zones.Deck(0, 3)))


def test_none_position_matches_any_position():
    gs = game.GameState([0])
    assert zones.Deck(0).contains(card_in(gs, zones.Deck(0, 5)))


def test_any_zone_contains_everything():
    gs = game.GameState([0])
    assert zones.Any().contains(card_in(gs, zones.Field(0)))
    assert zones.Any().contains(card_in(gs, zones.Hand(0)))
    assert zones.Any().contains(card_in(gs, zones.Deck(0, 3)))


# ---------------------------------------------------------------------------
# equality, hashing, copying
# ---------------------------------------------------------------------------

def test_equal_zones():
    assert zones.Field(0) == zones.Field(0)
    assert hash(zones.Field(0)) == hash(zones.Field(0, None))


def test_unequal_zones():
    assert zones.Field(0) != zones.Field(1)
    assert zones.Field(0) != zones.Hand(0)
    assert zones.Deck(0, 1) != zones.Deck(0, 2)


def test_zone_copy_is_independent():
    original = zones.Deck(0, 1)
    copy = original.copy()
    assert copy == original
    assert copy is not original
    copy.position = 9
    assert original.position == 1
