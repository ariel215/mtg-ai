"""
Tests for canonical_key(gs) — a deterministic, UID-independent tuple
representation of GameState suitable for use as a transposition-table key
across processes.

These are TDD / contract tests. canonical_key is expected to be importable
from mtg_ai.game.
"""
import pytest
from mtg_ai import game, actions, zones, mana, decklist
from mtg_ai.game import canonical_key


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fresh_state(*specs):
    """Build a GameState. Each spec is (CardClass, zone_instance)."""
    gs = game.GameState([0])
    cards = []
    for CardClass, zone in specs:
        card = CardClass(gs)
        card.zone = zone
        cards.append(card)
    return gs, cards


# ---------------------------------------------------------------------------
# Structure: the key must be a plain-Python, hashable tuple
# ---------------------------------------------------------------------------

def test_returns_tuple():
    gs, _ = fresh_state((decklist.Forest, zones.Field(0)))
    assert isinstance(canonical_key(gs), tuple)


def test_key_is_hashable():
    """Key must be usable as a dict key (needed for the transposition table)."""
    gs, _ = fresh_state((decklist.Forest, zones.Field(0)))
    key = canonical_key(gs)
    d = {key: 1}
    assert d[canonical_key(gs)] == 1


def test_key_contains_only_primitives():
    """
    Key must consist only of int, float, str, bool, None, tuple, or frozenset
    — no Card objects, no lambdas, nothing with id-based identity.
    This guarantees the key serialises with plain pickle across processes.
    """
    gs, _ = fresh_state((decklist.Forest, zones.Field(0)))

    def check(obj):
        if isinstance(obj, (tuple, frozenset)):
            for item in obj:
                check(item)
        else:
            assert isinstance(obj, (int, float, str, bool, type(None))), (
                f"Non-primitive found in canonical key: {type(obj).__name__!r}"
            )

    check(canonical_key(gs))


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_same_state_same_key():
    gs, _ = fresh_state((decklist.Forest, zones.Field(0)))
    assert canonical_key(gs) == canonical_key(gs)


def test_copy_same_key():
    """A copied game state has the same canonical key as the original."""
    gs, _ = fresh_state((decklist.Forest, zones.Field(0)))
    assert canonical_key(gs) == canonical_key(gs.copy())


def test_independently_constructed_equal_states():
    """Two GameState objects built the same way produce the same key."""
    g1, _ = fresh_state((decklist.Forest, zones.Field(0)))
    g2, _ = fresh_state((decklist.Forest, zones.Field(0)))
    assert canonical_key(g1) == canonical_key(g2)


def test_uid_independent():
    """
    Extra objects created and discarded before building the real state must
    not change the key — UIDs are process-local implementation details.
    """
    g1 = game.GameState([0])
    _discarded = decklist.Forest(g1)   # burns a UID
    f = decklist.Forest(g1)
    f.zone = zones.Field(0)

    g2 = game.GameState([0])
    f2 = decklist.Forest(g2)          # gets UID 0, not UID 1
    f2.zone = zones.Field(0)

    assert canonical_key(g1) == canonical_key(g2)


# ---------------------------------------------------------------------------
# Sensitivity: different logical states → different keys
# ---------------------------------------------------------------------------

def test_different_zone_type():
    g1, _ = fresh_state((decklist.Forest, zones.Field(0)))
    g2, _ = fresh_state((decklist.Forest, zones.Hand(0)))
    assert canonical_key(g1) != canonical_key(g2)


def test_different_card_class():
    g1, _ = fresh_state((decklist.Forest, zones.Field(0)))
    g2, _ = fresh_state((decklist.Plains, zones.Field(0)))
    assert canonical_key(g1) != canonical_key(g2)


def test_different_card_count():
    g1, _ = fresh_state((decklist.Forest, zones.Field(0)))
    g2, _ = fresh_state(
        (decklist.Forest, zones.Field(0)),
        (decklist.Forest, zones.Field(0)),
    )
    assert canonical_key(g1) != canonical_key(g2)


def test_tapped_vs_untapped():
    g1, _ = fresh_state((decklist.Forest, zones.Field(0)))
    [f] = g1.objects
    ability = f.attrs.activated[0]
    g2 = g1.take_action(ability, ability.get_choices(g1)[0])
    assert canonical_key(g1) != canonical_key(g2)


def test_different_mana_pool():
    g1, _ = fresh_state((decklist.Forest, zones.Field(0)))
    g1.mana_pool = mana.Mana(green=1)
    g2, _ = fresh_state((decklist.Forest, zones.Field(0)))
    g2.mana_pool = mana.Mana(green=2)
    assert canonical_key(g1) != canonical_key(g2)


def test_different_turn_number():
    gs, _ = fresh_state((decklist.Forest, zones.Field(0)))
    g2 = gs.copy()
    g2.turn_number += 1
    assert canonical_key(gs) != canonical_key(g2)


def test_different_land_drops():
    """Remaining land drops are part of game state and must affect the key."""
    gs, _ = fresh_state((decklist.Forest, zones.Field(0)))
    g2 = gs.copy()
    g2.land_drops = 0
    assert canonical_key(gs) != canonical_key(g2)


def test_summoning_sick_vs_not():
    """
    A card with summoning sickness and the same card without it must produce
    different keys, so MCTS doesn't confuse pre- and post-EndTurn positions.
    """
    g1, _ = fresh_state((decklist.Battlement, zones.Field(0)))
    [b] = g1.objects
    g1.summoning_sick.add(b.uid)

    g2, _ = fresh_state((decklist.Battlement, zones.Field(0)))
    # summoning_sick is empty in g2

    assert canonical_key(g1) != canonical_key(g2)


def test_counters_affect_key():
    """Cards with different counters must produce different keys."""
    gs, _ = fresh_state((decklist.Forest, zones.Field(0)))
    [f] = gs.objects

    g2 = gs.copy()
    g2.get(f)._state.counters['plus_one'] = 1

    assert canonical_key(gs) != canonical_key(g2)


def test_zero_counters_equal_to_no_counters():
    """
    A defaultdict entry with count 0 is semantically absent.
    Accessing a missing counter key must not create a spurious difference.
    """
    gs, _ = fresh_state((decklist.Forest, zones.Field(0)))
    [f] = gs.objects

    g2 = gs.copy()
    _ = g2.get(f)._state.counters['plus_one']  # triggers defaultdict insertion at 0

    assert canonical_key(gs) == canonical_key(g2)


# ---------------------------------------------------------------------------
# Transpositions: same logical state, different path → same key
# ---------------------------------------------------------------------------

def test_same_state_via_copy():
    """
    Identical board reached by copying rather than re-constructing
    should give the same key (basic sanity for transpositions).
    """
    gs = game.GameState([0])
    f1 = decklist.Forest(gs)
    f2 = decklist.Forest(gs)
    f1.zone = zones.Field(0)
    f2.zone = zones.Field(0)

    ability = f1.attrs.activated[0]
    g_original = gs.take_action(ability, ability.get_choices(gs)[0])

    gs_copy = gs.copy()
    f1_in_copy = gs_copy.get(f1)
    act_copy = f1_in_copy.attrs.activated[0]
    g_copy = gs_copy.take_action(act_copy, act_copy.get_choices(gs_copy)[0])

    assert canonical_key(g_original) == canonical_key(g_copy)


def test_card_order_in_hand_irrelevant():
    """
    Hand is unordered in MTG. Two states that differ only in which UID was
    assigned to which Forest in hand should compare equal.
    """
    g1 = game.GameState([0])
    a = decklist.Forest(g1)
    b = decklist.WallOfOmens(g1)
    a.zone = zones.Hand(0)
    b.zone = zones.Hand(0)

    g2 = game.GameState([0])
    # Reversed construction order → different UIDs for the same logical state
    b2 = decklist.WallOfOmens(g2)
    a2 = decklist.Forest(g2)
    a2.zone = zones.Hand(0)
    b2.zone = zones.Hand(0)

    assert canonical_key(g1) == canonical_key(g2)
