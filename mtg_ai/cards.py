from mtg_ai import game, actions, getters, mana, zones
from typing import Iterable, Optional, TypeVar
from dataclasses import dataclass, field
from enum import Enum

Action = TypeVar('Action')


class CardType(str, Enum):
    Land = "land"
    Creature = "creature"
    Instant = "instant"
    Sorcery = "sorcery"
    Artifact = "artifact"

SPELL_TYPES = {CardType.Instant, CardType.Sorcery}

class Card(game.GameObject):
    cards = {}
    @dataclass
    class Abilities:
        static: list = field(default_factory=list)
        activated: list = field(default_factory=list)

    def __init_subclass__(cls):
        Card.cards[cls.__name__] = cls

    def __init__(self, name,
                 cost: Optional[mana.Mana] = None,
                 types: Iterable[CardType]=(),
                 subtypes: Iterable[str] = (),
                 abilities: Optional[Abilities] = None,
                 effect: Optional[Action] = None,
                 zone:Optional[zones.Zone]=None,
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
        self._effect = effect
        
    @property
    def effect(self):
        dest_zone = zones.Grave(self.controller) if self.types & SPELL_TYPES else zones.Field(self.controller)
        dest = actions.MoveTo(dest_zone).bind(card=self)
        if self._effect:
            return self._effect + dest
        else:
            return dest

    def activated(self, cost: game.Action, effect: game.Action, uses_stack: bool=False):
        self.abilities.activated.append(actions.ActivatedAbility(
            cost=cost,
            effect=effect,
            uses_stack=uses_stack
        ))
        return self

    def triggered(self, when: type[game.Action], condition, action: actions.Action):
        when.triggers.append(actions.Trigger(condition=condition, action=action))
        return self
    
    def with_effect(self,effect: actions.Action):
        self._effect = effect if self._effect is None else self._effect + effect

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
                    effect=self._effect,
                    zone=self.zone,
                    permanent=self.permanent,
                    tapped=self.tapped,
                    game_state=self.game_state)

    def __str__(self):
        return f"[{self.name}@{self.zone}]"

    def __repr__(self):
        return str(self)
    

# -------------------------------------------------

# Cards in walls: 

# [x] Caretaker
# [x] Caryatid
# Roots
# [x] Battlement
# [x] Axebane
# [x] Blossoms
# [x] Arcades
# Recruiter
# TrophyMage
# Staff
# Company

# [x] Forest
# [x] Plains
# [x] Island
# TempleGarden
# BreedingPool
# HallowedFountain
# WindsweptHeath
# Westvale
# Wildwoods
# LumberingFalls

