from dataclasses import dataclass
from typing import Protocol, TypeVar, Optional, List, Dict, Any
from . import zone
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

    def __init__(self,players: List[Player], mana_pool: Optional['Mana']=None):
        self.objects = {}
        self.players = players
        self.mana_pool = mana_pool or Mana()
        self.parent = None
        self.children = []
        self.triggers = [] # triggers waiting to go onto the stack
        
            
    def copy(self) -> 'GameState':
        new_game_state = GameState(self.players,self.mana_pool.copy())
        uids = [uid for uid in self.objects]
        for uid in uids:
            self.objects[uid].move_to(new_game_state)
        self.children.append(new_game_state)
        new_game_state.parent = self
        return new_game_state

    def in_zone(self, zone: zone.Zone)->List['GameObject']:
        return sorted([c for c in self.objects.values() if zone.contains(c)],
        key=lambda card: card.zone.position or float('-inf'))

    def get(self, object):
        return self.objects[object.uid]

    def stack(self, card):
        stack = self.in_zone(zone.Stack())
        if stack:
            top = max(obj.zone.position for obj in stack)
            card.zone = zone.Stack(position=top+1)
        else:
            card.zone = zone.Stack(position=0)

    def resolve_stack(self) -> 'GameState':
        """
        Resolve the top of the stack
        """
        stack = self.in_zone(zone.Stack())
        top = stack.pop()
        choices = top.choose(self)

        new_state = self.take_action(top, choices[0])
        del new_state.objects[top.uid]
        return new_state

    def take_action(self, action, choices: Dict[str, Any] | None = None)->'GameState':
        choices = choices or {}
        new_state = self.copy()
        event = action.perform(new_state, **choices)
        event.game_state = new_state
        new_state.triggers.extend(
            (event,trigger) for trigger in action.triggers if trigger.condition(event)
        )
        return new_state

    def stack_triggers(self):
        for (event, trigger) in self.triggers:
            trigger.stack(self, event)
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
        raise NotImplemented

T = TypeVar('T')
type Choice[T] = Dict[str, T]
type ChoiceSet[T] = List[Choice[T]]

class Action(Protocol):
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
        ...
 
    def choose(self, game_state):
         # cls.choices() should not let you choose anything set in self.params
         choices =self.choices(game_state)
         return [
             {c: choice[c] for c in choice.keys() - self.params.keys()}
             for choice in choices 
         ]
 
    def perform(self, game_state, **kwargs):
         return self.do(game_state, **(kwargs | self.params))
 
    def do[T](self, game_state, **kwargs: Choice[T]):
        """
        Make the necessary changes to the game state. 
        Each action should have all the information 
        needed to make its constituent changes.
        """
        ...

