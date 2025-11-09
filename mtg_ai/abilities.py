from dataclasses import dataclass
from typing import Protocol, List
from collections.abc import Callable

@dataclass
class Mana:
    white: int = 0
    blue: int = 0
    black: int = 0
    red: int = 0
    green: int = 0
    generic: int = 0
    colorless: int = 0

class Action(Protocol):
    def can(self, gamestate):
        ...

    def do(self, gamestate):
        ...


class TapSymbol:
    def __init__(self, target):
        """
        Tap a permanent using the tap symbol.
        Target: the permanent to be tapped
        """
        self.card =target
    
    def can(self, _gamestate):
        return not (self.card.tapped or self.card.summoning_sick)

    def do(self, _gamestate):
        self.card.tapped = True


class AddMana:
    def __init__(self,mana: Union[Mana,Callable[['GameState'],Mana]]):
        self.mana = mana

    def can(self, _gamestate):
        return True

    def do(self, gamestate):
        if isinstance(self.mana, Mana):
           gamestate.mana_pool += self.mana
        else:
            mana = self.mana(gamestate)
            gamestate.mana_pool += mana
         
class ActivatedAbility:
    def __init__(self, costs: List[Action], effects: List[Action]):
        self.costs = costs
        self.effects = effects

    def can(self, gamestate):
        return all(cost.can(gamestate) for cost in self.costs)

    def do(self, gamestate):
        for cost in self.costs:
            cost.do(gamestate)
        for effect in self.effects:
            effect.do(gamestate)
