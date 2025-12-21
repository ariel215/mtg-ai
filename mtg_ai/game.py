from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from enum import Enum
from itertools import chain, product
from typing import Protocol, TypeVar, Optional, List, Dict, Any
from . import zones
from .mana import Mana

Player = int
StackObject = TypeVar('StackObject')

class Event:
    def __init__(self, action, game_state: 'GameState', source=None, cause=None, ):
        self.action = action 
        self.source = source
        self.cause = cause
        self.game_state = game_state

class GameState:

    def __init__(self,players: List[Player], mana_pool: Optional['Mana']=None, turn_number=0):
        self.objects = {}
        self.players = players
        self.mana_pool = mana_pool or Mana()
        self.turn_number = turn_number
        self.parent = None
        self.children = []
        self.triggers = [] # triggers waiting to go onto the stack
        self.summoning_sick = set() # summoning sick cards
        self.land_drops = 1
        self.active_player = 0

    def __hash__(self):
        return hash(
            tuple(chain((self.mana_pool, self.active_player),self.objects.values()))
        )
    
    def __eq__(self, value):
        return type(self) is type(value) and hash(self) == hash(value)
            
    def copy(self) -> 'GameState':
        new_game_state = GameState(self.players,self.mana_pool.copy(), self.turn_number)
        uids = [uid for uid in self.objects]
        for uid in uids:
            self.objects[uid].move_to(new_game_state)
        new_game_state.summoning_sick = {new_game_state.get(card) for card in self.summoning_sick}
        self.children.append(new_game_state)
        new_game_state.parent = self
        new_game_state.triggers = self.triggers
        return new_game_state

    def in_zone(self, zone: zones.Zone)->List['GameObject']:
        return sorted([c for c in self.objects.values() if zone.contains(c)],
        key=lambda card: card.zone.position or float('-inf'))

    def get(self, object: 'GameObject') -> 'GameObject':
        return self.objects[object.uid]

    def stack(self, card):
        owner = card.zone.owner if card.zone else None
        stack = self.in_zone(zones.Stack())
        if stack:
            top = max(obj.zone.position for obj in stack)
            card.zone = zones.Stack(owner=owner, position=top+1)
        else:
            card.zone = zones.Stack(owner=owner, position=0)

    def resolve_stack(self) -> 'GameState':
        """
        Resolve the top of the stack
        """
        stack = self.in_zone(zones.Stack())
        top = stack.pop()
        choices = top.effect.choices(self)

        new_state = self.take_action(top.effect, choices[0])
        return new_state

    def take_action(self, action: 'Action', choices: Dict[str, Any] | None = None, copy:bool=True)->'GameState':
        choices = choices or {}
        new_state = self.copy() if copy else self
        event = action.perform(new_state, **choices)
        new_state = event.game_state
        new_state.triggers.extend(
            (event,trigger) for trigger in action.triggers if trigger.condition(event)
        )
        return new_state

    def stack_triggers(self):
        for (event, trigger) in self.triggers:
            trigger.do(self, event)
        self.triggers.clear()

class GameObject:
    maxid = 0
    def __init__(self, game_state: GameState, uid: Optional[int]=None):
        self.game_state = game_state
        if uid is None:
            self.uid = GameObject.maxid
            GameObject.maxid += 1
        else:
            self.uid = uid
        game_state.objects[self.uid] = self

    def move_to(self, new_game_state: GameState):
        cpy = self.copy()
        tmp_uid = cpy.uid
        cpy.game_state = new_game_state
        cpy.uid = self.uid
        new_game_state.objects[self.uid] = cpy
        del self.game_state.objects[tmp_uid]
        return cpy
    
    def copy(self) -> 'GameObject':
        raise NotImplementedError()



T = TypeVar('T')
type Choice[T] = Dict[str, T]
type ChoiceSet[T] = List[Choice[T]]

class Action:
    def __init__(self):
         self.params = {}
 
    def bind(self, **kwargs):
         self.params |= kwargs
         return self
 
    
    def __init_subclass__(cls):
        cls.triggers: List['Trigger'] = []

    def choices[T](self,game_state) -> ChoiceSet[T]:
        """
        The possible choices that can be made for this action.
        For example: If a player has to sacrifice a creature, 
        the choices are the creatures that player controls.

        Each element of the ChoiceList should be a dictionary whose 
        keys are the same as the keyword arguments to `do()`.
        """
        raise NotImplementedError()
 
    def choose(self, game_state):
         # cls.choices() should not let you choose anything set in self.params
         choices =self.choices(game_state)
         return [
             {c: choice[c] for c in choice.keys() - self.params.keys()}
             for choice in choices 
         ]
 
    def perform(self, game_state, **kwargs) -> Event:

        if event := self.do(game_state, **(kwargs | self.params)):
            return event
        return Event(self, game_state)
 
    def do[T](self, game_state, **kwargs: Choice[T]) -> Event:
        """
        Make the necessary changes to the game state. 
        Each action should have all the information 
        needed to make its constituent changes.
        """
        raise NotImplementedError()
    
    def __add__(self, other: 'Action') -> 'And':
        return And(self, other)


class And(Action):
    def __init__(self, *actions):
        super().__init__()
        self.actions: List[Action] = list(actions)

    def choices(self,game_state):
        subchoices = [action.choices(game_state) for action in self.actions]
        combinations = list(product(*subchoices))
        return [{'choices': option }
        for option in combinations]
    
    def do(self, game_state, choices=None):
        if choices is None:
            choices = ({} for _ in self.actions)
        for action, choice in zip(self.actions, choices):
            game_state = game_state.take_action(action, choice)
        return Event(self, game_state)

    def __add__(self, other: Action):
        new_action = And(*self.actions)
        new_action.actions.append(other)
        return new_action

class StackAbility(GameObject):
    """
    An ability that is on the stack, waiting to resolve
    """

    class Cleanup(Action):
        def __init__(self, obj):
            super().__init__()
            self.obj = obj
            
        def choices(self, _game_state):
            return [{}]

        def do(self, game_state):
            del game_state.objects[self.obj.uid]

    def __init__(self,game_state: GameState,
                 effect):
        self.zone = None 
        super().__init__(game_state)
        self.effect: Action = effect + StackAbility.Cleanup(self)

    def copy(self):
        ability = StackAbility(
            game_state=self.game_state,
            effect=self.effect
        )
        ability.zone=self.zone
        ability.effect = self.effect
        return ability


class CardType(str, Enum):
    Land = "land"
    Creature = "creature"
    Instant = "instant"
    Sorcery = "sorcery"
    Artifact = "artifact"

SPELL_TYPES = {CardType.Instant, CardType.Sorcery}