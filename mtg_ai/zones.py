from dataclasses import dataclass
from typing import Optional, TypeVar


Player = TypeVar('Player')

@dataclass(slots=True)
class Zone:
    """
    This class represents both the particular location a card is in 
    in the game, and a zone containing a set of cards

    Every zone except for the stack is owned by a particular player.

    The library and the stack have a fixed order.
    """
    owner: Optional[Player] = None
    position: Optional[int] = None

    def contains(self, card) -> bool:
        """
        Whether a zone contains a particular card.

        If `self.owner` is None, it matches any player, and likewise 
        `self.position` matches any position when it is None.
        """
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
    def contains(self, card) -> bool:
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
