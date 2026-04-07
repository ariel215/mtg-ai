from mtg_ai import game, search, decklist, zones, actions
import cProfile

def test_mcts_fetch2():
    """
    test that mcts can crack fetches
    """
    gs = game.GameState([0])
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

if __name__ == "__main__":
        cProfile.run('test_mcts_fetch2()',filename='fetch.profile')
