from typing import Protocol, TypeVar

T = TypeVar('T')

class Getter[T](Protocol):
    def get(self, game_state) -> T:
        ...
        
class Controller:
    def __init__(self, card):
        self.card = card

    def get(self, game_state):
        return game_state.get(self.card).zone.owner
