"""
TDD tests for the transposition table in MCTSSearcher.

The transposition table stores MCTSInfo keyed by canonical_key(game_state),
allowing stats to accumulate across multiple searcher runs and to be shared
between parallel processes.

All tests in this file should FAIL before the implementation and PASS after.
"""
import pytest
from mtg_ai import actions, decklist, game, search, zones
from mtg_ai.game import canonical_key
from mtg_ai.search import MCTSInfo, MCTSSearcher


def _simple_state():
    """Two forests in hand, one player. Enough for a short MCTS run."""
    gs = game.GameState([0])
    f1 = decklist.Forest(gs)
    f1.zone = zones.Hand(0)
    f2 = decklist.Forest(gs)
    f2.zone = zones.Hand(0)
    return gs


def _any_state_reached(gs: game.GameState) -> bool:
    """Trivial condition — always true. Lets MCTS terminate immediately."""
    return True


def _never(gs: game.GameState) -> bool:
    return False


# ---------------------------------------------------------------------------
# Test 1: statistics dict is populated after explore()
# ---------------------------------------------------------------------------

def test_statistics_populated_after_explore():
    """After explore(), the statistics dict should contain at least one entry."""
    gs = _simple_state()
    statistics = {}
    searcher = MCTSSearcher(gs, statistics, _never, C=1.2, n_iters=5)
    searcher.explore()
    assert len(statistics) > 0


# ---------------------------------------------------------------------------
# Test 2: all keys are canonical tuples
# ---------------------------------------------------------------------------

def test_statistics_keys_are_canonical_tuples():
    """Every key in statistics after explore() must be a tuple."""
    gs = _simple_state()
    statistics = {}
    searcher = MCTSSearcher(gs, statistics, _never, C=1.2, n_iters=5)
    searcher.explore()
    assert len(statistics) > 0, "statistics must be populated (prerequisite)"
    for key in statistics:
        assert isinstance(key, tuple), f"expected tuple key, got {type(key)}"


# ---------------------------------------------------------------------------
# Test 3: root state's canonical key appears in statistics
# ---------------------------------------------------------------------------

def test_root_canonical_key_in_statistics():
    """canonical_key(initial_state) must be a key in statistics after explore()."""
    gs = _simple_state()
    statistics = {}
    searcher = MCTSSearcher(gs, statistics, _never, C=1.2, n_iters=5)
    searcher.explore()
    assert canonical_key(gs) in statistics


# ---------------------------------------------------------------------------
# Test 4: pre-seeded statistics are used by root
# ---------------------------------------------------------------------------

def test_pre_seeded_stats_used_by_root():
    """
    If statistics already contains an entry for the root state, the searcher
    should initialise root.stats from it.  After explore() with n_iters=5,
    root.stats.visits must be >= the pre-seeded 100 visits.
    """
    gs = _simple_state()
    key = canonical_key(gs)
    pre_seeded_visits = 100
    statistics = {key: MCTSInfo(value=1.0, visits=pre_seeded_visits)}
    searcher = MCTSSearcher(gs, statistics, _never, C=1.2, n_iters=5)
    searcher.explore()
    assert searcher.root.stats is not None
    assert searcher.root.stats.visits >= pre_seeded_visits


# ---------------------------------------------------------------------------
# Test 5: shared statistics accumulates across two independent searchers
# ---------------------------------------------------------------------------

def test_shared_statistics_accumulates_across_searchers():
    """
    Two searchers that share a statistics dict should accumulate combined
    visit counts.  After searcher1 finishes, the root canonical key must be
    in statistics.  After searcher2 finishes (on an independently built but
    logically identical state), the visit count must be strictly higher.
    """
    gs1 = _simple_state()
    statistics = {}

    searcher1 = MCTSSearcher(gs1, statistics, _never, C=1.2, n_iters=5)
    searcher1.explore()

    key = canonical_key(gs1)
    assert key in statistics, "searcher1 must populate statistics (prerequisite)"
    visits_after_1 = statistics[key].visits

    # Build the same logical state independently (different Python objects, same key)
    gs2 = _simple_state()
    assert canonical_key(gs2) == key, "gs2 must be logically identical to gs1"

    searcher2 = MCTSSearcher(gs2, statistics, _never, C=1.2, n_iters=5)
    searcher2.explore()

    assert statistics[key].visits > visits_after_1
