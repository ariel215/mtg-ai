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
    gs = gs.take_action(possible[0],possible[0].get_choices(gs)[0])
    assert gs.mana_pool.green == 1


def test_add():
    gs =game.GameState([0])
    f = decklist.Forest(gs)
    f.zone = zones.Hand(0)
    def condition(gs):
        return gs.mana_pool.green == 1
    
    result = search.bfs(gs,condition,100)
    assert result is not None

def test_play():
    gs = game.GameState([0])
    hand = [decklist.Forest(gs), decklist.Saruli(gs)]
    for card in hand: 
        card.zone = zones.Hand(0)
    def condition(gs):
        return len(gs.in_zone(zones.Field())) == 2
    result = search.bfs(gs, condition, 100)
    assert result is not None

def starting_hand(state, player, types):
    cards = [ty(state) for ty in types]
    for card in cards:
        card.zone = zones.Hand(player)
    return cards


def test_search():
    gs = game.GameState([0])
    opening_hand = starting_hand(gs, 0,
    [decklist.Forest, decklist.Saruli, decklist.Saruli, decklist.WallOfRoots])
    decklist.build_deck(
        gs,
        0,
        [decklist.Forest, decklist.Battlement, decklist.Forest, decklist.Forest],
    )

    def condition(game_state):
        return game_state.mana_pool.green == 8
    result = search.bfs(gs, condition,timeout=5000)
    assert result.final_state is not None

def test_wincon():
    gs = game.GameState([0])
    hand = starting_hand(gs, 0,[
        decklist.Forest, decklist.Forest, decklist.WallOfRoots,decklist.WallOfRoots, decklist.Battlement
    ])
    deck = decklist.build_deck(
        gs, 0,
        [decklist.Axebane, decklist.WallOfOmens, decklist.Staff, decklist.Forest],
    )
    result = search.bfs(gs,search.staff_victory,5000)
    assert result.final_state is not None
    assert result.final_state.game_state.turn_number == 4



def test_mcts_short():
    """
    shortest imaginable test of mcts, just to assert that
    everything on the expected path works as intended
    """
    gs = game.GameState([0])
    hand = starting_hand(gs, 0,[
        decklist.Forest, decklist.Forest, decklist.WallOfRoots,decklist.WallOfRoots, decklist.Battlement
    ])
    deck = decklist.build_deck(
        gs, 0,
        [decklist.Axebane, decklist.WallOfOmens, decklist.Staff, decklist.Forest],
    )
    searcher = search.MCTSSearcher(gs,{},search.staff_victory,1.2,n_iters=1)
    searcher.choose()


def test_mcts():
    """
    shortest imaginable test of mcts, just to assert that
    everything on the expected path works as intended
    """
    gs = game.GameState([0])
    hand = starting_hand(gs, 0,[
        decklist.Forest, decklist.Forest, decklist.WallOfRoots,decklist.WallOfRoots, decklist.Battlement
    ])
    deck = decklist.build_deck(
        gs, 0,
        [decklist.Axebane, decklist.WallOfOmens, decklist.Staff, decklist.Forest],
    )
    searcher = search.MCTSSearcher(gs,{},search.staff_victory,1.2,n_iters=1000)
    searcher.choose()
    assert any(entry.value > 0 for entry in searcher.stats.values())

