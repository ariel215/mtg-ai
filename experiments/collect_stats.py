from packaging.version import parse
import functools
import multiprocessing
import mtg_ai.search
from re import search
from mtg_ai.game import GameState, canonical_key
import mtg_ai
import os
import random
from mtg_ai.decklist import *

# Workflow: 
# - randomize
# - load stats
# - play game
# - record stats

DB = os.getenv("MTG_AI_DB") or "mtg_ai_db.sqlite" 


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



def do_run(db_path, C, max_turns, n_iters,*args):
    stats=  mtg_ai.transposition_db.load_statistics(db_path)
    random.seed()
    initial_game = game = GameState([0])
    node = None
    build_deck(game,0,DECK, shuffle=True, hand_size=7)
    while not mtg_ai.search.staff_victory(game):
        searcher = mtg_ai.search.MCTSSearcher(game,stats,mtg_ai.search.staff_victory,
        C=C, max_turns=max_turns, n_iters=n_iters)
        node = searcher.choose()
        game = node.game_state

    mtg_ai.transposition_db.merge_statistics(DB,stats)
    mtg_ai.transposition_db.save_result(DB, canonical_key(initial_game),node.game_state.turn_number)

def run_batch(batch_size, db_path, C, max_turns, n_iters):
    pool = multiprocessing.Pool()
    pool.map(functools.partial(do_run, db_path, C, max_turns,n_iters),range(batch_size))


if __name__ == "__main__":
    import argparse 
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch_size", required=True, type=int)
    parser.add_argument("--db", required=False, default=DB)
    parser.add_argument("--C", required=False, default=1.2,type=float)
    parser.add_argument("--max_turns", required=False, default=10, type=int)
    parser.add_argument("--n_iters", required=False, default=500, type=int)

    args = parser.parse_args()

    run_batch(args.batch_size, args.db, args.C, args.max_turns, args.n_iters)
