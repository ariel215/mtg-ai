from mtg_ai import game, actions, zones, decklist


def setup_deck(gs, n, owner=0):
    """Create n Forest cards in a deck at positions 0..n-1."""
    cards = [decklist.Forest(gs) for _ in range(n)]
    for i, card in enumerate(cards):
        card.zone = zones.Deck(owner, i)
    return cards


def test_move_to_top_is_last_in_deck():
    gs = game.GameState([0])
    deck = setup_deck(gs, 3)
    target = decklist.Forest(gs)
    target.zone = zones.Hand(0)

    gs1 = gs.take_action(actions.MoveTo(zones.Deck(0, zones.TOP), target), {'card': target})

    result = gs1.in_zone(zones.Deck(0))
    assert gs1.get(target) is result[-1]


def test_move_to_bottom_is_first_in_deck():
    gs = game.GameState([0])
    deck = setup_deck(gs, 3)
    target = decklist.Forest(gs)
    target.zone = zones.Hand(0)

    gs1 = gs.take_action(actions.MoveTo(zones.Deck(0, zones.BOTTOM), target), {'card': target})

    result = gs1.in_zone(zones.Deck(0))
    assert gs1.get(target) is result[0]


def test_move_to_top_preserves_relative_order_of_others():
    gs = game.GameState([0])
    deck = setup_deck(gs, 3)
    target = decklist.Forest(gs)
    target.zone = zones.Hand(0)

    gs1 = gs.take_action(actions.MoveTo(zones.Deck(0, zones.TOP), target), {'card': target})

    result = gs1.in_zone(zones.Deck(0))
    others = [c for c in result if c is not gs1.get(target)]
    assert others == [gs1.get(c) for c in deck]


def test_move_to_bottom_preserves_relative_order_of_others():
    gs = game.GameState([0])
    deck = setup_deck(gs, 3)
    target = decklist.Forest(gs)
    target.zone = zones.Hand(0)

    gs1 = gs.take_action(actions.MoveTo(zones.Deck(0, zones.BOTTOM), target), {'card': target})

    result = gs1.in_zone(zones.Deck(0))
    others = [c for c in result if c is not gs1.get(target)]
    assert others == [gs1.get(c) for c in deck]


def test_move_to_top_does_not_change_positions_of_others():
    gs = game.GameState([0])
    deck = setup_deck(gs, 3)
    target = decklist.Forest(gs)
    target.zone = zones.Hand(0)

    original_positions = {c: c.zone.position for c in deck}

    gs1 = gs.take_action(actions.MoveTo(zones.Deck(0, zones.TOP), target), {'card': target})

    for orig_card, orig_pos in original_positions.items():
        assert gs1.get(orig_card).zone.position == orig_pos
