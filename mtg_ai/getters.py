from typing import Protocol, TypeVar
from itertools import chain, combinations, tee
from . import zones

T = TypeVar('T')

class Getter[T](Protocol):
    def __call__(self, game_state) -> T:
        ...

class Get[T]:
    """
    Adapter to let us assign either Getters or values
    to a property
    """
    def __init__(self, default_value=None):
        def default(*args):
            return default_value
        self._default = default

    def __set_name__(self, owner, name):
        self.private_name = f"_{name}"
        self.public_name =name

    def __set__(self, owner, value: T):
        if callable(value):
            setattr(owner, self.private_name, value)
        else:
            def default(*args):
                return value
            setattr(owner, self.private_name, default)
        
    def __get__(self,owner, _objname)->T:
        if owner is None:
            return self._default
        return getattr(owner, self.private_name, self._default)


class Controller:
    def __init__(self, card):
        self.card = card

    def __call__(self, game_state):
        return game_state.get(self.card).controller

class Zone:
    owner = Get()
    def __init__(self, zone: zones.Zone, owner=None, position=None):
        self.zone = zone
        self.owner = owner
        self.postion = position
    
    def __call__(self, game_state):
        return type(self.zone)(
            self.owner(game_state), 
            self.postion)

class FromZone:

    zone = Get()

    def __init__(self, zone, top=None, bottom=None):
        self.zone = zone
        self.top = top
        self.bottom = bottom

    def __call__(self, game_state):
        zone = game_state.in_zone(self.zone(game_state))
        if self.top is not None:
            return zone[-(1+self.top):]
        if self.bottom is not None:
            return zone[:self.bottom]
        
        return zone


class ActivePlayer:
    def __call__(self,game_state):
        return game_state.players[game_state.active_player]
    

class UpTo:
    """
    Get every way to choose n or fewer items from a list that satisfy a predicate
    Returns an iterator that enumerates all possibilities from most choices
    to fewest choices
    """
    def __init__(self, n, predicate):
        self.n = n 
        self.predicate = predicate
    
    def __call__(self, iterable):
        iter_filtered = enumerate(tee(filter(self.predicate, iterable), self.n))
        return chain(chain.from_iterable(
            combinations(filtered,self.n - i) 
            for (i,filtered) in iter_filtered
        ), [{}])
