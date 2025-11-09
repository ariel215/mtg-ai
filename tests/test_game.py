from mtg_ai import cards, game

def test_forest():
    deck = [cards.forest(), cards.forest(), cards.forest()]

    [f1, f2, f3] = deck
    t_add_g = f1.abilities.activated[0]
    gs = game.Game(decks=[deck])

    gs.play(f1)
    assert t_add_g.can(gs.current)
    t_add_g.do(gs.current)

    assert gs.current.mana_pool.green == 1    
