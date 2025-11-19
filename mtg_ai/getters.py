from typing import Protocol, TypeVar

T = TypeVar('T')

class Getter[T](Protocol):
    def __call__(self, game_state) -> T:
        ...

class Controller:
    def __init__(self, card):
        self.card = card

    def __call__(self, game_state):
        return game_state.get(self.card).controller

