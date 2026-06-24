import random
from mtg_ai import game, decklist, search, zones
import cProfile
import timeit

def starting_hand(state, player, types):
    cards = [ty(state) for ty in types]
    for card in cards:
        card.zone = zones.Hand(player)
    return cards



def do_run():
    random.seed(0)
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

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-t','--time', required=False,action='store_true')
    parser.add_argument('-p','--profile',required=False,action='store_true')
    args = parser.parse_args()
    if not args.time and not args.profile: 
        raise argparse.ArgumentError('One of -t,-p required')
    if args.time:
        niters = 40
        t = timeit.Timer('do_run()',globals=globals())
        time = t.timeit(niters)
        print(f"Average time: {time / niters} seconds")
    else:
        cProfile.run(statement='do_run()',filename='mcts.profile')
