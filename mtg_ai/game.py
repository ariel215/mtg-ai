from collections.abc import Callable
from enum import Enum
from itertools import chain, product
from typing import TypeVar, Optional, List, Dict, Any, TYPE_CHECKING, Set
from . import zones
from .mana import Mana

if TYPE_CHECKING:
    from actions import Trigger
    from cards import Card

Player = int
GenericStackObject = TypeVar('GenericStackObject')
GenericGameObject = TypeVar('GenericGameObject', bound='GameObject')

class Event:
    def __init__(self, action, game_state: 'GameState', source=None, cause=None, ):
        self.action = action 
        self.source = source
        self.cause = cause
        self.game_state = game_state

class GameState:

    def __init__(self,players: List[Player], mana_pool: Optional['Mana']=None, turn_number=0):
        self.objects = {}
        self.players = players
        self.mana_pool = mana_pool or Mana()
        self.turn_number = turn_number
        self.parent = None
        self.children = []
        self.triggers = [] # triggers waiting to go onto the stack
        self.summoning_sick = set() # summoning sick cards
        self.land_drops = 1
        self.active_player = 0
        self.active_effects: 'List[ActiveEffect]' = []

    def __hash__(self):
        return hash(
            tuple(chain((self.mana_pool, self.active_player),self.objects.values()))
        )
    
    def __eq__(self, value):
        return type(self) is type(value) and hash(self) == hash(value)
            
    def copy(self) -> 'GameState':
        new_game_state = GameState(self.players,self.mana_pool.copy(), self.turn_number)
        uids = [uid for uid in self.objects]
        for uid in uids:
            self.objects[uid].move_to(new_game_state)
        new_game_state.summoning_sick = {new_game_state.get(card) for card in self.summoning_sick}
        self.children.append(new_game_state)
        new_game_state.parent = self
        new_game_state.triggers = self.triggers.copy()
        new_game_state.active_effects = self.active_effects.copy()
        return new_game_state

    def in_zone(self, zone: zones.Zone)->List['GameObject']:
        return sorted([c for c in self.objects.values() if zone.contains(c)],
                      key=lambda card: card.zone.position or float('-inf'))

    def get(self, obj: GenericGameObject) -> GenericGameObject:
        return self.objects[obj.uid]

    def stack(self, card):
        owner = card.zone.owner if card.zone else None
        stack = self.in_zone(zones.Stack())
        if stack:
            top = max(obj.zone.position for obj in stack)
            card.zone = zones.Stack(owner=owner, position=top+1)
        else:
            card.zone = zones.Stack(owner=owner, position=0)

    def resolve_stack(self) -> 'GameState':
        """
        Resolve the top of the stack
        """
        stack = self.in_zone(zones.Stack())
        top = stack.pop()
        choices = top.effect.choices(self)

        new_state = self.take_action(top.effect, choices[0])
        return new_state

    def take_action(self, action: 'Action', choices: Dict[str, Any] | None = None, copy:bool=True)->'GameState':
        choices = choices or {}
        new_state = self.copy() if copy else self
        event = action.perform(new_state, **choices)
        new_state = event.game_state
        new_state.triggers.extend(
            (event,trigger) for trigger in new_state.active_triggers if trigger.matches(event)
        )
        return new_state

    def stack_triggers(self):
        for (event, trigger) in self.triggers:
            trigger.do(self, event)
        self.triggers.clear()

    @property
    def active_triggers(self) -> List['TriggeredEffect']:
        return [active.effect for active in self.active_effects if active.is_trigger]

    @property
    def active_statics(self) -> List['StaticEffect']:
        return [active.effect for active in self.active_effects if active.is_static]


class GameObject:
    maxid = 0
    def __init__(self, game_state: GameState, uid: Optional[int]=None):
        self.game_state = game_state
        if uid is None:
            self.uid = GameObject.maxid
            GameObject.maxid += 1
        else:
            self.uid = uid
        game_state.objects[self.uid] = self
        self._zone: Optional[zones.Zone] = None

    def move_to(self, new_game_state: GameState):
        cpy = self.copy()
        tmp_uid = cpy.uid
        cpy.game_state = new_game_state
        cpy.uid = self.uid
        new_game_state.objects[self.uid] = cpy
        del self.game_state.objects[tmp_uid]
        return cpy
    
    def copy(self) -> 'GameObject':
        raise NotImplemented

    @property
    def zone(self) -> zones.Zone | None:
        return self._zone

    @zone.setter
    def zone(self, value):
        self._zone = value

T = TypeVar('T')
type Choice[T] = Dict[str, T]
type ChoiceSet[T] = List[Choice[T]]

class Action:
    def __init__(self):
         self.params = {}
 
    def bind(self, **kwargs):
         self.params |= kwargs
         return self

    def choices[T](self,game_state) -> ChoiceSet[T]:
        """
        The possible choices that can be made for this action.
        For example: If a player has to sacrifice a creature, 
        the choices are the creatures that player controls.

        Each element of the ChoiceList should be a dictionary whose 
        keys are the same as the keyword arguments to `do()`.
        """
        raise NotImplemented
 
    def choose(self, game_state):
         # cls.choices() should not let you choose anything set in self.params
         choices =self.choices(game_state)
         return [
             {c: choice[c] for c in choice.keys() - self.params.keys()}
             for choice in choices 
         ]
 
    def perform(self, game_state, **kwargs) -> Event:

        if event := self.do(game_state, **(kwargs | self.params)):
            return event
        return Event(self, game_state)
 
    def do[T](self, game_state, **kwargs: Choice[T]) -> Event:
        """
        Make the necessary changes to the game state. 
        Each action should have all the information 
        needed to make its constituent changes.
        """
        raise NotImplemented
    
    def __add__(self, other: 'Action') -> 'And':
        return And(self, other)


class And(Action):
    def __init__(self, *actions):
        super().__init__()
        self.actions: List[Action] = list(actions)

    def choices(self,game_state):
        subchoices = [action.choices(game_state) for action in self.actions]
        combinations = list(product(*subchoices))
        return [{'choices': option }
        for option in combinations]
    
    def do(self, game_state, choices):
        for action, choice in zip(self.actions, choices):
            game_state = game_state.take_action(action, choice)
        return Event(self, game_state)

    def __add__(self, other: Action):
        new_action = And(*self.actions)
        new_action.actions.append(other)
        return new_action

class StackAbility(GameObject):
    """
    An ability that is on the stack, waiting to resolve
    """

    class Cleanup(Action):
        def __init__(self, obj):
            super().__init__()
            self.obj = obj
            
        def choices(self, _game_state):
            return [{}]

        def do(self, game_state):
            del game_state.objects[self.obj.uid]

    def __init__(self,game_state: GameState,
                 effect):
        super().__init__(game_state)
        self.effect: Action = effect + StackAbility.Cleanup(self)

    def copy(self) -> 'StackAbility':
        ability = StackAbility(
            game_state=self.game_state,
            effect=self.effect
        )
        ability.zone=self.zone
        ability.effect = self.effect
        return ability


class StaticEffect:
    """
    A static effect waits for the given property of a Card to be checked. When
    a Card would return a value for a matching property, it first applies this
    modification to the value.
    Example: "+1/+1 until EoT" are two effects modifying the "power" and
    "toughness" properties.
    """
    def __init__(self,
                 property_name: str,
                 condition: 'Callable[[Card], bool]',
                 modification: Callable[[GameState, T], T]):
        self.property_name = property_name
        self.condition = condition
        self.modification = modification

    def matches(self, property_name: str, card: 'Card') -> bool:
        return self.property_name == property_name and self.condition(card)

    def do(self, game_state: GameState, value: T) -> T:
        return self.modification(game_state, value)


class TriggeredEffect:
    """
    A triggered effect waits for an Event of the given type. When the GameState
    performs a matching Event, the GameState should `do` this effect afterward.
    """

    def __init__(self,  when: type[Action],
                        condition: Callable[[Event], bool],
                        action: Action,
                        uses_stack: bool = True):
        self.when = when
        self.condition = condition
        self.action = action
        self.uses_stack = uses_stack

    def matches(self, event: Event) -> bool:
        return isinstance(event.action, self.when) and self.condition(event)

    def do(self, game_state: GameState, event):
        if self.uses_stack:
            game_state.stack(StackAbility(game_state, self.action))
        else:
            self.action.perform(game_state)


class ActiveEffect(GameObject):
    """
    An active StaticEffect or TriggeredEffect.

    There are two ways an ActiveEffect can be created:
    1) Cards with static abilities will create an ActiveEffect when they enter
        the zone where the static ability is active, and will delete them when
        they leave that zone. These ActiveEffects have duration=None.
    2) Some spells or activated abilities will create an ActiveEffect with a
        duration. For example, Giant Growth gives +3/+3 until end of turn. The
        GameState will delete these ActiveEffects when the duration ends.
    """
    def __init__(self,
                 game_state: GameState,
                 source: 'Card',
                 effect: StaticEffect | TriggeredEffect,
                 duration = None):
        super().__init__(game_state)
        self.source = source
        self.effect = effect
        self.duration = duration   # TODO: implement phases and durations

    def copy(self) -> 'ActiveEffect':
        return ActiveEffect(game_state=self.game_state,
                            source=self.source,
                            effect=self.effect,
                            duration=self.duration)

    @property
    def is_trigger(self) -> bool:
        return isinstance(self.effect, TriggeredEffect)

    @property
    def is_static(self) -> bool:
        return isinstance(self.effect, StaticEffect)


class StaticAbility:
    """
    Any ability which is automatically active when the card is in the
    appropriate zone.
    Includes triggered abilities: "When this creature enters, draw a card"
    is only checked when the creature is in play.
    """

    def __init__(self,
                 active_zone: zones.Zone,
                 source: 'Card',
                 effect: StaticEffect | TriggeredEffect):
        self.active_zone = active_zone
        self.source = source
        self.effect = effect
        self.active_uid = None
        self.on_move(source.game_state)

    def is_active(self, game_state) -> bool:
        card = game_state.get(self.source)
        return self.active_zone.contains(card)

    def on_move(self, game_state: GameState):
        card = game_state.get(self.source)
        was_active = self.active_uid is not None
        now_active = self.active_zone.contains(card)
        if now_active and not was_active:
            # Add ActiveEffect to the GameState
            active = ActiveEffect(game_state=game_state,
                                  source=card,
                                  effect=self.effect,
                                  duration=None)
            self.active_uid = active.uid
            game_state.active_effects.append(active)
        if was_active and not now_active:
            # Remove ActiveEffect from the GameState
            game_state.active_effects = [active for active in game_state.active_effects
                                         if active.uid != self.active_uid]
            del game_state.objects[self.active_uid]
            self.active_uid = None


class CardType(str, Enum):
    Land = "land"
    Creature = "creature"
    Instant = "instant"
    Sorcery = "sorcery"
    Artifact = "artifact"

SPELL_TYPES = {CardType.Instant, CardType.Sorcery}