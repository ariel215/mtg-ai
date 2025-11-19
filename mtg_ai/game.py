from dataclasses import dataclass, field
from typing import Protocol, TypeVar, Optional, List, Tuple, Dict, Any, Iterable
from collections.abc import Callable
from collections import defaultdict
from enum import Enum
from . import zone

Player = int
StackObject = TypeVar('StackObject')

class Event:
    def __init__(self, action, source=None, cause=None):
        self.action = action 
        self.source = source 
        self.cause = cause


class EventFilter:
    def matches(self, event: Event) -> bool:
        return NotImplemented

    def __and__(self, other) -> 'EventFilter':
        new_filter = EventFilter()
        def new_matches(filter, event):
            return self.matches(event) and other.matches(event)
        new_filter.matches = new_matches
        return new_filter

    def __or__(self, other) -> 'EventFilter':
        new_filter = EventFilter()
        def new_matches(filter, event):
            return self.matches(event) and other.matches(event)
        new_filter.matches = new_matches
        return new_filter


class Game:
    def __init__(self, decks: List[List['Card']], track_history: bool = False):
        self.history = []
        players = list(range(len(decks)))
        for p in players:
            deck = decks[p]
            for position in range(len(deck)):
                deck[position].zone = zone.Deck(owner=p, position=position)
        cards = [c for deck in decks for c in deck]
        self.root = GameState(
            players, cards, [],
            0,0
        )
        self.track_history =track_history
        
    @property
    def active(self):
        return self.root.active

    @property
    def priority(self):
        return self.root.priority

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
        stack = self.in_zone(zone.Stack())
        top = stack.pop()
        choices = top.choices(self)

        new_state = self.take_action(top, choices[0])
        del new_state.objects[top.uid]
        return new_state

    def take_action(self, action, choices: Dict[str, Any] | None = None)->'GameState':
        choices = choices or {}
        new_state = self.copy()
        event = action.do(new_state, **choices)
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

class ObjRef:

    def __set_name__(self, obj, name):
        self.private_name = f"_{name}"
        self.public_name = name

    def __set__(self, owner: GameObject, value: GameObject):
        if hasattr(value, '__iter__'):
            ids = [v.uid for v in value]
            setattr(owner, self.private_name, ids)
        else:
            id = value.uid
            setattr(owner, self.private_name, id)
            owner.game_state = value.game_state 
        

    def __get__(self, owner: GameObject, owner_type):
        uids = getattr(owner,self.private_name)
        if isinstance(uids, list):
            return [
                owner.game_state.objects[uid]
                for uid in uids 
            ]
        else: 
            return owner.game_state.objects[uid]


T = TypeVar('T')
type Choice[T] = Dict[str, T]
type ChoiceSet[T] = List[Choice[T]]

class Action(Protocol):
    def __init_subclass__(cls):
        cls.triggers: List['Trigger'] = []

    def choices[T](self,game_state) -> ChoiceSet[T]:
        ...

    def do[T](self, game_state, **kwargs: Choice[T]):
        ...


@dataclass
class Mana:
    white: int = 0
    blue: int = 0
    black: int = 0
    red: int = 0
    green: int = 0
    colorless: int = 0
    generic: int = 0

    def __iadd__(self, other):
        for field in ('white','blue','black','red','green','generic','colorless'):
            current = getattr(self,field)
            setattr(self,field,current + getattr(other, field))
        return self

    def __isub__(self, other):
        for field in ('white','blue','black','red','green','colorless'):
            current = getattr(self,field)
            setattr(self,field,current - getattr(other, field))
        generic_cost = other.generic
        while generic_cost > 0:
            for field in  ('white','blue','black','red','green','colorless'):
                value =getattr(self, field)
                amt = min(generic_cost, value)
                setattr(self, field, value - amt)
                generic_cost -= amt 
        return self
    
    def __add__(self, other) -> 'Mana':
        new = self.copy()
        new += other
        return new

    def __sub__(self, other) -> 'Mana':
        new = self.copy() 
        new -= other
        return new

    def __imul__(self, amount):
        for field in ('white','blue','black','red','green','generic','colorless'):
            setattr(self, field, getattr(self, field) * amount)
        return self

    def __mul__(self, amount):
        copy = self.copy() 
        copy *= amount
        return copy

    @property
    def mana_value(self):
        return sum(getattr(self, field)
         for field in
         ('white','blue','black','red','green','colorless','generic')
     )

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return all(
            getattr(self, field) == getattr(other, field)
             for field in ('white','blue','black','red','green','colorless','generic')
        )

    def can_pay(self, other)->bool:
        """
        Returns whether `self` can pay the cost `other` 
        """

        for field in  ('white','blue','black','red','green','colorless'):
            if getattr(self, field) < getattr(other, field):
                return False

        return self.mana_value >= other.mana_value        

    def copy(self):
        return Mana(
            self.white,
            self.blue,
            self.black,
            self.red,
            self.green,
            self.generic,
            self.colorless
        )
    
