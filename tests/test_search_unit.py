"""
Unit tests for search.py internals: staff_victory, UCB scoring,
backpropagation, playouts, expansion labelling, advance(), and the
transposition-table integration edge cases.
"""
import math

import pytest

from mtg_ai import actions, decklist, game, search, zones
from mtg_ai.game import canonical_key
from mtg_ai.mana import Mana
from mtg_ai.search import HistoryNode, MCTSInfo, MCTSSearcher


def hand_state():
    gs = game.GameState([0])
    cards = [decklist.Forest(gs), decklist.Island(gs)]
    for card in cards:
        card.zone = zones.Hand(0)
    return gs


def field_state():
    gs = game.GameState([0])
    card = decklist.Forest(gs)
    card.zone = zones.Field(0)
    return gs


def never(_gs):
    return False


# ---------------------------------------------------------------------------
# staff_victory
# ---------------------------------------------------------------------------

def combo_state(*, staff=True, extra_scaler=False, wall_dorks=4, sick=False):
    gs = game.GameState([0])
    if staff:
        decklist.Staff(gs).zone = zones.Field(0)
    battlement = decklist.Battlement(gs)
    battlement.zone = zones.Field(0)
    for _ in range(wall_dorks):
        decklist.VineTrellis(gs).zone = zones.Field(0)
    if extra_scaler:
        second = decklist.Battlement(gs)
        second.zone = zones.Field(0)
        if not sick:
            gs.summoning_sick.add(second.uid)
    if sick:
        gs.summoning_sick.add(battlement.uid)
    return gs


def test_staff_victory_complete_combo():
    assert search.staff_victory(combo_state())


def test_staff_victory_needs_the_staff():
    assert not search.staff_victory(combo_state(staff=False))


def test_staff_victory_needs_five_walls():
    assert not search.staff_victory(combo_state(wall_dorks=3))


def test_staff_victory_blocked_when_only_scaler_is_sick():
    assert not search.staff_victory(combo_state(sick=True))


def test_staff_victory_allows_a_healthy_duplicate_scaler():
    # Two identical Battlements, one sick and one healthy: the healthy one
    # should be enough.  Currently fails because Card.__eq__ is value-based,
    # so the healthy duplicate tests equal to the sick one in the
    # summoning_sick set.
    assert search.staff_victory(combo_state(extra_scaler=True))


# ---------------------------------------------------------------------------
# MCTSSearcher.score
# ---------------------------------------------------------------------------

def test_score_matches_ucb_formula():
    searcher = MCTSSearcher(game.GameState([0]), {}, never, C=2.0)
    root = searcher.root
    root.stats = MCTSInfo(value=0.0, visits=100)
    child = HistoryNode(game.GameState([0]), root)
    child.stats = MCTSInfo(value=6.0, visits=3)
    expected = 2.0 + 2.0 * math.sqrt(math.log(100) / 3)
    assert searcher.score(child) == pytest.approx(expected)


def test_score_of_unvisited_child_is_zero():
    searcher = MCTSSearcher(game.GameState([0]), {}, never, C=1.2)
    root = searcher.root
    root.stats = MCTSInfo(value=0.0, visits=10)
    child = HistoryNode(game.GameState([0]), root)
    assert searcher.score(child) == 0.0


# ---------------------------------------------------------------------------
# backpropagation
# ---------------------------------------------------------------------------

def test_backpropagate_walks_ancestors_and_updates_table():
    gs = hand_state()
    statistics = {}
    searcher = MCTSSearcher(gs, statistics, never, C=1.2)
    children = searcher.root.expand()
    assert len(children) == 2
    grandchild = children[0].expand()[0]

    searcher.backpropogate(grandchild, 0.5)

    for node in (searcher.root, children[0], grandchild):
        assert node.stats.value == 0.5
        assert node.stats.visits == 1
    assert statistics[canonical_key(gs)] == MCTSInfo(value=0.5, visits=1)


# ---------------------------------------------------------------------------
# playout
# ---------------------------------------------------------------------------

def test_playout_rewards_immediate_victory_by_turn():
    searcher = MCTSSearcher(game.GameState([0]), {}, lambda _gs: True, C=1.2)
    node = HistoryNode(field_state())
    assert searcher.playout(node, max_turns=10) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# HistoryNode expansion and records
# ---------------------------------------------------------------------------

def test_expand_labels_children_with_action_and_choice():
    gs = hand_state()
    children = HistoryNode(gs).expand()
    assert len(children) == 2
    assert all(isinstance(child.action, actions.PlayLand) for child in children)
    assert all(child.choice == {} for child in children)


def test_expand_falls_back_to_end_turn_when_nothing_is_possible():
    children = HistoryNode(game.GameState([0])).expand()
    assert len(children) == 1
    assert children[0].action is search.END_TURN


def test_to_record_contains_canonical_key_and_stats():
    gs = hand_state()
    node = HistoryNode(gs)
    child = node.expand()[0]
    assert child.to_record() == {"game_state": canonical_key(child.game_state),
                                 "stats": None}
    child.stats = MCTSInfo(value=1.5, visits=2)
    assert child.to_record()["stats"] == {"value": 1.5, "visits": 2}


# ---------------------------------------------------------------------------
# advance
# ---------------------------------------------------------------------------

def test_advance_plays_out_forced_single_choices():
    gs = game.GameState([0])
    in_hand = decklist.Forest(gs)
    in_hand.zone = zones.Hand(0)
    in_deck = decklist.Forest(gs)
    in_deck.zone = zones.Deck(0, 0)
    gs.land_drops = 1

    result = search.advance(gs)
    field = result.in_zone(zones.Field())
    assert len(field) == 1
    assert field[0].tapped
    assert result.mana_pool == Mana(green=1)
    assert len(result.in_zone(zones.Hand())) == 0


# ---------------------------------------------------------------------------
# transposition-table edge cases
# ---------------------------------------------------------------------------

def test_zero_visit_entries_do_not_crash_explore():
    # A table entry with visits == 0 (e.g. written by save_result) should be
    # treated as unexplored.  Currently score() divides by zero.
    gs = hand_state()
    statistics = {}
    searcher = MCTSSearcher(gs, statistics, never, C=1.2, n_iters=1)
    children = searcher.root.expand()

    statistics[canonical_key(gs)] = MCTSInfo(value=0.0, visits=1)
    for child in children:
        statistics[canonical_key(child.game_state)] = MCTSInfo(value=0.0, visits=1)
    statistics[canonical_key(children[0].game_state)] = MCTSInfo(value=0.0, visits=0)

    searcher.explore()
    assert all(child.stats is not None for child in children)
