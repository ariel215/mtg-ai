from mtg_ai import cards, game

def test_forest():
    g0 = game.GameState([0])
    deck = [cards.forest(g0), cards.forest(g0), cards.forest(g0)]
    for (i,card) in enumerate(deck):
        card.zone = game.Deck(0,int(i))

    [f1, f2, f3] = deck
    t_add_g = f1.abilities.activated[0]

    assert len(g0.objects) == 3 
    
    g1 = g0.play(f1)
    assert len(g0.objects) == 3
    assert len(g1.objects) == 3
    assert isinstance(g1.get(f1).zone, game.Field)
    assert g1.get(f1).permanent is not None
    assert t_add_g.can(g1)
    # import pdb
    # pdb.set_trace()
    g2 = g1.take_action(t_add_g)    

    assert g2.mana_pool.green == 1
    assert g2.get(f1).tapped

    assert g1.mana_pool.green == 0
    assert not g1.get(f1).tapped
