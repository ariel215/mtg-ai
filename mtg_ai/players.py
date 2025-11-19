from typing import Protocol

class Player(Protocol):
    def choose(self, choices, game_state):
        ...


class TestPlayer:
    def choose(self, choices, _game_state):
        return next(iter(choices))

