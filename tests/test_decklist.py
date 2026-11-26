"""
Direct tests for card definitions that the engine-level tests never touch:
dual lands, gold-mana dorks, and the Wall of Roots counter cost.
"""
from mtg_ai import actions, decklist, game, zones
from mtg_ai.mana import Mana


def on_field(card_class, gs, owner=0):
    card = card_class(gs)
    card.zone = zones.Field(owner)
    return card


def activate(gs, card, index=0):
    ability = card.attrs.activated[index]
    return gs.take_action(ability, ability.get_choices(gs)[0])


def test_plains_taps_for_white():
    gs = game.GameState([0])
    plains = on_field(decklist.Plains, gs)
    g1 = activate(gs, plains)
    assert g1.mana_pool == Mana(white=1)
    assert g1.get(plains).tapped


def test_temple_garden_taps_for_either_color():
    for index, expected in [(0, Mana(white=1)), (1, Mana(green=1))]:
        gs = game.GameState([0])
        garden = on_field(decklist.TempleGarden, gs)
        g1 = activate(gs, garden, index)
        assert g1.mana_pool == expected


def test_breeding_pool_taps_for_either_color():
    for index, expected in [(0, Mana(blue=1)), (1, Mana(green=1))]:
        gs = game.GameState([0])
        pool = on_field(decklist.BreedingPool, gs)
        g1 = activate(gs, pool, index)
        assert g1.mana_pool == expected


def test_vine_trellis_taps_for_green_after_sickness_clears():
    gs = game.GameState([0])
    trellis = decklist.VineTrellis(gs)
    trellis.zone = zones.Hand(0)
    gs.land_drops = 1

    g1 = gs.take_action(actions.Play(trellis), {})
    assert not trellis.attrs.activated[0].get_choices(g1)  # summoning sick

    g2 = g1.take_action(actions.EndTurn(), {})
    g3 = activate(g2, trellis)
    assert g3.mana_pool == Mana(green=1)
    assert g3.get(trellis).tapped


def test_sylvan_caryatid_taps_for_gold():
    gs = game.GameState([0])
    caryatid = on_field(decklist.SylvanCaryatid, gs)
    g1 = activate(gs, caryatid)
    assert g1.mana_pool == Mana(gold=1)
    assert g1.mana_pool.can_pay(Mana(generic=1))


def test_wall_of_roots_pays_with_tap_and_counter():
    gs = game.GameState([0])
    roots = on_field(decklist.WallOfRoots, gs)
    g1 = activate(gs, roots)
    assert g1.mana_pool == Mana(green=1)
    assert g1.get(roots).tapped
    assert g1.get(roots).counters["-0/-1"] == 1
    # tapping was part of the cost, so it cannot activate again
    assert not roots.attrs.activated[0].get_choices(g1)


def test_wall_of_roots_ignores_summoning_sickness():
    # Characterization: the cost taps rather than using the tap symbol,
    # so — unlike real Magic — it can be used the turn it arrives
    gs = game.GameState([0])
    roots = decklist.WallOfRoots(gs)
    roots.zone = zones.Hand(0)
    g1 = gs.take_action(actions.Play(roots), {})
    assert roots.attrs.activated[0].get_choices(g1)
