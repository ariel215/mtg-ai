"""
Tests for Mana: parsing, arithmetic, affordability, and payment.

Contract being pinned:
- parse: letters map to colors per the abbreviation table, digits are generic
- can_pay: gold mana substitutes for any color; generic costs are payable
  with any kind of mana; colorless requirements need colorless mana
- __sub__: paying a cost leaves no negative fields and conserves totals
"""
import pytest
from dataclasses import asdict

from mtg_ai.mana import Mana


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------

def test_parse_single_letters():
    assert Mana.parse("w") == Mana(white=1)
    assert Mana.parse("u") == Mana(blue=1)
    assert Mana.parse("b") == Mana(black=1)
    assert Mana.parse("r") == Mana(red=1)
    assert Mana.parse("g") == Mana(green=1)
    assert Mana.parse("a") == Mana(gold=1)
    assert Mana.parse("c") == Mana(colorless=1)


def test_parse_repeated_letters():
    assert Mana.parse("gg") == Mana(green=2)


def test_parse_mixed_colors():
    assert Mana.parse("wub") == Mana(white=1, blue=1, black=1)


def test_parse_digits_are_generic():
    assert Mana.parse("2gg") == Mana(generic=2, green=2)


def test_parse_is_case_insensitive():
    assert Mana.parse("GG") == Mana(green=2)


def test_parse_empty_string():
    assert Mana.parse("") == Mana()


# ---------------------------------------------------------------------------
# equality and copying
# ---------------------------------------------------------------------------

def test_equal_manas():
    assert Mana(green=1) == Mana(green=1)


def test_unequal_manas():
    assert Mana(green=1) != Mana(green=2)
    assert Mana(green=1) != Mana(blue=1)


def test_not_equal_to_other_type():
    assert Mana(green=1) != "green"


def test_copy_is_independent():
    original = Mana(green=1)
    copy = original.copy()
    copy.green = 5
    assert original == Mana(green=1)


# ---------------------------------------------------------------------------
# arithmetic
# ---------------------------------------------------------------------------

def test_add_combines_pools():
    assert Mana(green=1) + Mana(blue=1) == Mana(green=1, blue=1)


def test_add_leaves_operands_unchanged():
    a, b = Mana(green=1), Mana(blue=1)
    a + b
    assert a == Mana(green=1)
    assert b == Mana(blue=1)


def test_iadd_mutates_in_place():
    pool = Mana(green=1)
    pool += Mana(green=1)
    assert pool == Mana(green=2)


def test_mul_scales_every_field():
    assert Mana(green=1, generic=2) * 3 == Mana(green=3, generic=6)


def test_mul_leaves_operand_unchanged():
    pool = Mana(green=1)
    pool * 3
    assert pool == Mana(green=1)


def test_mana_value_sums_all_fields():
    assert Mana(white=1, blue=1, generic=2).mana_value == 4
    assert Mana(gold=2).mana_value == 2


# ---------------------------------------------------------------------------
# can_pay
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pool,cost", [
    # exact colored payment
    (Mana(green=2), Mana(green=2)),
    (Mana(green=5), Mana(green=2, generic=1)),
    # generic is payable with any kind of mana
    (Mana(green=1), Mana(generic=1)),
    (Mana(colorless=1), Mana(generic=1)),
    (Mana(gold=1), Mana(generic=1)),
    # gold covers colored deficits
    (Mana(gold=3), Mana(white=1, black=1, generic=1)),
    (Mana(gold=2), Mana(white=2)),
    (Mana(green=1, gold=1), Mana(green=2)),
])
def test_can_pay_true(pool, cost):
    assert pool.can_pay(cost)


@pytest.mark.parametrize("pool,cost", [
    (Mana(green=1), Mana(green=2)),
    (Mana(green=1), Mana(generic=2)),
    (Mana(gold=1), Mana(white=2)),
    (Mana(gold=2), Mana(white=1, blue=2)),
    # colored mana cannot pay a colorless requirement
    (Mana(green=1), Mana(colorless=1)),
])
def test_can_pay_false(pool, cost):
    assert not pool.can_pay(cost)


def test_can_pay_does_not_mutate_pool():
    pool = Mana(gold=2, green=1)
    pool.can_pay(Mana(green=2))
    assert pool == Mana(gold=2, green=1)


# ---------------------------------------------------------------------------
# paying costs (__sub__ / __isub__)
# ---------------------------------------------------------------------------

def test_sub_exact_colored():
    assert Mana(green=2) - Mana(green=1) == Mana(green=1)


def test_sub_colored_pays_generic():
    assert Mana(green=3) - Mana(generic=1) == Mana(green=2)


def test_sub_drains_colorless_before_colored_for_generic():
    assert Mana(colorless=1, green=1) - Mana(generic=1) == Mana(green=1)


def test_sub_drains_colored_before_gold_for_generic():
    assert Mana(white=1, gold=1) - Mana(generic=1) == Mana(gold=1)


def test_sub_gold_pays_generic():
    assert Mana(gold=2) - Mana(generic=2) == Mana()


def test_sub_gold_covers_colored_deficit():
    assert Mana(gold=2) - Mana(blue=2) == Mana()
    assert Mana(gold=1, blue=1) - Mana(blue=2) == Mana()


def test_sub_leaves_operands_unchanged():
    pool, cost = Mana(green=2), Mana(green=1)
    pool - cost
    assert pool == Mana(green=2)
    assert cost == Mana(green=1)


@pytest.mark.parametrize("pool,cost", [
    (Mana(green=3), Mana(green=1, generic=1)),
    (Mana(white=1, blue=1), Mana(white=1, blue=1)),
    (Mana(colorless=2), Mana(colorless=1, generic=1)),
    (Mana(gold=2), Mana(blue=2)),
    (Mana(white=1, gold=1), Mana(generic=1)),
])
def test_sub_never_negative(pool, cost):
    remainder = pool - cost
    assert all(value >= 0 for value in asdict(remainder).values())
