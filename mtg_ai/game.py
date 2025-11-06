from dataclasses import dataclass
from typing import TypeVar, Optional, List
from collections import defaultdict
from enum import Enum

Player = int
Card = TypeVar('Card')
StackObject = TypeVar('StackObj')


@dataclass
class GameState: 
    players: List[Player]
    cards: List[Card]
    stack: List[StackObject]
    active: Player
    priority: Player

@dataclass
class Zone:
    owner: Optional[Player] = None
    position: Optional[int] = None

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

class ZoneTracker:

    def __init__(self):
        self._zone = None

    handlers = defaultdict(list)

    def __get__(self, obj):
        return self._zone

    def __set__(self, obj, new_zone):
        if new_zone != self._zone:
            for callback in ZoneTracker.handlers[(type(self._zone),type(new_zone))]:
                callback(obj, self._zone, new_zone)
        self._zone = new_zone

    @classmethod
    def on_draw(cls, callback):
        cls.handlers[(Deck, Hand)].append(callback)
    
    @classmethod
    def on_discard(cls, callback):
        cls.handlers[(Hand,Grave)].append(callback)

    @classmethod
    def on_cast(cls, callback):
        cls.handlers[(Hand, Stack)].append(callback)

    @classmethod
    def on_enters(cls, callback): 
        for zone in (Hand, Deck, Grave, Stack):
            cls.handlers[(zone,Field)].append(callback)

class Card: 
    zone = ZoneTracker()

    def when_drawn(self, _a, _b):
        print(f"Drew {self.name}!")

    def __init__(self,name):
        self.name = name
        ZoneTracker.on_draw(Card.when_drawn)