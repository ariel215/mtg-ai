import logging
from mtg_ai import game, decklist, search, zones

logging.basicConfig(level=logging.DEBUG, filename="mcts.log",filemode='w')

def starting_hand(state, player, types):
    cards = [ty(state) for ty in types]
    for card in cards:
        card.zone = zones.Hand(player)
    return cards


def do_run():
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
    do_run()