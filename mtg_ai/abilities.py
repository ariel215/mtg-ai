from dataclasses import dataclass, field
from typing import Protocol, List, Union, Iterable, Optional
from collections.abc import Callable
from collections import defaultdict
from enum import Enum
from mtg_ai.game import GameObject, GameState, Zone, ObjRef, Mana, Action



class CardType(str, Enum):
    Land = "land"
    Creature = "creature"

class Card(GameObject):

    @dataclass
    class Abilities:
        static: list = field(default_factory=list)
        triggered: list = field(default_factory=list)
        activated: list = field(default_factory=list)

    def __init__(self, name,
                 types: Iterable[CardType]=(),
                 abilities: Optional[Abilities] = None,
                 zone:Optional[Zone]=None,
                 permanent: bool = False,
                 tapped: bool = False,
                 game_state: Optional[GameState] = None,
             ):

        super().__init__(game_state)
        self.zone = zone 
        self.name = name
        self.types = set(types)
        self.permanent = permanent
        self.tapped = tapped
        self.abilities = abilities or Card.Abilities()


    def set_abilities(self, static=(), triggered=(), activated=()):
        self.abilities = self.Abilities(
            static=list(static),
             triggered=list(triggered),
             activated=list(activated)
        )
        return self
    

    @property
    def summoning_sick(self):
        return self.permanent and self.permanent.summoning_sick
            
    def make_permanent(self):
        self.permanent = True

    def del_permanent(self):
        self.permanent = False

    def copy(self):
        return Card(name=self.name,
                    types=self.types,
                    abilities=self.abilities,
                    zone=self.zone,
                    permanent=self.permanent,
                    tapped=self.tapped,
                    game_state=self.game_state)

    def __str__(self):
        return f"[{self.name}@{self.zone}]"

    def __repr__(self):
        return str(self)


class Permanent:

    def __init__(self, card: Card, tapped: bool = False):        
        self.card = card
        self.tapped = tapped 
        self.summoning_sick = CardType.Creature in self.card.types 
          

class TapSymbol:

    def __init__(self, target: Card):
        """
        Tap a permanent using the tap symbol.
        Target: the permanent to be tapped
        """
        self.card = target
    
    def can(self, gamestate):
        card = gamestate.get(self.card)
        return not card.tapped

    def do(self, gamestate):
        gamestate.get(self.card).tapped = True


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

    def can(self, game_state: GameState):
        return all(cost.can(game_state) for cost in self.costs)

    def do(self, game_state):
        for cost in self.costs:
            cost.do(game_state)
        for effect in self.effects:
            effect.do(game_state)
        return game_state
