"""
Tests for individual Action classes and the possible_actions gate:
timing rules, no-op safeguards, and per-turn state resets.
"""
from mtg_ai import actions, decklist, game, zones
from mtg_ai.game import CardType
from mtg_ai.mana import Mana


# ---------------------------------------------------------------------------
# possible_actions
# ---------------------------------------------------------------------------

def test_possible_actions_excludes_actions_with_no_choices():
    gs = game.GameState([0])
    forest = decklist.Forest(gs)
    forest.zone = zones.Hand(0)
    gs.land_drops = 0
    assert actions.possible_actions(gs) == []


def test_possible_actions_returns_only_stack_triggers_when_pending():
    gs = game.GameState([0])
    omens = decklist.WallOfOmens(gs)
    omens.zone = zones.Hand(0)
    g1 = gs.take_action(actions.Play(omens), {})
    assert len(g1.triggers) == 1
    possible = actions.possible_actions(g1)
    assert len(possible) == 1
    assert isinstance(possible[0], actions.StackTriggers)


# ---------------------------------------------------------------------------
# spell timing
# ---------------------------------------------------------------------------

def test_creatures_cannot_be_cast_while_stack_nonempty():
    g0 = game.GameState([0])
    steel = decklist.SteelWall(g0)
    steel.zone = zones.Field(0)
    unsummon1 = decklist.Unsummon(g0)
    unsummon1.zone = zones.Hand(0)
    unsummon2 = decklist.Unsummon(g0)
    unsummon2.zone = zones.Hand(0)
    trellis = decklist.VineTrellis(g0)
    trellis.zone = zones.Hand(0)
    g0.mana_pool += Mana(blue=2, green=2)

    cast = actions.CastSpell(unsummon1)
    g1 = g0.take_action(cast, cast.get_choices(g0)[0])
    assert len(g1.in_zone(zones.Stack())) == 1

    # instants may still be cast
    assert actions.CastSpell(unsummon2).get_choices(g1)
    # creatures (and sorceries) may not
    assert actions.CastSpell(trellis).get_choices(g1) == []


# ---------------------------------------------------------------------------
# Draw
# ---------------------------------------------------------------------------

def test_draw_pulls_deck_top_into_hand():
    gs = game.GameState([0])
    bottom = decklist.Forest(gs)
    bottom.zone = zones.Deck(0, 0)
    top = decklist.Forest(gs)
    top.zone = zones.Deck(0, 1)

    draw = actions.Draw(player=0)
    g1 = gs.take_action(draw, draw.get_choices(gs)[0])
    assert zones.Hand(0).contains(g1.get(top))
    assert len(g1.in_zone(zones.Deck(0))) == 1
    assert g1.in_zone(zones.Deck(0)) == [g1.get(bottom)]


def test_draw_from_empty_deck_is_a_silent_noop():
    # Characterization: drawing from an empty deck does nothing (the
    # game-loss rule is a todo in actions.Draw.do)
    gs = game.GameState([0])
    draw = actions.Draw(player=0)
    g1 = gs.take_action(draw, draw.get_choices(gs)[0])
    assert len(g1.in_zone(zones.Hand(0))) == 0
    assert len(g1.in_zone(zones.Deck(0))) == 0


# ---------------------------------------------------------------------------
# Sacrifice / Tap / AddCounter / PayMana
# ---------------------------------------------------------------------------

def test_sacrifice_moves_field_card_to_grave():
    gs = game.GameState([0])
    forest = decklist.Forest(gs)
    forest.zone = zones.Field(0)
    sacrifice = actions.Sacrifice(forest)
    g1 = gs.take_action(sacrifice, sacrifice.get_choices(gs)[0])
    assert zones.Grave(0).contains(g1.get(forest))
    assert len(g1.in_zone(zones.Field())) == 0


def test_sacrifice_requires_card_on_field():
    gs = game.GameState([0])
    forest = decklist.Forest(gs)
    forest.zone = zones.Hand(0)
    assert actions.Sacrifice(forest).get_choices(gs) == []


def test_tap_targets_untapped_matching_cards_only():
    gs = game.GameState([0])
    saruli = decklist.Saruli(gs)
    saruli.zone = zones.Field(0)
    steel = decklist.SteelWall(gs)
    steel.zone = zones.Field(0)
    steel.tapped = True

    tap = actions.Tap(lambda c: CardType.Creature in c.attrs.types)
    choices = tap.get_choices(gs)
    assert [gs.get(c) for c in [choice["card"] for choice in choices]] == [saruli]
    g1 = gs.take_action(tap, choices[0])
    assert g1.get(saruli).tapped
    assert g1.get(steel).tapped


def test_add_counter_increments():
    gs = game.GameState([0])
    forest = decklist.Forest(gs)
    forest.zone = zones.Field(0)
    add = actions.AddCounter(forest, "plus_one")
    g1 = gs.take_action(add, add.get_choices(gs)[0])
    assert g1.get(forest).counters["plus_one"] == 1
    assert gs.get(forest).counters["plus_one"] == 0


def test_add_counter_respects_zone_restriction():
    gs = game.GameState([0])
    forest = decklist.Forest(gs)
    forest.zone = zones.Hand(0)
    assert actions.AddCounter(forest, "plus_one", zones.Field()).get_choices(gs) == []


def test_pay_mana_choices_respect_pool():
    gs = game.GameState([0])
    pay = actions.PayMana(mana=Mana(green=1))
    assert pay.get_choices(gs) == []
    gs.mana_pool += Mana(green=1)
    g1 = gs.take_action(pay, pay.get_choices(gs)[0])
    assert g1.mana_pool == Mana()


# ---------------------------------------------------------------------------
# Shuffle / ResolveStack / EndTurn
# ---------------------------------------------------------------------------

def test_shuffle_is_currently_a_noop():
    # Characterization: the deck order is unchanged (real shuffling unimplemented)
    gs = game.GameState([0])
    deck = [decklist.Forest(gs) for _ in range(3)]
    for i, card in enumerate(deck):
        card.zone = zones.Deck(0, i)
    g1 = gs.take_action(actions.Shuffle(), {})
    assert g1.in_zone(zones.Deck(0)) == [g1.get(c) for c in deck]


def test_resolve_empty_stack_returns_same_state():
    gs = game.GameState([0])
    assert gs.resolve_stack() is gs


def test_end_turn_resets_per_turn_state():
    gs = game.GameState([0])
    forest = decklist.Forest(gs)
    forest.zone = zones.Field(0)
    forest.tapped = True
    battlement = decklist.Battlement(gs)
    battlement.zone = zones.Field(0)
    gs.summoning_sick.add(battlement)
    gs.mana_pool += Mana(green=2)
    gs.land_drops = 0

    g1 = gs.take_action(actions.EndTurn(), {})
    assert g1.mana_pool == Mana()
    assert not g1.get(forest).tapped
    assert len(g1.summoning_sick) == 0
    assert g1.land_drops == 1
    assert g1.turn_number == 2
    assert g1.active_player == 0  # single player: rotation wraps to 0
