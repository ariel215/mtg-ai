from dataclasses import dataclass
from typing import Optional, TypeVar


Player = TypeVar('Player')

@dataclass(slots=True)
class Zone:
    owner: Optional[Player] = None
    position: Optional[int] = None

    def contains(self, card):
        return (
            type(self) is type(card.zone) 
            and (self.owner is None or self.owner == card.zone.owner)
            and (self.position is None or self.position == card.zone.position) 
        )
    
    def __str__(self):
        return f"{type(self)}({self.owner})[{self.position}]"

    def copy(self):
        return type(self)(self.owner, self.position)
    
    def __hash__(self):
        return hash(
            (type(self),
            self.owner,
            self.position)
        )
    
    def __eq__(self, value):
        return hash(self) == hash(value)

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
    def contains(self, _card):
        return True


class TOP:
    """
    Singleton representing the top of a zone
    """
    pass

class BOTTOM:
    """
    Singleton representing the bottom of a zone
    """
    pass
