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
        self.current = GameState(
            players, cards, [],
            0,0
        )
        if track_history:
            ChangeTracker.all_changes.append(self.on_change)

    def on_change(self, *_):
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


class ChangeTracker:

    all_changes = []

    def __init__(self):
        self.changes = defaultdict(list)
        self.change_from = defaultdict(list)
        self.change_to = defaultdict(list)

    def __set_name__(self,owner, name):
        self.private = f"_{name}"

    def __get__(self, obj, _objtype):
        return getattr(obj,self.private)

    def __set__(self, obj, value):
        old_value = getattr(obj, self.private,None)

        old_kind = type(old_value)
        new_kind = type(new_value)
        if value != old_value:
        for callback in self.changes[(old_kind,new_kind)]:
            callback(obj, old_value, value)
        for callback in (
                self.change_from[old_kind] + 
                self.change_from[Any] + 
                self.change_to[new_kind]):
            callback(obj)
        for callback in ChangeTracker.all_changes:
            callback(obj, old_value, value)
        setattr(obj,self.private,value)

    
    def on_draw(self, callback):
        self.changes[(Deck, Hand)].append(callback)
    
    
    def on_discard(self, callback):
        self.changes[(Hand,Grave)].append(callback)

    
    def on_cast(self, callback):
        self.changes[(Hand, Stack)].append(callback)

    
    def on_enters(self, callback): 
        self.change_to[Field].append(callback)
    
    
    def on_leaves(self, callback):
        self.change_from[Field].append(callback)

    
    def on_change(self, callback):
        self.change_from[Any].append(callback)

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
        self.permanent = None
        self.zone.on_enters(Card.make_permanent)
        self.zone.on_leaves(Card.del_permanent)

    all_changes = defaultdict(list) 
    
    def make_permanent(self):
        self.permanent = Permanent(self)

    def del_permanent(self):
        self.permanent = None

    def copy(self):
        return Card(self.name, self.types, self.zone.copy())

    def __str__(self):
        return f"[{self.name}@{self.zone}]"

    def __repr__(self):
        return str(self)

def forest():
    return Card("Forest",[CardType.Land])


class Permanent:
    tapped = ChangeTracker()

    def __init__(self, card: Card, tapped: bool = False):        
        self.card = card
        self.tap_untap(tapped, False)
        self.summoning_sick = CardType.Creature in self.card.types 

    def tap_untap(self, tapped: bool, record=True):
        if record:
            self.tapped = tapped
        else:
            self.__dict__['tapped'] = tapped
          
        
Cost = TypeVar('Cost')
Effect = TypeVar('Effect')


@dataclass
class Activated:
    cost: Cost
    effect: Effect
