from collections import defaultdict
from mtg_ai import game, actions, mana, zones
from mtg_ai.game import (CardType, SPELL_TYPES, StaticAbility, StaticEffect, TriggeredEffect,
                         Event)
from typing import Iterable, Optional, TypeVar, Set, List, Callable
from mtg_ai.game import CardType, SPELL_TYPES, GameState
from typing import Iterable, Optional, TypeVar
from dataclasses import dataclass, field
from enum import Enum

Action = TypeVar('Action')


class Card(game.GameObject):
    """
    Representation of a card.

    Attributes:
        name: the card's name
        cost: the amount of mana required to cast this card, if it is a spell.
        types: this card's card types
        subtypes: this card's subtypes
        abilities: this card's abilities
        effect: The action that should be taken when this card resolves, if it is
                a spell
        zone: The zone this card is in, if any.
        tapped: whether this card is tapped.
    """

    cards = {}

    class GetProperty[T]:
        """
        Many properties of a Card can be modified by ongoing static effects.
        This descriptor allows those properties to be affected by other things
        in the GameState.
        """

        def __set_name__(self, owner: 'Card', name: str):
            self.private_name = f"_{name}"
            self.public_name = name

        def __set__(self, owner: 'Card', value: T):
            assert(hasattr(owner, self.private_name))
            setattr(owner, self.private_name, value)

        def __get__(self, owner: 'Card', _objname) -> T:
            base = getattr(owner, self.private_name, None)
            if base is None:
                return None
            for effect in owner.game_state.active_statics:
                if effect.matches(self.public_name, owner):
                    # TODO: if condition cares about this properly, we will get an infinite loop
                    base = effect.modification(owner.game_state, base)
            return base

    power = GetProperty()
    toughness = GetProperty()
    types = GetProperty()
    subtypes = GetProperty()
    abilities = GetProperty()
    keywords = GetProperty()

    @dataclass
    class Abilities:
        static: List[game.StaticAbility] = field(default_factory=list) # includes triggered
        activated: List[actions.ActivatedAbility] = field(default_factory=list)

    def __init__(self, name:str,
                game_state: GameState,
                *,
                 cost: Optional[mana.Mana] = None,
                 types: Iterable[CardType]=(),
                 subtypes: Iterable[str] = (),
                 abilities: Optional[Abilities] = None,
                 effect: Optional[Action] = None,
                 zone:Optional[zones.Zone]=None,
                 tapped: bool = False,
                 power: Optional[int] = None,
                 toughness: Optional[int] = None,
                 keywords: Iterable[str] = (),
             ):

        super().__init__(game_state)
        self.cost = cost
        self._zone = zone  # private so setter can add/remove TemporaryEffects
        self.name = name
        self._types = set(types)
        self._subtypes: Set[str] = set(st.lower() for st in subtypes)
        self.tapped = tapped
        self._abilities = abilities or Card.Abilities()
        self.counters = defaultdict(lambda: 0)
        self._effect = effect
        self._power: Optional[int] = power
        self._toughness: Optional[int] = toughness
        self._keywords: Set[str] = set(kw.lower() for kw in keywords)

        if game_state is not None:
            for static in self.abilities.static:
                static.on_move(self.game_state)

    @property
    def effect(self):
        """
        The full effect of resolving a spell, in addition to any card-specific effects.
        Instants and sorceries go to the graveyard on resolution; all other
        card types are put into play
        """

        dest_zone = zones.Grave(self.controller) if self.types & SPELL_TYPES else zones.Field(self.controller)
        dest = actions.MoveTo(dest_zone).bind(card=self)
        if self._effect:
            return self._effect + dest
        else:
            return dest

    @property
    def zone(self) -> zones.Zone | None:
        return self._zone

    @zone.setter
    def zone(self, zone: zones.Zone):
        self._zone = zone
        if self.game_state is not None:
            for static in self.abilities.static:
                static.on_move(self.game_state)


    def activated(self, cost: game.Action, effect: game.Action, uses_stack: bool=False):
        """
        Add an activated ability to this card.

        Args:
            cost: the action that must be taken to activate the ability
            effect: the action that is performed by the ability
            uses_stack: whether the ability is put on the stack.
                        Mana abilities and special actions do not use the stack.
        """
        self.abilities.activated.append(actions.ActivatedAbility(
            cost=cost,
            effect=effect,
            uses_stack=uses_stack
        ))
        return self

    def triggered(self,
                  when: type[game.Action],
                  condition: Callable[[Event], bool],
                  action: actions.Action,
                  active_zone: zones.Zone = zones.Field()):
        """
        Add a triggered ability to this card.
        """
        trigger = TriggeredEffect(when=when, condition=condition, action=action)
        static = StaticAbility(active_zone=active_zone, source=self, effect=trigger)
        self.abilities.static.append(static)
        return self

    def static(self,
               condition: 'Callable[[Card], bool]',
               property_name: str,
               modification: Callable,
               active_zone: zones.Zone = zones.Field(),
               affected_zone: zones.Zone = zones.Field()):
        """
        Add a static ability to this card.
        """
        full_condition = lambda c: affected_zone.contains(c) and condition(c)
        effect = StaticEffect(property_name=property_name,
                              condition=full_condition,
                              modification=modification)
        static = StaticAbility(active_zone=active_zone, source=self, effect=effect)
        self.abilities.static.append(static)
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

    def copy(self, game_state: GameState):
        return Card(name=self.name,
                    types=self._types,
                    subtypes=self._subtypes,
                    cost=self.cost,
                    abilities=self._abilities,
                    effect=self._effect,
                    zone=self.zone,
                    tapped=self.tapped,
                    game_state=game_state,
                    power=self._power,
                    toughness=self._toughness,
                    keywords=self._keywords,
                    )

    def __str__(self):
        return f"{self.name}({self.zone})"

    def __repr__(self):
        return str(self)
    
    def __hash__(self):
        return hash(
            (self.name,
            self.zone,
            self.tapped
            )
        )

    def __eq__(self, value):
        return type(self) is type(value) and hash(self) == hash(value)
    


