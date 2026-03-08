import pytest
from mtg_ai.game import HashKind
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


def test_possible_fetch():
    gs = game.GameState([0])
    forest = decklist.Forest(gs)
    forest.zone = zones.Deck(0)
    fetch = decklist.WindsweptHeath(gs)
    fetch.zone = zones.Field(0)
    possible = actions.possible_actions(gs)
    assert len(possible) == 1
    assert fetch.attrs.activated[0] in possible
    searcher = search.MCTSSearcher(gs,{},lambda _: True, 0.1)
    children = searcher.expand(searcher.root)
    assert len(children) == 1
    assert children[0].action == fetch.attrs.activated[0]
    new_forest = children[0].game_state.get(forest)
    assert zones.Field().contains(new_forest)


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

@pytest.mark.long
def test_search():
    gs = game.GameState([0])
    decklist.build_deck(
        gs,
        0,
        [decklist.Forest, decklist.Saruli, decklist.Saruli, decklist.WallOfRoots,
         decklist.Forest, decklist.Battlement, decklist.Forest, decklist.Forest],
        hand_size=4,
    )

    def condition(game_state):
        return game_state.mana_pool.green == 8
    result = search.bfs(gs, condition,timeout=10000)
    final = result.remaining[-1]
    print(final.game_state.in_zone(zones.Field()))
    assert final.game_state.turn_number == 4

    assert result.final_state is not None

@pytest.mark.long
def test_wincon():
    gs = game.GameState([0])
    (hand,deck) = decklist.build_deck(
        gs, 0,
        [
            decklist.Forest, decklist.Forest, decklist.WallOfRoots,decklist.WallOfRoots, decklist.Battlement,
            decklist.Axebane, decklist.WallOfOmens, decklist.Staff, decklist.Forest
        ],
        hand_size=5
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
    decklist.build_deck(
        gs, 0,
        [decklist.Forest, decklist.Forest, decklist.WallOfRoots, decklist.WallOfRoots, decklist.Battlement,
         decklist.Axebane, decklist.WallOfOmens, decklist.Staff, decklist.Forest],
        hand_size=5,
    )
    searcher = search.MCTSSearcher(gs,{},search.staff_victory,1.2,n_iters=1)
    searcher.choose()


def test_mcts():
    """
    shortest imaginable test of mcts, just to assert that
    everything on the expected path works as intended
    """
    gs = game.GameState([0])
    decklist.build_deck(
        gs, 0,
        [decklist.Forest, decklist.Forest, decklist.WallOfRoots, decklist.WallOfRoots, decklist.Battlement,
         decklist.Axebane, decklist.WallOfOmens, decklist.Staff, decklist.Forest],
        hand_size=5,
    )
    searcher = search.MCTSSearcher(gs,{},search.staff_victory,1.2,n_iters=100)
    searcher.choose()
    assert any(entry.value > 0 for entry in searcher.stats.values())


def test_mcts_is():
    """
    shortest imaginable test of mcts, just to assert that
    everything on the expected path works as intended
    """
    gs = game.GameState([0],hash_kind=HashKind.VISIBLE)
    decklist.build_deck(
        gs, 0,
        [decklist.WindsweptHeath, decklist.WindsweptHeath, decklist.WallOfRoots, decklist.WallOfRoots, decklist.Battlement,
         decklist.Axebane, decklist.WallOfOmens, decklist.Staff, decklist.Forest, decklist.Forest, decklist.Forest],
        hand_size=5,
    )
    searcher = search.MCTSSearcher(gs,{},search.staff_victory,1.2,n_iters=100)
    searcher.choose()
    assert any(entry.value > 0 for entry in searcher.stats.values())


def test_mcts_fetch():
    """
    test that mcts can crack fetches
    """
    gs = game.GameState([0],hash_kind=HashKind.VISIBLE)
    decklist.build_deck(
        gs, 0,
        [decklist.WindsweptHeath, decklist.WallOfRoots, decklist.WallOfRoots, decklist.Battlement,
         decklist.Axebane, decklist.WallOfOmens, decklist.Staff, decklist.Forest, decklist.Forest, decklist.Forest],
        hand_size=4,
    )
    gs.land_drops = 0
    field = decklist.WindsweptHeath(gs)
    field.zone = zones.Field(0)
    searcher = search.MCTSSearcher(gs,{},search.staff_victory,1.2,n_iters=100)
    choice = searcher.choose()
    assert isinstance(choice.action, actions.ActivatedAbility)
    field = choice.game_state.in_zone(zones.Field())
    assert len(field) == 1
    assert field[0].attrs.name == "Forest"

    gy = choice.game_state.in_zone(zones.Grave())
    assert len(gy) == 1
    assert gy[0].attrs.name == "Windswept Heath"


def test_mcts_fetch2():
    """
    test that mcts can crack fetches
    """
    gs = game.GameState([0],hash_kind=HashKind.VISIBLE)
    decklist.build_deck(
        gs, 0,
        [decklist.WindsweptHeath, decklist.WindsweptHeath, decklist.WallOfRoots, decklist.WallOfRoots, decklist.Battlement,
         decklist.Axebane, decklist.WallOfOmens, decklist.Staff, decklist.Forest, decklist.Forest, decklist.Forest],
        hand_size=5,
    )
    gs.land_drops = 1
    searcher = search.MCTSSearcher(gs,{},search.staff_victory,1.2,n_iters=100)
    choice = searcher.choose()
    assert isinstance(choice.action, actions.PlayLand)
    field = choice.game_state.in_zone(zones.Field())
    assert len(field) == 1
    assert field[0].attrs.name == "Windswept Heath"
    assert choice.game_state.land_drops == 0

    actions.possible_actions(choice.game_state)
    searcher.root = choice
    choice = searcher.choose()
    assert isinstance(choice.action, actions.ActivatedAbility)
    field = choice.game_state.in_zone(zones.Field())
    assert len(field) == 1
    assert field[0].attrs.name == "Forest"

    gy = choice.game_state.in_zone(zones.Grave())
    assert len(gy) == 1
    assert gy[0].attrs.name == "Windswept Heath"




def test_mcts_states():
    """
    test that mcts can crack fetches
    """
    gs = game.GameState([0],hash_kind=HashKind.VISIBLE)
    decklist.build_deck(
        gs, 0,
        [decklist.TempleGarden, decklist.Forest, decklist.Saruli, decklist.Axebane,
         decklist.TrophyMage, decklist.CollectedCompany, decklist.CollectedCompany,
         decklist.Axebane, decklist.WallOfOmens, decklist.Staff, decklist.Forest, decklist.Forest, decklist.Forest],
        hand_size=7,
    )
    gs.land_drops = 1
    searcher = search.MCTSSearcher(gs,{},search.staff_victory,1.2,n_iters=100)
    children = searcher.expand(searcher.root)
    assert len(children) == 2

    searcher.explore_node(children[0])
    assert children[0].game_state in searcher.stats

    searcher.explore_node(children[1])
    assert children[1].game_state in searcher.stats
    assert children[0].game_state in searcher.stats
