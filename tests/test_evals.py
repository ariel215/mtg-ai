from mtg_ai import decklist, zones
from mtg_ai.game import GameState

from dataclasses import dataclass

CARDS = {}

def populate_cards():
    gs = GameState([0])
    for cardtype in vars(decklist).values()
        if isinstance(v,type) and v.__module__ == decklist.__name__:
            card = v(gs)
            CARDS[card.name] = v

populate_cards()

ZONES = {
    'field': zones.Field,
    'hand': zones.Hand,
    'deck': zones.Deck
}

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

    field = None
    hand = None
    deck = None
    zones = {'field': field, 'hand': hand, 'deck': deck}
    final_turn = None
    field_name = None
    
    for line in lines:
        if line.endswith(':'):
            field_name = line.rstrip(':').lower()
            if field_name == 'final turn':
                final_turn = int(next(lines))
            else:
                zones[field_name] = []
            
        elif field_name is not None:
            if line:
                num, card = line.split()
                zones[field_name].extend(card for _ in range(num))

        if final_turn is not None and not any(zone is None for zone in zones.values()):
            gs =GameState([0])
            for card_type in field:
                card = card_type(gs)
                card.zone = zones.Field(0)
            field = None
            for card_type in hand:
                card = card_type(gs)
                card.zone = zones.Hand(0)
            hand = None
            for i,card_type in reversed(deck):
                card = card_type(gs)
                card.zone = zones.Deck(0,i)
            deck = None
            eval = Eval(gs,final_turn)
            final_turn = None
            field_name = None
            yield eval
