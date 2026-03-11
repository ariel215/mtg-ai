from collections import defaultdict
from mtg_ai import game, actions, mana, zones, getters
from typing import Iterable, Optional, List, Callable
from mtg_ai.mana import Mana


class CardState:
    """
    Mutable, Copy-on-Write card state.

    Holds the per-game-state data for a card: zone, tapped, counters.
    Supports CoW via _owner: Card sets _owner = self after construction or
    after forking. Card._cow_state() forks this object before any mutation
    when _owner is not self.
    """
    __slots__ = ('zone', 'tapped', 'counters', '_owner')

    def __init__(self, zone=None, tapped=False, counters=None):
        self.zone = zone
        self.tapped = tapped
        self.counters = counters if counters is not None else defaultdict(lambda: 0)
        self._owner = None

    def copy(self):
        new = CardState(
            zone=self.zone,
            tapped=self.tapped,
            counters=defaultdict(lambda: 0, self.counters),
        )
        return new
 
class CardAttributes:
    """
    Immutable card definition — the flyweight.

    One instance per card uid, shared across all GameState copies of that card.
    Holds only data that never changes during a game: name, cost, types, abilities, etc.
    Never copied after initial construction.
    """
    __slots__ = (
        '_name', '_cost', '_types', '_subtypes',
        '_power', '_toughness', '_static', '_activated', '_keywords',
    )

    def __init__(self, name, cost, types, subtypes, *,
                 power: Optional[int] = None,
                 toughness: Optional[int] = None,
                 static: List = None,
                 activated: List = None,
                 keywords=None):
        self._name = name
        self._cost = cost
        self._types = set(types)
        self._subtypes = set(subtypes)
        self._power = power
        self._toughness = toughness
        self._static = static or []
        self._activated = activated or []
        self._keywords = keywords or []


class _CardAttrsProxy:
    """
    Lightweight view of a CardAttributes in the context of a specific Card.

    Created on each access to Card.attrs.  Provides pass-through access to
    all immutable attributes plus game-state-aware computation of power and
    toughness (applying active static effects from the card's game state).
    """
    __slots__ = ('_def', '_card')

    def __init__(self, card_def: CardAttributes, card: 'Card'):
        self._def = card_def
        self._card = card

    def __getattribute__(self,name):
        def_ = object.__getattribute__(self,'_def') # self._def
        card = object.__getattribute__(self, '_card') # self._card
        base = object.__getattribute__(def_, '_' + name)
        
        if base is None:
            return None
        for effect in card.game_state.active_statics:
            if effect.matches(name,card):
                base = effect.modification(card.game_state, base)
        return base


class Card(game.GameObject):
    """
    Representation of a card.

    A thin wrapper around an immutable CardAttributes flyweight (_def) and a
    mutable Copy-on-Write CardState (_state).  Copying a Card shares _def
    entirely and only copies the small _state, so the expensive definition
    data is never re-allocated across game-state copies.

    Attributes:
        attrs:    proxy giving access to definition data and effect-aware stats
        zone:     the zone this card is currently in
        tapped:   whether this card is tapped
        counters: dict of counters on this card
    """

    cards = {}

    def __init__(self,
                 name: str,
                 game_state: 'game.GameState',
                 owner,
                 *,
                 cost: Optional[Mana] = None,
                 types: Iterable['game.CardType'] = (),
                 subtypes: Iterable[str] = (),
                 tapped: bool = False,
                 static: List['game.StaticAbility'] = None,
                 activated: List['actions.ActivatedAbility'] = None,
                 effect: Optional['game.Action'] = None,
                 zone: Optional['zones.Zone'] = None,
                 power: Optional[int] = None,
                 toughness: Optional[int] = None,
                 keywords: Iterable[str] = (),
                 ):
        super().__init__(game_state)
        self.owner = owner
        self._def = CardAttributes(
            name=name,
            cost=cost,
            types=types,
            subtypes=set(st.lower() for st in subtypes),
            power=power,
            toughness=toughness,
            static=static or [],
            activated=activated or [],
            keywords=set(kw.lower() for kw in keywords),
        )
        self._state = CardState(zone=zone, tapped=tapped)
        self._state._owner = self

        if self._def._types & game.SPELL_TYPES:
            dest_zone = zones.Grave(owner=owner)
        else:
            dest_zone = zones.Field(owner=owner)
        dest = actions.MoveTo(dest_zone).bind(card=self)
        self.effect = effect + dest if effect is not None else dest

        if game_state is not None:
            for sa in self._def._static:
                sa.on_move(self.game_state)

    # ── attrs proxy ────────────────────────────────────────────────────────────

    @property
    def attrs(self) -> _CardAttrsProxy:
        return _CardAttrsProxy(self._def, self)

    # ── mutable state properties (all trigger CoW) ─────────────────────────────

    @property
    def zone(self):
        return self._state.zone

    @zone.setter
    def zone(self, zone: 'zones.Zone'):
        self._cow_state()
        self._state.zone = zone
        if self.game_state is not None:
            for sa in self._def._static:
                sa.on_move(self.game_state)

    @property
    def tapped(self) -> bool:
        return self._state.tapped

    @tapped.setter
    def tapped(self, value: bool):
        self._cow_state()
        self._state.tapped = value

    @property
    def counters(self):
        return self._state.counters

    @counters.setter
    def counters(self, value):
        self._cow_state()
        self._state.counters = value

    # ── Copy-on-Write ──────────────────────────────────────────────────────────

    def _cow_state(self):
        """Fork CardState if it is currently shared with another Card."""
        if self._state._owner is not self:
            self._state = self._state.copy()
            self._state._owner = self

    # ── Fluent builder methods ─────────────────────────────────────────────────

    def activated(self, cost: 'game.Action', effect: 'game.Action',
                  uses_stack: bool = False):
        """Add an activated ability to this card."""
        self._def._activated.append(actions.ActivatedAbility(
            cost=cost, effect=effect, uses_stack=uses_stack,
        ))
        return self

    def triggered(self,
                  when: 'type[game.Action]',
                  condition: 'Callable[[game.Event], bool]',
                  action: 'game.Action',
                  active_zone: 'zones.Zone' = zones.Field()):
        """Add a triggered ability to this card."""
        trigger = game.TriggeredEffect(when=when, condition=condition, action=action)
        sa = game.StaticAbility(active_zone=active_zone, source=self, effect=trigger)
        self._def._static.append(sa)
        return self

    def static(self,
               condition: 'Callable[[Card], bool]',
               property_name: str,
               modification: Callable,
               active_zone: 'zones.Zone' = zones.Field(),
               affected_zone: 'zones.Zone' = zones.Field()):
        """Add a static ability to this card."""
        full_condition = lambda c: affected_zone.contains(c) and condition(c)
        effect = game.StaticEffect(property_name=property_name,
                                   condition=full_condition,
                                   modification=modification)
        sa = game.StaticAbility(active_zone=active_zone, source=self, effect=effect)
        self._def._static.append(sa)
        return self

    def with_effect(self, effect: 'game.Action'):
        """Add an effect that happens when this card resolves."""
        self.effect = effect if self.effect is None else self.effect + effect

    # ── Computed properties ────────────────────────────────────────────────────

    @property
    def controller(self):
        return self.zone.owner

    @property
    def mana_value(self):
        if self._def._cost is None:
            return 0
        return self._def._cost.mana_value

    # ── Copy ───────────────────────────────────────────────────────────────────

    def copy(self, game_state: 'game.GameState') -> 'Card':
        """
        Return a copy of this card registered in game_state.

        _def (CardAttributes) is shared — the flyweight is never re-allocated.
        _state (CardState) is copied; the new card immediately owns its state.
        """
        card = object.__new__(type(self))
        # replicate what GameObject.__init__ would do (append pattern)
        card.game_state = game_state
        card.uid = len(game_state.objects)
        game_state.objects.append(card)
        card.owner = self.owner
        card._def = self._def              # shared flyweight — never copied
        card._state = self._state.copy()  # only the small mutable state is copied
        card._state._owner = card
        card.effect = self.effect
        return card

    # ── Dunder methods ─────────────────────────────────────────────────────────

    def __str__(self):
        return f"{self._def._name}({self.zone})"

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash((self._def._name, self.zone, self.tapped))

    def __eq__(self, value):
        return type(self) is type(value) and hash(self) == hash(value)
