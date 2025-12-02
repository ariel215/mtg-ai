from mtg_ai import cards, game, actions, zones, mana, decklist


def setup_function(fun):
    actions.Play.triggers.clear()


def test_forest():
    g0 = game.GameState([0])
    deck = [decklist.Forest(g0), decklist.Forest(g0), decklist.Forest(g0)]
    for (i,card) in enumerate(deck):
        card.zone = zones.Deck(0,int(i))

    [f1, f2, f3] = deck
    t_add_g = f1.abilities.activated[0]

    assert len(g0.objects) == 3 
    
    g1 = g0.take_action(actions.Play(f1))
    assert len(g0.objects) == 3
    assert len(g1.objects) == 3
    assert isinstance(g1.get(f1).zone, zones.Field)
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
    [f1, f2, vt] = deck = [decklist.Forest(g0), decklist.Forest(g0), decklist.VineTrellis(g0)]
    vt.zone = zones.Hand(0)
    f1.zone = zones.Field(0)
    f2.zone = zones.Field(0)
    choices = f1.abilities.activated[0].choices(g0)[0] 
    g1 = g0.take_action(f1.abilities.activated[0],choices)
    g2 = g1.take_action(f2.abilities.activated[0],choices)
    cast_spell = actions.CastSpell(vt)
    choice = cast_spell.choices(g2)[0]
    g3 = g2.take_action(actions.CastSpell(vt).bind(mana=g2.mana_pool),{})

    vt = g3.get(vt)
    assert isinstance(vt.zone, zones.Stack)
    assert g3.mana_pool.green == 0


def test_etb():
    g0 = game.GameState([0])
    f1 = decklist.Forest(g0)
    omens = decklist.WallOfOmens(g0)
    assert len(actions.Play.triggers) == 1

    f1.zone = zones.Deck(0,0)
    omens.zone = zones.Hand(0)

    g1 = g0.take_action(actions.Play(omens))
    assert len(g1.triggers) == 1
    g1.stack_triggers()
    assert len(g1.triggers) == 0
    stack = g1.in_zone(zones.Stack()) 
    assert len(stack) == 1
    g3 = g1.resolve_stack()
    f2 = g3.get(f1)
    assert isinstance(f2.zone, zones.Hand)
    assert f2.zone.owner == 0
    assert len(g3.in_zone(zones.Hand(owner=0))) == 1
    assert len(g3.in_zone(zones.Stack())) == 0


def test_battlement():
    gs = game.GameState([0])
    b1 = decklist.Battlement(gs)
    b1.zone = zones.Field(0)
    b2 = decklist.Battlement(gs)
    b2.zone = zones.Field(0)
    ability = b1.abilities.activated[0]
    choice = ability.choices(gs)[0]
    gs = gs.take_action(ability, choice)
    assert gs.mana_pool.green == 2

def test_saruli():
    gs = game.GameState([0])
    omens = decklist.WallOfOmens(gs)
    saruli = decklist.Saruli(gs)
    omens.zone = zones.Field(0)
    saruli.zone = zones.Field(0)
    saruli_ability = saruli.abilities.activated[0]
    choices = saruli_ability.choices(gs)
    assert len(choices) == 1
    assert len(choices[0]['costs_choice']) == 1
    o2 = decklist.WallOfOmens(gs)
    o2.zone = zones.Field(0)
    choices = saruli_ability.choices(gs)
    assert len(choices) == 2
    choice = choices[0]
    gs = gs.take_action(saruli_ability,choice)
    assert gs.get(saruli).tapped
    assert gs.get(omens).tapped or gs.get(o2).tapped
    assert gs.mana_pool.green == 1

def test_gold_mana():
    # 'Gold' mana is a little hack to skip choosing colors 
    # when an effect produces "mana of any color"
    available = mana.Mana(gold=3)
    cost = mana.Mana(white=1, black=1, generic=1)
    assert available.can_pay(cost)

    cost.white = 2
    assert not available.can_pay(cost)

def test_arcades():
    g0 = game.GameState([0])
    f1 = decklist.Forest(g0)
    f2 = decklist.Forest(g0)
    assert len(actions.Play.triggers) == 0
    arc = decklist.Arcades(g0)
    assert len(actions.Play.triggers) == 1
    omens = decklist.WallOfOmens(g0)
    assert len(actions.Play.triggers) == 2

    f1.zone = zones.Deck(0,0)
    f2.zone = zones.Deck(0,1)
    arc.zone = zones.Field(0)
    omens.zone = zones.Hand(0)

    g1 = g0.take_action(actions.Play(omens))
    assert len(g1.triggers) == 2
    g1.stack_triggers()
    assert len(g1.triggers) == 0
    stack = g1.in_zone(zones.Stack()) 
    assert len(stack) == 2
    g2 = g1.resolve_stack()
    f2_1 = g2.get(f2)
    assert isinstance(f2_1.zone, zones.Hand)
    assert f2.zone.owner == 0
    assert len(g2.in_zone(zones.Hand(owner=0))) == 1
    assert len(g2.in_zone(zones.Stack())) == 1
    g3 = g2.resolve_stack()
    stack = g3.in_zone(zones.Stack()) 
    assert len(stack) == 0
    stack = g3.in_zone(zones.Stack()) 
    f1_1 = g3.get(f1)
    assert isinstance(f1_1.zone, zones.Hand)
    assert f1_1.zone.owner == 0
    assert len(g3.in_zone(zones.Hand(owner=0))) == 2
    assert len(g3.in_zone(zones.Stack())) == 0


def test_coco():
    g0 = game.GameState([0])
    coco = decklist.CollectedCompany(g0)
    coco.zone = zones.Hand(0)
    deck = [decklist.Forest(g0) for _ in range(4)] + [decklist.Axebane(g0) for _ in range(2)]
    for i,card in enumerate(deck):
        card.zone = zones.Deck(0, i)
    g0.mana_pool += mana.Mana(green=4)
    g1 = g0.take_action(
        actions.CastSpell(coco),
        {'mana': g0.mana_pool}
    )
    assert isinstance(g1.get(coco).zone, zones.Stack)
    assert len(g1.in_zone(zones.Stack())) == 1
    g2 = g1.resolve_stack()
    field = g2.in_zone(zones.Field())
    assert len(field) == 2
    assert all(card.name == "Axebane Guardian" for card in field)

def test_coco_etb():
    g0 = game.GameState([0])
    coco = decklist.CollectedCompany(g0)
    coco.zone = zones.Hand(0)
    deck = [decklist.Forest(g0) for _ in range(4)] + [decklist.WallOfOmens(g0)]
    for i,card in enumerate(deck):
        card.zone = zones.Deck(0, i)
    g0.mana_pool += mana.Mana(green=4)
    g1 = g0.take_action(
        actions.CastSpell(coco),
        {'mana': g0.mana_pool}
    )
    assert isinstance(g1.get(coco).zone, zones.Stack)
    assert len(g1.in_zone(zones.Stack())) == 1
    g2 = g1.resolve_stack()
    field = g2.in_zone(zones.Field())
    assert len(field) == 1
    assert len(g2.triggers) == 1
    g2.stack_triggers()
    g3 = g2.resolve_stack()
    assert len(g3.triggers) == 0
    assert len(g3.in_zone(zones.Hand())) == 1
    
