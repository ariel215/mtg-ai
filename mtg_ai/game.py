from dataclasses import dataclass
from typing import TypeVar, Optional, List, Tuple, Dict, Any, Iterable
from collections.abc import Callable
from collections import defaultdict
from enum import Enum

Player = int
StackObject = TypeVar('StackObj')
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

class Game:
    def __init__(self, decks: List[List['Card']], track_history: bool = False):
        self.history = []
        players = list(range(len(decks)))
        for p in players:
            deck = decks[p]
            for position in range(len(deck)):
                deck[position].zone = Deck(owner=p, position=position)
        cards = [c for deck in decks for c in deck]
        self.current = GameState(
            players, cards, [],
            0,0
        )
        if track_history:
            ChangeTracker.on_change(self.on_change)

    def on_change(self, _):
        prev_gamestate = self.current.copy()
        self.history.append(prev_gamestate)

    @property
    def active(self):
        return self.current.active

    @property
    def priority(self):
        return self.current.priority

    def draw(self, player: Player):
        deck = self.current.get_zone(Deck(owner=player))
        top_card = deck.pop()
        top_card.zone = Hand(owner=player)

    def play(self, card):
        card.zone = Field(owner=card.zone.owner)

    def cast(self, card):
        card.zone = Stack(owner=None,position=len(self.current.stack))
        self.current.stack.append(card)


@dataclass
class GameState: 
    players: List[Player]
    cards: List['Card']
    stack: List[StackObject]
    active: int
    priority: int
    
    def copy(self):
        # this is probably too neat
        cards = [card.copy() for card in self.cards]
        stack = [obj.copy() for obj in self.stack]

        return GameState(self.players, cards, stack, self.active, self.priority)

    def get_zone(self, zone: Zone):
        return sorted([c for c in self.cards if zone.contains(c)],
        key=lambda card: card.zone.position)

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

class ChangeTracker:

    changes: Dict[Tuple[Zone,Zone],Callable[[Any,Zone,Zone],None]] = defaultdict(list)
    change_from = defaultdict(list)
    change_to = defaultdict(list)

    def __set_name__(self,owner, name):
        self.private = f"_{name}"

    def __get__(self, obj, _objtype):
        return getattr(obj,self.private)

    def __set__(self, obj, value):
        old_value = getattr(obj, self.private,None)
        if value != old_value:
            for callback in ChangeTracker.changes[(type(old_value),type(value))]:
                callback(obj, obj._zone, value)
            for callback in (
                    ChangeTracker.change_from[type(old_value)] + 
                    ChangeTracker.change_from[Any] + 
                    ChangeTracker.change_to[type(value)]):
                callback(obj)
        setattr(obj,self.private,value)

    @classmethod
    def on_draw(cls, callback):
        cls.changes[(Deck, Hand)].append(callback)
    
    @classmethod
    def on_discard(cls, callback):
        cls.changes[(Hand,Grave)].append(callback)

    @classmethod
    def on_cast(cls, callback):
        cls.changes[(Hand, Stack)].append(callback)

    @classmethod
    def on_enters(cls, callback): 
        cls.change_to[Field].append(callback)

    @classmethod
    def on_change(cls, callback):
        cls.change_from[Any].append(callback)

class CardType(str, Enum):
    Land = "land"
    Creature = "creature"

class Card:
    zone = ChangeTracker()

    def __init__(self,name, types: Iterable[CardType]=(), zone:Optional[Zone]=None):
        self.name = name
        self.types = set(types)
        # need to dodge the change tracker here
        self.__dict__['zone'] = zone

    def copy(self):
        return Card(self.name, self.types, self.zone.copy())

    def __str__(self):
        return f"[{self.name}@{self.zone}]"

    def __repr__(self):
        return str(self)

Forest = Card("Forest",[CardType.Land])