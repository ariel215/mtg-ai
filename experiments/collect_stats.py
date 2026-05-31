from _asyncio import Future
from mtg_ai.transposition_db import LazyTranspositionDB
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
import asyncio
from concurrent.futures import ProcessPoolExecutor

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

def do_run(db_path, params,*args):
    stats = get_stats(db_path)
    random.seed()
    initial_game = game = GameState([0])
    node = None
    max_turns = params['max_turns']
    build_deck(game,0,DECK, shuffle=True, hand_size=7)
    while not mtg_ai.search.staff_victory(game) and game.turn_number < max_turns:
        searcher = mtg_ai.search.MCTSSearcher(game,stats,mtg_ai.search.staff_victory,
        **params)
        node = searcher.choose()
        game = node.game_state
    stats = {k: v for k,v in stats.items()}
    return (stats, canonical_key(initial_game), node.game_state.turn_number)


def save_results(db_path, stats, key, turn_no):
    assert os.path.exists(os.path.dirname(db_path))
    mtg_ai.transposition_db.merge_statistics(db_path,statistics=stats)
    mtg_ai.transposition_db.save_result(db_path,key,turn_no)


async def run_batch(batch_size, db_path, params):

    with ProcessPoolExecutor() as executor:
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(executor,do_run, db_path, params)
            for _ in range(batch_size)
        ]
        for task in asyncio.as_completed(tasks):
            task_result = await task
            save_results(db_path,*task_result)


def get_stats(db_path) -> dict | LazyTranspositionDB:
    if not os.path.exists(db_path):
        return {}
    size = os.stat(db_path).st_size
    if size > 50*1e6:
        return LazyTranspositionDB(db_path)
    else:
        return mtg_ai.transposition_db.load_statistics(db_path)


if __name__ == "__main__":
    import argparse 
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch_size", "-b", required=False, type=int, default=1)
    parser.add_argument("--db", "-d", required=False, default=DB)
    parser.add_argument("--C", "-C", required=False, default=1.2,type=float)
    parser.add_argument("--max_turns", "-m", required=False, default=10, type=int)
    parser.add_argument("--n_iters", "-n", required=False, default=500, type=int)

    args = parser.parse_args()
    db_path = os.path.expanduser(args.db)
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    params = {
        'C': args.C,
        'max_turns': args.max_turns,
        'n_iters': args.n_iters
    }

    asyncio.run(
        run_batch(args.batch_size, db_path,params)
    )
