from mtg_ai import cards, game, abilities

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


def test_cast():
    g0 = game.GameState([0])
    [f1, f2, vt] = deck = [cards.forest(g0), cards.forest(g0), cards.vine_trellis(g0)]
    vt.zone = game.Hand(0)
    f1.zone = game.Field(0)
    f2.zone = game.Field(0)

    g1 = g0.take_action(f1.abilities.activated[0])
    g2 = g1.take_action(f2.abilities.activated[0])

    g3 = g2.take_action(abilities.CastSpell(vt))

    vt = g3.get(vt)
    assert isinstance(vt.zone, game.Stack)
    assert g3.mana_pool.green == 0

