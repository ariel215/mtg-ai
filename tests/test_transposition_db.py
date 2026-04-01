"""
TDD tests for SQLite persistence of the MCTS transposition table.

All tests should FAIL before mtg_ai/transposition_db.py is implemented
and PASS after.
"""
import os
import pytest
from mtg_ai import decklist, game, search, zones
from mtg_ai.game import canonical_key
from mtg_ai.search import MCTSInfo, MCTSSearcher
from mtg_ai import transposition_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_key():
    """Build a canonical key from a simple game state (two forests in hand)."""
    gs = game.GameState([0])
    f1 = decklist.Forest(gs)
    f1.zone = zones.Hand(0)
    f2 = decklist.Forest(gs)
    f2.zone = zones.Hand(0)
    return canonical_key(gs), gs


def _richer_key():
    """
    A key with non-trivial mana, a counter, and two distinct object types —
    exercises the full decompose/recompose path.
    """
    gs = game.GameState([0], mana_pool=game.Mana(green=3, white=1))
    forest = decklist.Forest(gs)
    forest.zone = zones.Field(0)
    forest.tapped = True
    wall = decklist.WallOfRoots(gs)
    wall.zone = zones.Field(0)
    wall.counters['minus_one'] += 1
    return canonical_key(gs), gs


def _never(_gs):
    return False


# ---------------------------------------------------------------------------
# Test 1: empty dict round-trips cleanly
# ---------------------------------------------------------------------------

def test_save_and_load_empty(tmp_path):
    db = str(tmp_path / "stats.db")
    transposition_db.save_statistics(db, {})
    result = transposition_db.load_statistics(db)
    assert result == {}


# ---------------------------------------------------------------------------
# Test 2: single entry round-trips with correct key and values
# ---------------------------------------------------------------------------

def test_save_and_load_single_entry(tmp_path):
    db = str(tmp_path / "stats.db")
    key, _ = _simple_key()
    stats = {key: MCTSInfo(value=1.5, visits=3)}
    transposition_db.save_statistics(db, stats)
    loaded = transposition_db.load_statistics(db)
    assert len(loaded) == 1
    assert key in loaded
    assert loaded[key].value == pytest.approx(1.5)
    assert loaded[key].visits == 3


# ---------------------------------------------------------------------------
# Test 3: multiple distinct entries all survive the round-trip
# ---------------------------------------------------------------------------

def test_save_and_load_multiple_entries(tmp_path):
    db = str(tmp_path / "stats.db")
    key1, _ = _simple_key()
    key2, _ = _richer_key()
    assert key1 != key2
    stats = {
        key1: MCTSInfo(value=0.5, visits=10),
        key2: MCTSInfo(value=2.0, visits=7),
    }
    transposition_db.save_statistics(db, stats)
    loaded = transposition_db.load_statistics(db)
    assert len(loaded) == 2
    assert loaded[key1].visits == 10
    assert loaded[key2].visits == 7


# ---------------------------------------------------------------------------
# Test 4: loading from a non-existent path returns an empty dict (not an error)
# ---------------------------------------------------------------------------

def test_load_from_nonexistent_path(tmp_path):
    db = str(tmp_path / "does_not_exist.db")
    assert not os.path.exists(db)
    result = transposition_db.load_statistics(db)
    assert result == {}


# ---------------------------------------------------------------------------
# Test 5: merge_statistics accumulates value and visits
# ---------------------------------------------------------------------------

def test_merge_accumulates(tmp_path):
    db = str(tmp_path / "stats.db")
    key, _ = _simple_key()
    transposition_db.save_statistics(db, {key: MCTSInfo(value=1.0, visits=10)})
    transposition_db.merge_statistics(db, {key: MCTSInfo(value=0.5, visits=5)})
    loaded = transposition_db.load_statistics(db)
    assert loaded[key].value == pytest.approx(1.5)
    assert loaded[key].visits == 15


# ---------------------------------------------------------------------------
# Test 6: save_statistics overwrites (does not accumulate)
# ---------------------------------------------------------------------------

def test_save_overwrites(tmp_path):
    db = str(tmp_path / "stats.db")
    key, _ = _simple_key()
    transposition_db.save_statistics(db, {key: MCTSInfo(value=1.0, visits=10)})
    transposition_db.save_statistics(db, {key: MCTSInfo(value=2.0, visits=3)})
    loaded = transposition_db.load_statistics(db)
    assert loaded[key].value == pytest.approx(2.0)
    assert loaded[key].visits == 3


# ---------------------------------------------------------------------------
# Test 7: round-trip preserves the exact canonical key tuple structure
# ---------------------------------------------------------------------------

def test_roundtrip_preserves_canonical_key_structure(tmp_path):
    """
    The reconstructed key from the DB must be bit-for-bit identical to the
    original canonical_key() output, including counters, mana, zone fields.
    """
    db = str(tmp_path / "stats.db")
    key, _ = _richer_key()
    transposition_db.save_statistics(db, {key: MCTSInfo(value=1.0, visits=1)})
    loaded = transposition_db.load_statistics(db)
    reconstructed_key = next(iter(loaded))
    assert reconstructed_key == key


# ---------------------------------------------------------------------------
# Test 8: integration — saved stats seed a second MCTSSearcher
# ---------------------------------------------------------------------------

def test_integration_with_mcts_searcher(tmp_path):
    """
    Run searcher1, save its statistics, load them into a fresh dict, start
    searcher2 with that dict.  After seeding, searcher2.root should already
    have visit counts from the first run (seeded via _seed_from_table).
    """
    db = str(tmp_path / "stats.db")

    def build_state():
        gs = game.GameState([0])
        f1 = decklist.Forest(gs)
        f1.zone = zones.Hand(0)
        f2 = decklist.Forest(gs)
        f2.zone = zones.Hand(0)
        return gs

    # Run searcher1
    gs1 = build_state()
    stats1 = {}
    s1 = MCTSSearcher(gs1, stats1, _never, C=1.2, n_iters=5)
    s1.explore()
    visits_after_s1 = s1.root.stats.visits

    # Persist
    transposition_db.save_statistics(db, stats1)

    # Load into fresh dict
    stats2 = transposition_db.load_statistics(db)
    assert canonical_key(gs1) in stats2

    # Run searcher2 — it starts with prior knowledge
    gs2 = build_state()
    s2 = MCTSSearcher(gs2, stats2, _never, C=1.2, n_iters=5)
    s2.explore()

    # Root was seeded, so visits include the pre-loaded count plus this run's
    assert s2.root.stats.visits > visits_after_s1
