from mtg_ai import actions, decklist, game, search, zones


def test_possible():
    gs = game.GameState([0])
    hand = decklist.Forest(gs)
    hand.zone = zones.Hand(0)
    possible = actions.possible_actions(gs)
    assert any(isinstance(action, actions.PlayLand) for action in possible)
    gs = gs.take_action(actions.PlayLand(hand),{})

    possible = actions.possible_actions(gs)
    assert any(isinstance(action, actions.ActivatedAbility) for action in possible)
    assert len(possible) == 1
    gs = gs.take_action(possible[0],possible[0].choices(gs)[0])
    assert gs.mana_pool.green == 1


def test_add():
    gs =game.GameState([0])
    f = decklist.Forest(gs)
    f.zone = zones.Hand(0)
    def condition(gs):
        return gs.mana_pool.green == 1
    
    state, _ = search.bfs(gs,condition,100)
    assert state is not None

def test_play():
    gs = game.GameState([0])
    hand = [decklist.Forest(gs), decklist.Saruli(gs)]
    for card in hand: 
        card.zone = zones.Hand(0)
    def condition(gs):
        return len(gs.in_zone(zones.Field())) == 2
    state, remaining = search.bfs(gs, condition, 100)
    assert state is not None


def test_search():
    gs = game.GameState([0])
    opening_hand = map(lambda ty: ty(gs), [decklist.Forest, decklist.Saruli, decklist.Saruli, decklist.WallOfRoots])
    for card in opening_hand:
        card.zone = zones.Hand(0)
    decklist.build_deck(
        [decklist.Forest, decklist.Battlement, decklist.Forest, decklist.Forest],
        gs,
        0
    )

    def condition(game_state):
        return game_state.mana_pool.green == 8
    result = search.bfs(gs, condition,timeout=5000)
    assert result.final_state is not None



def test_wincon():
    gs = game.GameState([0])
    deck = decklist.build_deck([
        decklist.Forest for _ in range(3)
    ] + [decklist.WallOfRoots for _ in range(3)] 
    + [decklist.Axebane, decklist.Battlement, decklist.Staff],
    gs, 0, shuffle=True)
    for card in deck[-1:-5]:
        card.zone = zones.Hand(0)
    
    result = search.bfs(gs,search.staff_victory,5000)
    assert result.final_state is not None
