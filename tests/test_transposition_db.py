"""
TDD tests for SQLite persistence of the MCTS transposition table.

All tests should FAIL before mtg_ai/transposition_db.py is implemented
and PASS after.
"""
from re import M
from mtg_ai.transposition_db import _canonical_hash, _ensure_schema
import stat
import random
from random import randint
import sqlite3
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

def _random_key():
    """
    A key with enough non-trivial state that repeated invocations can 
    be called without ever returning the same state
    """
    gs = game.GameState(players=[0], mana_pool=game.Mana(green=randint(0,4), white=randint(0,4), blue=randint(0,4)))
    card_types = [
        decklist.Forest,
        decklist.Island,
        decklist.Arcades,
        decklist.WallOfRoots,
        decklist.WallOfOmens,
        decklist.SteelWall,
        decklist.BreedingPool,
        decklist.TrophyMage]
    for card_type in card_types:
        ncards = randint(0,4)
        for _ in range(ncards):
            card = card_type(game_state=gs)
            card.zone = random.choice((zones.Field(0),zones.Hand(0), zones.Grave(0)))

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


def test_save_and_load_many_entries(tmp_path):
    db = str(tmp_path / "stats.db")
    keys = [_random_key()[0] for _ in range(transposition_db._BATCH_SIZE * 2)]
    stats = {
        k: MCTSInfo(i,i)
        for i,k in enumerate(keys)
    }
    assert len(stats) == len(keys)
    transposition_db.save_statistics(db,stats)
    loaded = transposition_db.load_statistics(db)
    assert len(loaded) == len(stats)
    assert set(loaded.keys()) == set(stats.keys())


# ---------------------------------------------------------------------------
# Test 4: loading from a non-existent path returns an empty dict (not an error)
# ---------------------------------------------------------------------------

def test_load_from_nonexistent_path(tmp_path):
    db = str(tmp_path / "does_not_exist.db")
    assert not os.path.exists(db)
    result = transposition_db.load_statistics(db)
    assert result == {}


# --------------------------------------
# Test 4a: saving game results works as expected
# -----------------------------------------

def test_save_results(tmp_path):
    db = str(tmp_path / "results.db")
    key,_  = _simple_key()
    transposition_db.save_statistics(db, {key: MCTSInfo(value=0.1, visits=10)})
    transposition_db.save_result(db, key,3)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        result = conn.execute("SELECT * from mcts_results").fetchall()
    assert len(result) == 1

# --------------------------------------
# Test 4b: saving game results inserts game state when it is not already in the database
# -----------------------------------------

def test_save_results_without_gamestate(tmp_path):
    db = str(tmp_path / "results.db")
    key,_  = _simple_key()
    chash = transposition_db._canonical_hash(key)
    with sqlite3.connect(db) as conn:
        transposition_db._ensure_schema(conn)
        gs_row = conn.execute("SELECT id from game_states where canonical_hash = ?", (chash,)).fetchone()
        assert gs_row is None
    transposition_db.save_result(db, key,3)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        result = conn.execute("SELECT * from mcts_results").fetchall()
        gs_row = conn.execute("SELECT id from game_states where canonical_hash = ?", (chash,)).fetchone()
        gs_id = gs_row['id']
    assert len(result) == 1
    assert result[0]['id'] == gs_id


def test_load_all_results(tmp_path):
    db = str(tmp_path / "results.db")
    initial_keys = [_random_key()[0], _random_key()[0], _random_key()[0]]
    other_keys = [_random_key()[0], _random_key()[0], _random_key()[0]]
    stats = {
        initial_keys[0]: MCTSInfo(0.1, 10),
        initial_keys[1]: MCTSInfo(0.4, 3),
        initial_keys[2]: MCTSInfo(1, 1),
        
        other_keys[0]: MCTSInfo(0.1, 10),
        other_keys[1]: MCTSInfo(0.4, 3),
        other_keys[2]: MCTSInfo(1, 1)
    }
    transposition_db.save_statistics(db,stats)
    for r,k in enumerate(initial_keys):
        transposition_db.save_result(db,k,r) 
    results = transposition_db.load_all_results(db)
    assert all(k in results for k in initial_keys)
    for r,k in enumerate(initial_keys):
        assert results[k] == r

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

@pytest.mark.parametrize(["key"],[canonical_key,info])
def test_roundtrip_preserves_canonical_key_structure(tmp_path,key):
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

def _insert(tmp_path):
    db = str(tmp_path / "stats.db")
    keys = [_random_key()[0] for _ in range(transposition_db._BATCH_SIZE * 2)]
    stats = {
        k: MCTSInfo(i,i)
        for i,k in enumerate(keys)
    }
    assert len(stats) == len(keys)
    transposition_db.save_statistics(db,stats)
    loaded = transposition_db.load_statistics(db)
    assert len(loaded) >= len(stats)
    return True

@pytest.mark.skipif("not config.getoption('--run-slow')")
def test_concurrent(tmp_path):
    n_connections = 6
    import multiprocessing
    with multiprocessing.Pool() as pool:
        results = pool.map(_insert, [tmp_path] * n_connections)
    assert all(results)

# ---------------------------------------------------------------------------
# LazyTranspositionDB tests
# ---------------------------------------------------------------------------

def test_lazy_lookup_hit(tmp_path):
    """Keys present in the DB are returned on demand."""
    db = str(tmp_path / "stats.db")
    key, _ = _simple_key()
    transposition_db.save_statistics(db, {key: MCTSInfo(value=1.5, visits=3)})

    with transposition_db.LazyTranspositionDB(db) as lazy:
        assert key in lazy
        info = lazy.get(key)
        assert info is not None
        assert info.value == pytest.approx(1.5)
        assert info.visits == 3


def test_lazy_lookup_miss(tmp_path):
    """Keys absent from the DB return None / raise KeyError as expected."""
    db = str(tmp_path / "stats.db")
    key, _ = _simple_key()

    with transposition_db.LazyTranspositionDB(db) as lazy:
        assert key not in lazy
        assert lazy.get(key) is None
        with pytest.raises(KeyError):
            _ = lazy[key]


def test_lazy_flush_overwrites(tmp_path):
    """flush() writes dirty entries and overwrites existing value/visits."""
    db = str(tmp_path / "stats.db")
    key, _ = _simple_key()
    transposition_db.save_statistics(db, {key: MCTSInfo(value=1.0, visits=10)})

    with transposition_db.LazyTranspositionDB(db) as lazy:
        lazy[key] = MCTSInfo(value=9.0, visits=99)
        lazy.flush()

    loaded = transposition_db.load_statistics(db)
    assert loaded[key].value == pytest.approx(9.0)
    assert loaded[key].visits == 99


def test_lazy_merge_accumulates(tmp_path):
    """merge() accumulates value and visits into existing DB entries."""
    db = str(tmp_path / "stats.db")
    key, _ = _simple_key()
    transposition_db.save_statistics(db, {key: MCTSInfo(value=1.0, visits=10)})

    with transposition_db.LazyTranspositionDB(db) as lazy:
        lazy[key] = MCTSInfo(value=0.5, visits=5)
        lazy.merge()

    loaded = transposition_db.load_statistics(db)
    assert loaded[key].value == pytest.approx(1.5)
    assert loaded[key].visits == 15


def test_lazy_cache_stays_small(tmp_path):
    """Only fetched keys end up in the cache; untouched keys are not loaded."""
    db = str(tmp_path / "stats.db")
    key1, _ = _simple_key()
    key2, _ = _richer_key()
    transposition_db.save_statistics(db, {
        key1: MCTSInfo(value=1.0, visits=1),
        key2: MCTSInfo(value=2.0, visits=2),
    })

    with transposition_db.LazyTranspositionDB(db) as lazy:
        _ = lazy.get(key1)
        assert len(lazy._cache) == 1
        assert key1 in lazy._cache
        assert key2 not in lazy._cache


def test_lazy_items_compatible_with_save_statistics(tmp_path):
    """items() makes LazyTranspositionDB usable with save_statistics()."""
    db = str(tmp_path / "stats.db")
    key, _ = _simple_key()

    with transposition_db.LazyTranspositionDB(db) as lazy:
        lazy[key] = MCTSInfo(value=3.0, visits=7)
        # Pass lazy directly to save_statistics via its items() method
        transposition_db.save_statistics(db, lazy)  # type: ignore[arg-type]

    loaded = transposition_db.load_statistics(db)
    assert loaded[key].value == pytest.approx(3.0)
    assert loaded[key].visits == 7


def test_lazy_integration_with_mcts_searcher(tmp_path):
    """
    LazyTranspositionDB seeds a searcher from the DB and accumulates new stats
    back via flush(), without ever loading the full table into memory.
    """
    db = str(tmp_path / "stats.db")

    def build_state():
        gs = game.GameState([0])
        f1 = decklist.Forest(gs)
        f1.zone = zones.Hand(0)
        f2 = decklist.Forest(gs)
        f2.zone = zones.Hand(0)
        return gs

    # First run — populate DB
    gs1 = build_state()
    stats1: dict = {}
    s1 = MCTSSearcher(gs1, stats1, _never, C=1.2, n_iters=5)
    s1.explore()
    assert s1.root.stats is not None
    visits_after_s1 = s1.root.stats.visits
    transposition_db.save_statistics(db, stats1)

    # Second run — use lazy DB instead of loading everything
    gs2 = build_state()
    with transposition_db.LazyTranspositionDB(db) as lazy:
        s2 = MCTSSearcher(gs2, lazy, _never, C=1.2, n_iters=5)  # type: ignore[arg-type]
        s2.explore()
        assert s2.root.stats is not None
        assert s2.root.stats.visits > visits_after_s1
        lazy.flush()

def _insert_lazy(db):
    key = _random_key()
    value = MCTSInfo(randint(1,4), randint(3,6))
    with transposition_db.LazyTranspositionDB(db) as lazy:
        lazy[key] = MCTSInfo(value=3.0, visits=7)
        # Pass lazy directly to save_statistics via its items() method
        transposition_db.save_statistics(db, lazy)  # type: ignore[arg-type]


def test_lazy_items_concurrent(tmp_path):
    """try and run LazyTranspositionDB from multiple processes simultaneously"""
    n_connections = 2
    db = str(tmp_path / "stats.db")
    import multiprocessing
    with multiprocessing.Pool() as pool:
        results = pool.map(_insert_lazy, [db] * n_connections)
    assert all(results)

