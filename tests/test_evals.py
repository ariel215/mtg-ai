from mtg_ai.decklist import build_deck
from mtg_ai.search import HistoryNode, MCTSSearcher, staff_victory
import mtg_ai.search
import pytest
from typing import Generator, List
from mtg_ai import decklist, zones
from mtg_ai.game import GameState

from dataclasses import dataclass
from pathlib import Path

CARDS = {}

def populate_cards():
    gs = GameState([0])
    for cardtype in vars(decklist).values():
        if isinstance(cardtype,type) and cardtype.__module__ == decklist.__name__:
            card = cardtype(gs)
            CARDS[card.attrs.name] = cardtype

populate_cards()

ZONES = {
    'field': zones.Field,
    'hand': zones.Hand,
    'deck': zones.Deck
}

HERE = Path(__file__).parent

@dataclass
class Eval:
    game_state: GameState
    final_turn: int



def parse_eval(lines: list[str]):
    """
    Eval format:
    - '## [name]'
    - newline
    - 'Field:'
    - card spec*
    - newline
    - 'Hand:'
    - card spec *
    - newline
    - 'Deck:'
    - card spec*
    - newline
    - 'Final Turn':
    - int
    -newline
    """

    zone_lsts = {'field': [], 'hand':[], 'deck': []}
    final_turn = None
    field_name = None
    lines = iter(enumerate(lines))
    try:
        for lineno, line in lines:
            line = line.strip()
            if line.endswith(':'):
                field_name = line.rstrip(':').lower()
                if field_name == 'final turn':
                    final_turn = int(next(lines)[1])
                else:
                    zone_lsts[field_name] = []
                
            elif field_name is not None:
                if line:
                    num, card = line.split(maxsplit=1)
                    zone_lsts[field_name].extend(CARDS[card] for _ in range(int(num)))

            if final_turn is not None and not any(zone is None for zone in zone_lsts.values()):
                gs =GameState([0])
                for card_type in zone_lsts['field']:
                    card = card_type(gs)
                    card.zone = zones.Field(0)
                zone_lsts['field'] = []
                for card_type in zone_lsts['hand']:
                    card = card_type(gs)
                    card.zone = zones.Hand(0)
                zone_lsts['hand'] = []
                for i,card_type in enumerate(reversed(zone_lsts['deck'])):
                    card = card_type(gs)
                    card.zone = zones.Deck(0,i)
                zone_lsts['deck'] = []
                eval = Eval(gs,final_turn)
                final_turn = None
                field_name = None
                yield eval
    except Exception:
        raise Exception(f'parse error in line {lineno}')


def evals() -> List[Eval]:
    with open(HERE / 'evals.md') as eval_file: 
        return [ev for ev in parse_eval(eval_file)]

@pytest.mark.flaky(reruns=2)
@pytest.mark.parametrize(['eval'],[(e,) for e in evals()])
def test_evals(eval: Eval):
    statistics = {}
    
    params = {
        'C': 1.5,
        'max_turns': 10,
        'n_iters': 500
    }
    current = HistoryNode(eval.game_state)
    assert (eval.game_state.turn_number == 1)
    while not staff_victory(current.game_state) and current.game_state.turn_number < params['max_turns']:
        searcher = MCTSSearcher(current.game_state, statistics,staff_victory,**params)
        current = searcher.choose()
        print(f"(t{current.game_state.turn_number}: {current.action}, {current.choice})")

    assert current.game_state.turn_number <= eval.final_turn
    
