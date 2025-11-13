from dataclasses import dataclass, field
from typing import Protocol, TypeVar, Optional, List, Tuple, Dict, Any, Iterable
from collections.abc import Callable
from collections import defaultdict
from enum import Enum

Player = int
StackObject = TypeVar('StackObject')
CardRef = int

@dataclass
class Zone:
    owner: Optional[Player] = None
    position: Optional[int] = None

    def contains(self, card):
        return (
            type(self) is type(card.zone) 
            and self.owner == card.zone.owner
            and (self.position is None or self.position == card.zone.position) 
        )
    
    def __str__(self):
        return f"{type(self)}({self.owner})[{self.position}]"

    def copy(self):
        return type(self)(self.owner, self.position)

class Grave(Zone):
    pass

class Hand(Zone):
    pass

class Deck(Zone):
    pass

class Field(Zone):
    pass

class Stack(Zone):
    pass

class Any(Zone):
    pass

class Game:
    def __init__(self, decks: List[List['Card']], track_history: bool = False):
        self.history = []
        players = list(range(len(decks)))
        for p in players:
            deck = decks[p]
            for position in range(len(deck)):
                deck[position].zone = Deck(owner=p, position=position)
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
        
            
    def copy(self) -> 'GameState':
        new_gamestate = GameState(self.players,self.mana_pool.copy())
        uids = [uid for uid in self.objects]
        for uid in uids:
            self.objects[uid].move_to(new_gamestate)
        self.children.append(new_gamestate)
        new_gamestate.parent = self
        return new_gamestate

    def in_zone(self, zone: Zone)->List['GameObject']:
        return sorted([c for c in self.objects.values() if zone.contains(c)],
        key=lambda card: card.zone.position)

    def get(self, object):
        return self.objects[object.uid]

    def stack(self, card):
        stack = self.in_zone(Stack())
        if stack:
            top = max(obj.zone.position for obj in stack)
            card.zone = Stack(position=top+1)
        else:
            card.zone = Stack(0)

    def draw(self, player: Player)->'GameState':
        deck = self.in_zone(Deck(owner=player))
        top_card = deck.pop()
        new_state = self.copy()
        top_card = new_state.get(top_card)
        top_card.zone = Hand(owner=player)
        return new_state

    def play(self, card: 'Card')->'GameState':
        new_state = self.copy()
        card = new_state.get(card)
        card.zone = Field(owner=card.zone.owner)
        card.make_permanent()
        return new_state
    
    def take_action(self, action, choices: Dict[str, Any] | None = None)->'GameState':
        choices = choices or {}
        new_state = self.copy()
        action.do(new_state, **choices)
        return new_state

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

    def move_to(self, new_gamestate: GameState):
        cpy = self.copy()
        tmp_uid = cpy.uid
        cpy.game_state = new_gamestate
        cpy.uid = self.uid
        new_gamestate.objects[self.uid] = cpy
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
    def choices[T](self,gamestate) -> ChoiceSet[T]:
        ...

    def do[T](self, gamestate, **kwargs: Choice[T]):
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
