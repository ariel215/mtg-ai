from mtg_ai import game, actions, getters, zone
from typing import Iterable, Optional
from dataclasses import dataclass, field
from enum import Enum


class CardType(str, Enum):
    Land = "land"
    Creature = "creature"
    Instant = "instant"
    Sorcery = "sorcery"
    Artifact = "artifact"

class Card(game.GameObject):
    cards = {}
    @dataclass
    class Abilities:
        static: list = field(default_factory=list)
        activated: list = field(default_factory=list)

    def __init_subclass__(cls):
        Card.cards[cls.__name__] = cls

    def __init__(self, name,
                 cost: Optional[game.Mana] = None,
                 types: Iterable[CardType]=(),
                 subtypes: Iterable[str] = (),
                 abilities: Optional[Abilities] = None,
                 zone:Optional[zone.Zone]=None,
                 permanent: bool = False,
                 tapped: bool = False,
                 game_state: Optional[game.GameState] = None,
             ):

        super().__init__(game_state)
        self.cost = cost
        self.zone = zone 
        self.name = name
        self.types = set(types)
        self.subtypes = set(st.lower() for st in subtypes)
        self.permanent = permanent
        self.tapped = tapped
        self.abilities = abilities or Card.Abilities()


    def activated(self, cost: game.Action, effect: game.Action, uses_stack: bool=False):
        self.abilities.activated.append(actions.ActivatedAbility(
            cost=cost,
            effect=effect,
            uses_stack=uses_stack
        ))
        return self

    def triggered(self, when: type(game.Action), condition, action: actions.Action):
        when.triggers.append(actions.Trigger(condition=condition, action=action))
        return self

    @property
    def summoning_sick(self):
        return self.permanent and self.permanent.summoning_sick

    @property
    def controller(self):
        return self.zone.owner
            
    def make_permanent(self):
        self.permanent = True

    def del_permanent(self):
        self.permanent = False

    def copy(self):
        return Card(name=self.name,
                    types=self.types,
                    subtypes=self.subtypes,
                    cost=self.cost,
                    abilities=self.abilities,
                    zone=self.zone,
                    permanent=self.permanent,
                    tapped=self.tapped,
                    game_state=self.game_state)

    def __str__(self):
        return f"[{self.name}@{self.zone}]"

    def __repr__(self):
        return str(self)

  
