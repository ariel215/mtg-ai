import mtg_ai.zones
from mtg_ai.search import SearchResult, HistoryNode
from mtg_ai import search
from mtg_ai.game import GameState
from mtg_ai.decklist import WindsweptHeath, TempleGarden, Forest, Island, Plains, BreedingPool, Saruli, WallOfRoots, SylvanCaryatid, Battlement, Axebane, TrophyMage, Staff, Duskwatch, Arcades, CollectedCompany, build_deck
import logging

# logging.basicConfig(level=logging.DEBUG,filename="fullgame.log",filemode='w')
logger = logging.getLogger(__name__)


CARDS = [
    (WindsweptHeath , 8),
    (TempleGarden , 3),
    (BreedingPool , 3),
    (Forest, 2),
    (Plains, 1),
    (Island, 1),
    (Saruli , 4),  
    (WallOfRoots , 4),  
    (SylvanCaryatid , 4),
    (Battlement , 4),
    (Axebane, 4),
    (TrophyMage, 2),
    (Staff, 1),
    (Duskwatch, 3),
    (Arcades, 4),
    (CollectedCompany,4)
]

DECK = [ cardtype for cardtype, i in CARDS for _ in range(i) ]

def play_game(limit) -> search.SearchResult:
    player = 0
    gs = GameState([player])
    deck = build_deck(gs, player,DECK,  shuffle=True)
    return search.bfs(gs, search.staff_victory, timeout=limit)


def play_mcts_game(limit: int) -> SearchResult:
    statistics = {}
    player = 0
    current = HistoryNode( GameState([player]))
    deck = build_deck(current.game_state, player,DECK,  shuffle=True,hand_size=7)
    
    params = {
        'C': 1.5,
        'max_turns': limit,
        'n_iters': 250
    }

    while not search.staff_victory(current.game_state) and current.game_state.turn_number < params['max_turns']:
        print(f"hand: {[card.attrs.name for card in current.game_state.in_zone(mtg_ai.zones.Hand())]}")
        print(f"field: {[card.attrs.name for card in current.game_state.in_zone(mtg_ai.zones.Field())]}")
        print(f"mana: {current.game_state.mana_pool}")
        print(f"land drops: {current.game_state.land_drops}")
        searcher = search.MCTSSearcher(current.game_state, statistics,search.staff_victory,**params)
        current = searcher.choose()
        print(f"choices: {[str(node.action) for node in searcher.root.children]}")
        print(f"(t{current.game_state.turn_number}: {current.action}, {current.choice})")

    
    if search.staff_victory(current.game_state):
        return SearchResult(current,[],0)
    else:
        return SearchResult(None, [current], 0)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', default='bfs', choices=('bfs', 'mcts'))
    args = parser.parse_args()
    if args.mode == 'bfs':
        result = play_game(100000)
        if result.final_state:
            print(f"found path to victory after {result.final_state.game_state.turn_number} turns")
        else:
            print("could not find path to victory")
    
    elif args.mode == 'mcts':
        import random
        # seed = random.randint(0,10000000000)
        # print(f"seed: {seed}")
        # seed = 6128917386
        # random.seed(seed)
        logging.basicConfig(filename="mcts.log", filemode='w', level=logging.DEBUG)
        turn_limit= 10
        result = play_mcts_game(turn_limit)
        if result.final_state:
            print(f"found victory in {result.final_state.game_state.turn_number} turns")
        else:
            print(f"could not find victory in {turn_limit} turns")