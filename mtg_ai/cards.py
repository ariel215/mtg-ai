from collections import defaultdict
from mtg_ai import game, actions, mana, zones
from typing import Iterable, Optional, TypeVar, Set, List, Callable
from mtg_ai.mana import Mana

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

    class CardAttributes:
        def __init__(self, card, name, cost, types, subtypes, *,
                     power: Optional[int] = None,
                     toughness: Optional[int] = None,
                     static: List[game.StaticAbility] = None,
                     activated: List[actions.ActivatedAbility] = None,
                     keywords: Iterable[str] = None):
            self._name: str = name
            self._cost: Mana = cost
            self._types: Set[game.CardType] = set(types)
            self._subtypes: Set[str] = set(subtypes)
            self._power: int | None = power
            self._toughness: int | None = toughness
            self._static: List[game.StaticAbility] = static or []
            self._activated: List[actions.ActivatedAbility] = activated or []
            self._keywords = keywords or []
            self._card = card

        def __setattr__(self, key, value):
            if hasattr(self, "_" + key):
                super().__setattr__("_" + key, value)
            else:
                super().__setattr__(key, value)

        def __getattr__(self, attribute_name):
            base = self.__getattribute__("_" + attribute_name)
            if base is None:
                return None
            card = self._card
            for effect in card.game_state.active_statics:
                if effect.matches(attribute_name, card):
                    # TODO: if condition cares about this properly, we will get an infinite loop
                    base = effect.modification(card.game_state, base)
            return base

        def copy(self, new_card):
            return Card.CardAttributes(card=new_card,
                                       name = self._name,
                                       cost = self._cost,
                                       power=self._power,
                                       toughness=self._toughness,
                                       types=self._types,
                                       subtypes=self._subtypes,
                                       static = self._static,
                                       activated=self._activated,
                                       keywords=self._keywords)
    @property
    def effect(self):
        """
        The full effect of resolving a spell, in addition to any card-specific effects.
        Instants and sorceries go to the graveyard on resolution; all other
        card types are put into play
        """
        if self.attrs.types & game.SPELL_TYPES:
            dest_zone = zones.Grave(self.controller)
        else:
            dest_zone = zones.Field(self.controller)
        dest = actions.MoveTo(dest_zone).bind(card=self)
        if self._effect:
            return self._effect + dest
        else:
            return dest


    def __init__(self,
                 name:str,
                 game_state: game.GameState,
                 *,
                 cost: Optional[mana.Mana] = None,
                 types: Iterable[game.CardType]=(),
                 subtypes: Iterable[str] = (),
                 tapped: bool = False,

                 static: List[game.StaticAbility] = None,
                 activated: List[actions.ActivatedAbility] = None,
                 effect: Optional[game.Action] = None,
                 zone:Optional[zones.Zone]=None,

                 power: Optional[int] = None,
                 toughness: Optional[int] = None,
                 keywords: Iterable[str] = (),
                 ):

        super().__init__(game_state)
        self._zone = zone  # private so setter can add/remove TemporaryEffects
        self.attrs = Card.CardAttributes(card=self,
                                         name=name,
                                         cost=cost,
                                         power=power,
                                         toughness=toughness,
                                         types=types,
                                         subtypes=set(st.lower() for st in subtypes),
                                         static=static or [],
                                         activated=activated or [],
                                         keywords=set(kw.lower() for kw in keywords))
        self.tapped = tapped
        self.counters = defaultdict(lambda: 0)
        self._effect = effect
        if game_state is not None:
            for static in self.attrs.static:
                static.on_move(self.game_state)

    @property
    def zone(self) -> zones.Zone | None:
        return self._zone

    @zone.setter
    def zone(self, zone: zones.Zone):
        self._zone = zone
        if self.game_state is not None:
            for static in self.attrs.static:
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
        self.attrs.activated.append(actions.ActivatedAbility(
            cost=cost,
            effect=effect,
            uses_stack=uses_stack
        ))
        return self

    def triggered(self,
                  when: type[game.Action],
                  condition: Callable[[game.Event], bool],
                  action: game.Action,
                  active_zone: zones.Zone = zones.Field()):
        """
        Add a triggered ability to this card.
        """
        trigger = game.TriggeredEffect(when=when, condition=condition, action=action)
        static = game.StaticAbility(active_zone=active_zone, source=self, effect=trigger)
        self.attrs.static.append(static)
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
        effect = game.StaticEffect(property_name=property_name,
                                   condition=full_condition,
                                   modification=modification)
        static = game.StaticAbility(active_zone=active_zone, source=self, effect=effect)
        self.attrs.static.append(static)
        return self

    def with_effect(self,effect: game.Action):
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
        if self.attrs.cost is None:
            return 0
        return self.attrs.cost.mana_value

    def copy(self, game_state: game.GameState):
        card = Card(name=self.attrs.name, # will be overwritten by attrs
                    game_state=game_state,
                    )
        card.attrs = self.attrs.copy(card)
        card.tapped = self.tapped
        card._effect = self._effect
        card._zone = self._zone
        card.counters = defaultdict(lambda: 0, self.counters)
        # Don't need to sync the statics, because game_state.copy() will do that
        return card

    def __str__(self):
        return f"{self.attrs.name}({self.zone})"

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(
            (self.attrs.name,
             self.zone,
             self.tapped
             )
        )

    def __eq__(self, value):
        return type(self) is type(value) and hash(self) == hash(value)
    


