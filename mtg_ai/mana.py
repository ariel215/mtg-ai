from itertools import chain
from functools import cached_property, cache
from dataclasses import dataclass, asdict

COLORS = ('white', 'blue', 'black', 'red', 'green', 'colorless')
FIELDS = ('white', 'blue', 'black', 'red', 'green', 'gold', 'colorless','generic')

@dataclass(unsafe_hash=True,slots=True)
class Mana:
    white: int = 0
    blue: int = 0
    black: int = 0
    red: int = 0
    green: int = 0
    gold: int = 0 # stand-in for mana of any color
    colorless: int = 0
    generic: int = 0

    def __str__(self):
        return f"Mana({','.join(f'{k}={v}' for k,v in [(field,getattr(self,field)) for field in FIELDS] if v)})"

    def __repr__(self):
        return str(self)

    @classmethod
    def parse(cls, amount: str):
        mana = cls()
        abbreviations = {
            'w': 'white',
            'u': 'blue',
            'b': 'black',
            'r': 'red',
            'g': 'green',
            'a': 'gold', # any color
            'c': 'colorless'
        }
        for char in amount.lower():
            if field := abbreviations.get(char):
                setattr(mana, field, getattr(mana, field) + 1)
            else:
                mana.generic += int(field)
        return mana

    def __add__(self, other):
        result = self.copy()
        for field in FIELDS:
            current = getattr(self,field)
            setattr(result,field,current + getattr(other, field))
        return result

    def __sub__(self, cost):
        """
        Use the mana in `self` to pay the mana cost `cost`
        """
        result = self.copy()
        # step one: pay for colored costs with colored mana
        for field in COLORS:
            current = getattr(result,field)
            setattr(result,field,current - getattr(cost, field))

        # step two: pay remaining colored costs with gold mana
        gold = cost.gold
        for field in COLORS:
            if color_cost := getattr(result, field):
                amt = min(color_cost, gold)
                setattr(self, field, color_cost-amt)
                gold -= amt
            break
        
        generic_cost = cost.generic
        # step four: pay generic costs, starting with colorless mana
        for field in list(reversed(COLORS)) + ['gold']:
            value = getattr(result, field)
            amt = min(generic_cost, value)
            setattr(self, field, value - amt)
            generic_cost -= amt 
        return self

    def __mul__(self, amount):
        result = self.copy()
        for field in FIELDS:
            setattr(result, field, getattr(result, field) * amount)
        return result

    @property
    @cache
    def mana_value(self):
        return sum(getattr(self, field)
         for field in FIELDS
     )

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return all(
            getattr(self, field) == getattr(other, field)
             for field in chain(COLORS,('gold','colorless','generic'))
        )

    def can_pay(self, other)->bool:
        """
        Returns whether `self` can pay the cost `other` 
        """
        gold_available = self.gold
        for field in COLORS:
            self_color = getattr(self, field)
            other_color = getattr(other, field)
            if self_color >= other_color:
                continue
            # else
            other_color -= self_color
            if gold_available > other_color:
                gold_available -= other_color
                continue
            # else
            return False

        return self.mana_value >= other.mana_value        

    def copy(self):
        return Mana(self.white, self.blue,self.black,self.red,self.green,self.gold,self.colorless,self.generic)
    
