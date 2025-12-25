import mtg_ai.search
from mtg_ai.game import GameState
from mtg_ai.decklist import WindsweptHeath, TempleGarden, Forest, Island, Plains, BreedingPool, Saruli, WallOfRoots, SylvanCaryatid, Battlement, Axebane, TrophyMage, Staff, Duskwatch, Arcades, CollectedCompany, build_deck
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

def play_game(limit) -> mtg_ai.search.SearchResult:
    player = 0
    gs = GameState([player])
    deck = build_deck(DECK, gs, player, shuffle=True)
    return mtg_ai.search.bfs(gs, mtg_ai.search.staff_victory, timeout=limit)

if __name__ == "__main__":
    result = play_game(100000)
    if result.final_state:
        print(f"found path to victory after {result.final_state.game_state.turn_number} turns")
    else:
        print("could not find path to victory")