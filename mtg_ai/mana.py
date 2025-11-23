from dataclasses import dataclass

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
    
