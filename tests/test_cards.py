"""
Tests for the Card flyweight / copy-on-write machinery and card identity.

Card splits into an immutable CardAttributes (_def, shared across copies)
and a mutable CardState (_state, forked before any write).  These tests pin
the isolation guarantees that GameState.copy() relies on.
"""
from mtg_ai import decklist, game, zones


def forest_state():
    gs = game.GameState([0])
    forest = decklist.Forest(gs)
    forest.zone = zones.Hand(0)
    return gs, forest


# ---------------------------------------------------------------------------
# copy-on-write
# ---------------------------------------------------------------------------

def test_copy_shares_definition_but_not_state():
    gs, forest = forest_state()
    copy = gs.copy()
    forest_copy = copy.get(forest)
    assert forest_copy._def is forest._def
    assert forest_copy._state is not forest._state


def test_mutating_copy_does_not_affect_original():
    gs, forest = forest_state()
    copy = gs.copy()
    forest_copy = copy.get(forest)
    forest_copy.zone = zones.Field(0)
    forest_copy.tapped = True
    forest_copy.counters["plus_one"] += 1
    assert zones.Hand(0).contains(forest)
    assert not forest.tapped
    assert forest.counters["plus_one"] == 0


def test_mutating_original_does_not_affect_copy():
    gs, forest = forest_state()
    copy = gs.copy()
    forest_copy = copy.get(forest)
    forest.tapped = True
    assert not forest_copy.tapped


# ---------------------------------------------------------------------------
# identity semantics
# ---------------------------------------------------------------------------

def test_cards_compare_by_value():
    gs = game.GameState([0])
    f1 = decklist.Forest(gs)
    f1.zone = zones.Field(0)
    f2 = decklist.Forest(gs)
    f2.zone = zones.Field(0)
    assert f1 == f2
    assert hash(f1) == hash(f2)
    assert f1 is not f2


def test_card_equality_distinguishes_zone_and_tapped():
    gs = game.GameState([0])
    f1 = decklist.Forest(gs)
    f1.zone = zones.Field(0)
    f2 = decklist.Forest(gs)
    f2.zone = zones.Field(0)
    f2.tapped = True
    assert f1 != f2
    f2.tapped = False
    f2.zone = zones.Hand(0)
    assert f1 != f2


def test_duplicate_cards_collide_in_sets():
    # Characterization: because __eq__/__hash__ are value-based, two distinct
    # but identical cards collapse to one element in any set of cards.
    # This is the hazard behind summoning_sick / staff_victory membership
    # checks on duplicate permanents.
    gs = game.GameState([0])
    f1 = decklist.Forest(gs)
    f1.zone = zones.Field(0)
    f2 = decklist.Forest(gs)
    f2.zone = zones.Field(0)
    assert len({f1, f2}) == 1
    assert f2 in {f1}


# ---------------------------------------------------------------------------
# attrs proxy
# ---------------------------------------------------------------------------

def test_keywords_and_subtypes_are_lowercased():
    gs = game.GameState([0])
    caryatid = decklist.SylvanCaryatid(gs)
    assert caryatid.attrs.keywords == {"defender", "hexproof"}
    assert caryatid.attrs.subtypes == {"wall"}
    forest = decklist.Forest(gs)
    assert forest.attrs.subtypes == {"forest"}


def test_power_is_none_for_lands():
    gs = game.GameState([0])
    forest = decklist.Forest(gs)
    assert forest.attrs.power is None
    assert forest.attrs.toughness is None


def test_mana_value():
    gs = game.GameState([0])
    forest = decklist.Forest(gs)
    trellis = decklist.VineTrellis(gs)
    assert forest.mana_value == 0
    assert trellis.mana_value == 2
