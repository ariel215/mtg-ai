from mtg_ai import cards, game, actions, getters, zones, mana, decklist
from mtg_ai.game import StaticEffect, StaticAbility


def test_forest():
    g0 = game.GameState([0])
    deck = [decklist.Forest(g0), decklist.Forest(g0), decklist.Forest(g0)]
    for (i,card) in enumerate(deck):
        card.zone = zones.Deck(0,int(i))

    [f1, f2, f3] = deck
    f1.zone = zones.Hand(0)
    t_add_g = f1.attrs.activated[0]

    assert len(g0.objects) == 3 
    
    g1 = g0.take_action(actions.PlayLand(f1))
    assert len(g0.objects) == 3
    assert len(g1.objects) == 3
    assert isinstance(g1.get(f1).zone, zones.Field)
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
    choices = f1.attrs.activated[0].choices(g0)[0]
    g1 = g0.take_action(f1.attrs.activated[0],choices)
    g2 = g1.take_action(f2.attrs.activated[0],choices)
    cast_spell = actions.CastSpell(vt)
    g3 = g2.take_action(actions.CastSpell(vt).bind(mana=g2.mana_pool),{})

    vt = g3.get(vt)
    assert isinstance(vt.zone, zones.Stack)
    assert g3.mana_pool.green == 0


def test_etb():
    g0 = game.GameState([0])
    f1 = decklist.Forest(g0)
    omens = decklist.WallOfOmens(g0)
    assert len(g0.active_triggers) == 0

    f1.zone = zones.Deck(0,0)
    omens.zone = zones.Hand(0)

    g1 = g0.take_action(actions.Play(omens))
    assert len(g0.triggers) == 0
    assert len(g1.triggers) == 1
    assert len(g0.active_triggers) == 0
    assert len(g1.active_triggers) == 1
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
    ability = b1.attrs.activated[0]
    choice = ability.choices(gs)[0]
    gs = gs.take_action(ability, choice)
    assert gs.mana_pool.green == 2

def test_saruli():
    gs = game.GameState([0])
    omens = decklist.WallOfOmens(gs)
    saruli = decklist.Saruli(gs)
    omens.zone = zones.Field(0)
    saruli.zone = zones.Field(0)
    saruli_ability = saruli.attrs.activated[0]
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
    assert len(g0.triggers) == 0
    assert len(g0.active_triggers) == 0
    arc = decklist.Arcades(g0)
    omens = decklist.WallOfOmens(g0)
    assert len(g0.triggers) == 0
    assert len(g0.active_triggers) == 0

    f1.zone = zones.Deck(0,0)
    f2.zone = zones.Deck(0,1)
    arc.zone = zones.Field(0)
    omens.zone = zones.Hand(0)
    assert len(g0.triggers) == 0
    assert len(g0.active_triggers) == 1

    g1 = g0.take_action(actions.Play(omens))
    assert len(g0.triggers) == 0
    assert len(g1.triggers) == 2
    assert len(g1.active_triggers) == 2
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
        {'mana': g0.mana_pool, "effect_choices":{}}
    )
    assert isinstance(g1.get(coco).zone, zones.Stack)
    assert len(g1.in_zone(zones.Stack())) == 1
    g2 = g1.resolve_stack()
    field = g2.in_zone(zones.Field())
    assert len(field) == 2
    assert all(card.attrs.name == "Axebane Guardian" for card in field)
    assert (len(g2.in_zone(zones.Grave())) == 1)
    assert(len(g2.in_zone(zones.Grave(0))) == 1)

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
    

def test_duskwatch():
    g0 = game.GameState([0])
    dw = decklist.Duskwatch(g0)
    deck = [decklist.Forest(g0), decklist.Arcades(g0), decklist.Forest(g0)]
    for (i,card) in enumerate(deck):
        card.zone = zones.Deck(0,i)
    dw.zone = zones.Field(0)
    g0.mana_pool = mana.Mana(green=3)
    ability = dw.attrs.activated[0]
    choice = next(iter(ability.choices(g0)))
    g1 = g0.take_action(ability,choice)
    assert zones.Hand(0).contains(g1.get(deck[1]))
    assert len(g1.in_zone(zones.Deck(0))) == 2

def test_duskwatch_miss():
    g0 = game.GameState([0])
    dw = decklist.Duskwatch(g0)
    deck = [decklist.Forest(g0), decklist.Forest(g0), decklist.Forest(g0)]
    for (i,card) in enumerate(deck):
        card.zone = zones.Deck(0,i)
    dw.zone = zones.Field(0)
    g0.mana_pool = mana.Mana(green=3)
    ability = dw.attrs.activated[0]
    choice = next(iter(ability.choices(g0)))
    g1 = g0.take_action(ability,choice)
    assert len(g1.in_zone(zones.Deck(0))) == 3

def test_trophy_mage():
    g0 = game.GameState([0])
    tm = decklist.TrophyMage(g0)
    deck = [decklist.Staff(g0), decklist.Forest(g0), decklist.Forest(g0)]
    for (i,card) in enumerate(deck):
        card.zone = zones.Deck(0,i)
    tm.zone = zones.Hand(0)
    g1 = g0.take_action(actions.Play(tm), {})
    g1.stack_triggers()
    g2 = g1.resolve_stack()
    assert zones.Hand(0).contains(g2.get(deck[0]))

def test_summoning_sickness():
    gs = game.GameState([0])
    b1 = decklist.Battlement(gs)
    b1.zone = zones.Field(0)
    b2 = decklist.Battlement(gs)
    b2.zone = zones.Hand(0)
    f1 = decklist.Forest(gs)
    f1.zone = zones.Hand(0)

    ability = b2.attrs.activated[0]
    gs = gs.take_action(actions.Play(card=b2),{})
    # should not be able to activate b2 the turn it comes into play
    assert not ability.choices(gs)
    gs = gs.take_action(actions.EndTurn(),{})
    # can activate it on subsequent turns
    assert ability.choices(gs)
    # noncreatures don't have summoning sickness
    gs = gs.take_action(actions.Play(card=f1),{})
    assert f1.attrs.activated[0].choices(gs)

def test_end_turn():
    gs = game.GameState([0])
    [forest] = decklist.build_deck([decklist.Forest],gs, 0)
    end_turn = actions.EndTurn() + actions.Draw(getters.ActivePlayer())
    choices = end_turn.choices(gs)[0]
    gs = gs.take_action(end_turn, choices)
    assert zones.Hand().contains(gs.get(forest))

def test_static_anthem():
    gs = game.GameState([0])
    [saruli, steel, kaysa] = decklist.build_deck([decklist.Saruli, decklist.SteelWall, decklist.Kaysa], gs, 0)
    saruli.zone = zones.Field(0)
    steel.zone = zones.Field(0)
    kaysa.zone = zones.Hand(0)
    assert(saruli.attrs.power == 0 and saruli.attrs.toughness == 3)
    assert(steel.attrs.power == 0 and steel.attrs.toughness == 4)
    assert (kaysa.attrs.power == 2 and kaysa.attrs.toughness == 3)

    kaysa.zone = zones.Field(0)
    assert (saruli.attrs.power == 1 and saruli.attrs.toughness == 4)
    assert (steel.attrs.power == 0 and steel.attrs.toughness == 4)
    assert (kaysa.attrs.power == 3 and kaysa.attrs.toughness == 4)

    # anthem effect should not affect cards that aren't in play
    saruli.zone = zones.Hand(0)
    steel.zone = zones.Hand(0)
    assert (saruli.attrs.power == 0 and saruli.attrs.toughness == 3)
    assert (steel.attrs.power == 0 and steel.attrs.toughness == 4)


def test_fetch():
    gs = game.GameState([0])
    decklist.build_deck([decklist.Island, decklist.Forest] + [decklist.Island for _ in range(4)],
    gs, 0)
    fetch = decklist.WindsweptHeath(gs)
    fetch.zone = zones.Field(0)
    ability = fetch.attrs.activated[0]
    choice = ability.choices(gs)[0]
    gs = gs.take_action(ability, choice)
    fetch = gs.get(fetch)
    assert zones.Grave(0).contains(fetch)
    field = gs.in_zone(zones.Field())
    assert len(field) == 1
    assert "forest" in field[0].attrs.subtypes

def test_target():
    g0 = game.GameState([0])
    [saruli, steel, unsummon] = decklist.build_deck([decklist.Saruli, decklist.SteelWall, decklist.Unsummon], g0, 0)
    saruli.zone = zones.Field(0)
    steel.zone = zones.Field(0)
    unsummon.zone = zones.Hand(0)
    g0.mana_pool += mana.Mana(blue=1)
    cast = actions.CastSpell(unsummon)
    cast_choices = cast.choices(g0)

    g_onstack = []
    for choice in cast_choices:
        g1 = g0.take_action(cast, choice)
        g_onstack.append(g1)
        assert(len(g1.in_zone(zones.Stack())) == 1)
        assert(len(g1.get(unsummon).effect.choose(g1)) == 1)
    assert(len(g_onstack) == 2)
    # This test puts both versions of Unsummon on the stack at the same time before letting either
    # resolve, to make sure that the two GameStates are not affecting each other.
    bounced_names = set()
    for g1 in g_onstack:
        assert (len(g1.get(unsummon).effect.choose(g1)) == 1) # choices locked in
        g2 = g1.resolve_stack()
        bounced_names.add(g2.in_zone(zones.Hand())[0].attrs.name)
        assert(len(g2.in_zone(zones.Stack())) == 0)
        assert(len(g2.in_zone(zones.Field())) == 1)
        assert(len(g2.in_zone(zones.Hand())) == 1)
        assert(len(g2.in_zone(zones.Grave())) == 1)
        # choices should no longer be locked in. If a second creature is in play again,
        # Unsummon should be ready to target either one.
        g2.in_zone(zones.Hand())[0].zone = zones.Field(0)
        assert (len(g2.get(unsummon).effect.choose(g2)) == 2)

    # confirm the affected card was different in the two branches
    assert(bounced_names == {'Steel Wall', 'Saruli Caretaker'})
    # make sure g0 is still unaffected by all this...
    assert(len(g0.in_zone(zones.Stack())) == 0)
    assert(len(g0.in_zone(zones.Field())) == 2)
    assert(len(g0.in_zone(zones.Hand())) == 1)
    assert(len(g0.in_zone(zones.Grave())) == 0)