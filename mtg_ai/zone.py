from dataclasses import dataclass
from typing import Optional, TypeVar


Player = TypeVar('Player')

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

    def short(self):
        name=type(self).__name__[0]
        if self.owner:
            name+=str(self.owner)[0]
        if self.position:
            name+=str(self.position)
        return name 

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
