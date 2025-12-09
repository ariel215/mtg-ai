from mtg_ai import game, actions, mana, zones
from mtg_ai.game import CardType, SPELL_TYPES
from typing import Iterable, Optional, TypeVar
from dataclasses import dataclass, field
from enum import Enum

Action = TypeVar('Action')


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
                 tapped: bool = False,
                 game_state: Optional[game.GameState] = None,
             ):

        super().__init__(game_state)
        self.cost = cost
        self.zone = zone 
        self.name = name
        self.types = set(types)
        self.subtypes = set(st.lower() for st in subtypes)
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
        """
        Add an activated ability to this card.

        Params:
        cost: the action that must be taken to activate the ability
        effect: the action that is performed by the ability
        uses_stack: whether the ability is put on the stack. Mana abilities and 
        special actions do not use the stack.
        """
        self.abilities.activated.append(actions.ActivatedAbility(
            cost=cost,
            effect=effect,
            uses_stack=uses_stack
        ))
        return self

    def triggered(self, when: type[game.Action], condition, action: actions.Action):
        """
        Add a triggered ability to this card.
        """
        when.triggers.append(actions.Trigger(condition=condition, action=action, source=self))
        return self
    
    def with_effect(self,effect: actions.Action):
        """
        Add an effect that happens when this card resolves. 
        This is mostly for instants and sorceries, but is also used to implement
        choices that are made as a permanent enters the battlefield, such as shocklands
        and Cavern of Souls.
        """
        self._effect = effect if self._effect is None else self._effect + effect

    @property
    def controller(self):
        return self.zone.owner
    
    @property
    def mana_value(self):
        if self.cost is None:
            return 0
        return self.cost.mana_value
            
    def copy(self):
        return Card(name=self.name,
                    types=self.types,
                    subtypes=self.subtypes,
                    cost=self.cost,
                    abilities=self.abilities,
                    effect=self._effect,
                    zone=self.zone,
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

