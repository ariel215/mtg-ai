from mtg_ai import cards, game, actions, zone

def test_forest():
    g0 = game.GameState([0])
    deck = [cards.forest(g0), cards.forest(g0), cards.forest(g0)]
    for (i,card) in enumerate(deck):
        card.zone = zone.Deck(0,int(i))

    [f1, f2, f3] = deck
    t_add_g = f1.abilities.activated[0]

    assert len(g0.objects) == 3 
    
    g1 = g0.take_action(actions.Play(f1))
    assert len(g0.objects) == 3
    assert len(g1.objects) == 3
    assert isinstance(g1.get(f1).zone, zone.Field)
    assert g1.get(f1).permanent is not None
    choices = t_add_g.choices(g1)
    assert choices
    g2 = g1.take_action(t_add_g, choices[0])    

    assert g2.mana_pool.green == 1
    assert g2.get(f1).tapped

    assert g1.mana_pool.green == 0
    assert not g1.get(f1).tapped


def test_cast():
    g0 = game.GameState([0])
    [f1, f2, vt] = deck = [cards.forest(g0), cards.forest(g0), cards.vine_trellis(g0)]
    vt.zone = zone.Hand(0)
    f1.zone = zone.Field(0)
    f2.zone = zone.Field(0)
    choices = f1.abilities.activated[0].choices(g0)[0] 
    g1 = g0.take_action(f1.abilities.activated[0],choices)
    g2 = g1.take_action(f2.abilities.activated[0],choices)
    cast_spell = actions.CastSpell(vt)
    choice = cast_spell.choices(g2)[0]
    g3 = g2.take_action(actions.CastSpell(vt),choice)

    vt = g3.get(vt)
    assert isinstance(vt.zone, zone.Stack)
    assert g3.mana_pool.green == 0


def test_etb():
    g0 = game.GameState([0])
    f1 = cards.forest(g0)
    omens = cards.wall_of_omens(g0)
    assert len(actions.Play.triggers) == 1

    f1.zone = zone.Deck(0,0)
    omens.zone = zone.Hand(0)

    g1 = g0.take_action(actions.Play(omens))
    assert len(g1.triggers) == 1
    g1.stack_triggers()
    assert len(g1.triggers) == 0
    stack = g1.in_zone(zone.Stack()) 
    assert len(stack) == 1
    g3 = g1.resolve_stack()
    f2 = g3.get(f1)
    assert isinstance(f2.zone, zone.Hand)
    assert f2.zone.owner == 0
    assert len(g3.in_zone(zone.Hand(owner=0))) == 1
    assert len(g3.in_zone(zone.Stack())) == 0
