from typing import List, TYPE_CHECKING, Callable
from mtg_ai.game import GameState, Action, ChoiceSet, Event, StackAbility, CardType, StaticEffect, \
    GameObject
from mtg_ai import zones
from mtg_ai.mana import Mana
from itertools import product
import mtg_ai.getters as getters
from mtg_ai.getters import Get

if TYPE_CHECKING:
    from cards import Card


def possible_actions(game_state: GameState) -> List[Action]:
    """
    List the actions available to the player with priority
    in the current game state
    """
    player = game_state.players[game_state.active_player]
    if len(game_state.triggers) > 0:
        return [
            StackTriggers()
        ]
        
    hand = game_state.in_zone(zones.Hand(player))
    actions = [PlayLand(card) if CardType.Land in card.attrs.types else CastSpell(card) for card in hand ]
    field = game_state.in_zone(zones.Field(player))
    field_abilities = [ability for card in field for ability in card.attrs.activated]
    actions += field_abilities
    if len(game_state.in_zone(zones.Stack())) > 0:
        actions.append(ResolveStack())
    return list(
        filter(
            lambda action: len(action.get_choices(game_state)) > 0, 
             actions
        )
    )


class Draw(Action):
    """
    A player draws a card.
    If the player is not specified initially, either player can be chosen.
    """
    
    player = Get()

    def __init__(self, player=None):
        super().__init__()
        self.player = player

    def choices(self, game_state: GameState):
        player = self.player(game_state)
        if player is None:
            return [{'player': p} for p in game_state.players]
        else:
            return [{'player': player}]

    def do(self, game_state, player):
        deck = game_state.in_zone(zones.Deck(owner=player))
        if not deck:
            return None # todo: game loss

        card = game_state.get(deck.pop())
        card.zone = zones.Hand(owner=player)
        return Event(self,game_state,card,None)

class Play(Action):
    def __init__(self, card=None):
        super().__init__()
        if card: 
            self.params['card'] = card
    
    def choices(self, _game_state):
        return [{'card': self.params.get('card')}] # todo: does the card need to make choices as it enters?
    
    def do(self, game_state: GameState, card):
        card = game_state.get(card)
        card.zone = zones.Field(owner=card.zone.owner)
        if CardType.Creature in card.attrs.types:
            game_state.summoning_sick.add(card)
        return Event(self, game_state, source=card,cause=card)

class MoveTo(Action):
    zone = Get()
    card = Get()

    def __init__(self, zone, card=None):
        super().__init__()
        self.zone = zone
        self.card = card

    def choices(self, game_state):
        card = self.card(game_state)
        if card:
            return [{'card': self.card(game_state)}]
        else:
            return [{}]

    def do(self, game_state,card):
        zone = self.zone(game_state)
        if zone.position == zones.TOP:
            in_zone = game_state.in_zone(type(zone)(zone.owner))
            top = max(
                [c.zone.position for c in in_zone],
                default=0
            )
            position = top + 1
        elif zone.position == zones.BOTTOM:
            in_zone = game_state.in_zone(type(zone)(zone.owner))
            position = min([c.zone.position for c in in_zone if hasattr(c, "zone")], default=0)
            
            for other in in_zone:
                other = game_state.get(other)
                old_zone = other.zone
                other.zone = type(old_zone)(old_zone.owner, old_zone.position + 1)

        else:
            # position should not matter in this case
            assert zone.position is None
            position = zone.position
             
        card = game_state.get(card)
        card.zone = type(zone)(owner=zone.owner, position=position)


class Sacrifice(Action):
    def __init__(self, card):
        super().__init__()
        self.action = MoveTo(getters.Zone(zones.Grave(),getters.Controller(card)),
        lambda gs: gs.get(card))

    def choices(self,game_state):
        card = self.action.card(game_state)
        if card and zones.Field().contains(card):
            return self.action.choices(game_state)
        else:
            return []

    def do(self, game_state, card):
        gs = game_state.take_action(self.action,{'card': card})
        return Event(self, gs)


class TapSymbol(Action):
    def __init__(self, target):
        super().__init__()
        """
        Tap a permanent using the tap symbol.
        Target: the permanent to be tapped
        """
        self.card = target
    
    def choices(self, game_state: GameState):
        card = game_state.get(self.card)
        return [] if card.tapped or card in game_state.summoning_sick else [{}]

    def do(self, game_state):
        game_state.get(self.card).tapped = True
        return Event(self,game_state)

class Tap(Action):

    def __init__(self, condition):
        super().__init__()
        self.condition = condition

    def choices(self, game_state):
        return [{'card': c} for c in game_state.objects if self.condition(c)
            and not getattr(c,'tapped', True)
        ]

    def do(self, game_state,card):
        card = game_state.get(card)
        card.tapped = True


class AddMana(Action):

    mana=Get()

    def __init__(self,mana):
        super().__init__()
        self.mana = mana

    def choices(self, _game_state) -> ChoiceSet:
        return [{}]

    def do(self, game_state):
        mana = self.mana(game_state)
        game_state.mana_pool += mana


class ActivatedAbility(Action):
    def __init__(self, cost: Action, effect: Action,
                 uses_stack: bool = False):
        super().__init__()
        # todo: change default for activated abilities to use stack
        # once fully implemented
        self.cost = cost
        self.effect = effect
        self.uses_stack = uses_stack
        
    def choices(self, game_state: GameState):
        costs = self.cost.get_choices(game_state)
        effects = self.effect.get_choices(game_state)
        return [{'costs_choice': c, 'effects_choice': e} for (c,e) in product(costs, effects)]

    def do(self, game_state: GameState, costs_choice, effects_choice):
        game_state = game_state.take_action(self.cost, costs_choice)
        if self.uses_stack: 
            new_ability = StackAbility(game_state=game_state, effect=self.effect)
            game_state.stack(new_ability)
        else:
            game_state = game_state.take_action(self.effect, effects_choice)
        return Event(self, game_state)

    def __str__(self) -> str:
        return str(self.cost) + ": " + str(self.effect)

class Trigger:
    def __init__(self, condition, action, source, uses_stack=True):
        self.condition = condition
        self.action = action
        self.source = source
        self.uses_stack = uses_stack

    def do(self,game_state: GameState, event):
        if self.uses_stack:
            game_state.stack(StackAbility(game_state, self.action))
        else:
            self.action.perform(game_state)

class StackTriggers(Action):
    def __init__(self):
        super().__init__()
    
    def choices(self,game_state):
        return [{}]

    def do(self,game_state: GameState,**kwargs):
        game_state.stack_triggers()

class CastSpell(Action):
    def __init__(self,card):
        super().__init__()
        self.card = card


    def choices(self, game_state: GameState):
        card = game_state.get(self.card)
        card_zone = card.zone
        if not isinstance(card_zone, zones.Hand):
            return []

        if CardType.Instant not in card.attrs.types and len(game_state.in_zone(zones.Stack())) > 0:
            return []

        if game_state.mana_pool.can_pay(card.attrs.cost):
            # todo: compute all the ways to pay given the mana available?
            mana_choices = {'mana': card.attrs.cost}
            effect_choices = card.effect.get_choices(game_state)
            return [mana_choices | {"effect_choices":ch} for ch in effect_choices]
        else:
            return []

    def do(self, game_state: GameState, mana: Mana, effect_choices=None):
        effect_choices = effect_choices or {}
        card = game_state.get(self.card)
        game_state.mana_pool -= mana
        game_state.stack(card)
        card.effect.set_targets(game_state, **effect_choices)
        return Event(self,game_state,source=card,cause=card)

class PlayLand(Action):
    def __init__(self, card):
        super().__init__()
        self.card = card
    
    def choices(self, game_state):
        card = game_state.get(self.card)
        if not zones.Hand().contains(card):
            return []
        if game_state.land_drops <= 0:
            return []
        else: 
            return [{}]
    
    def do(self, game_state):
        game_state = game_state.take_action(Play(self.card), {})
        game_state.land_drops -= 1
        return Event(self, game_state)

class Search(Action):
    search_in = Get()
    search_for = Get()

    def __init__(self, search_in, search_for, to_found: Action, to_rest: Action):
        """
        Parameters
        ---------
        search_in: a getter that returns a list of cards
        search_for: a function that takes a list of cards and filters is
        to_found: the action to be performed to each card that is chosen
        to_rest: the action to be performed to each card that is not chosen
        """
        super().__init__()
        self.search_in = search_in
        self.search_for = search_for
        self.to_found = to_found
        self.to_rest = to_rest

    def choices(self, game_state):
        available = self.search_in(game_state)
        choices = self.search_for(available)
        available = set(available)
        options = [{'found': c, 'rest': available.difference(c)} for c in choices]
        return options 
    
    def do(self, game_state: GameState, found, rest):
        for card in found:
            game_state = game_state.take_action(self.to_found, {'card': card})
        for card in rest:
            game_state = game_state.take_action(self.to_rest, {'card': card})
        return Event(self, game_state)

class Shuffle(Action):
    def choices(self,game_state):
        return [{}]

    def do(self, game_state,**kwargs): # this is a terrible hack
        return Event(self, game_state)

class PayMana(Action):
    mana = Get()
    def __init__(self, mana=None):
        super().__init__()
        self.mana = mana

    def choices(self, game_state: GameState):
        mana = self.mana(game_state)
        if game_state.mana_pool.can_pay(mana): 
            return [{'mana': self.mana(game_state)}]
        else:
            return []
        
    def do(self, game_state: GameState, mana: Mana):
        game_state.mana_pool -= mana

class AddCounter(Action):

    def __init__(self, card, counter, zone=zones.Any()):
        super().__init__()
        self.counter = counter
        self.card = card
        self.zone = zone

    def choices(self,game_state):
        if self.zone.contains(game_state.get(self.card)):
            return [{}]
        else:
            return []
    
    def do(self,game_state):
        card = game_state.get(self.card)
        card.counters[self.counter] += 1

class ResolveStack(Action):
    def __init__(self):
        super().__init__()

    def choices(self,game_state:GameState):
        stack = game_state.in_zone(zones.Stack())
        top = stack[-1]
        return top.effect.get_choices(game_state)

    def do(self, game_state, **kwargs):
        stack = game_state.in_zone(zones.Stack())
        top = stack[-1]
        return top.effect.perform(game_state, **kwargs) 


class EndTurn(Action):
    def __init__(self):
        super().__init__()

    def choices(self, _game_state):
        return [{}]
    
    def do(self,game_state: GameState):
        game_state.mana_pool = Mana()
        for card in game_state.in_zone(zones.Field()):
            game_state.get(card).tapped = False
        game_state.summoning_sick.clear()
        game_state.turn_number += 1
        game_state.land_drops = 1
        game_state.active_player += 1
        game_state.active_player %= len(game_state.players)


class Target(Action, GameObject):
    """
    Target is an Action, a GameObject, and a Getter.
    Action:     Call do() to lock in the choice of target and raises an Event.
    GameObject: The "same" Target can be set to different values in different GameStates.
    Getter:     call the Target to retrieve the chosen value
    """
    def __init__(self,
                 game_state: GameState,
                 criteria: GameObject | Callable[[GameObject], bool],
                 search_zone: zones.Zone):
        GameObject.__init__(self, game_state)
        Action.__init__(self)
        self.criteria = criteria
        self.search_zone = search_zone

    def __call__(self, game_state: GameState):
        obj = game_state.get(self)
        return obj.params["target"]

    def choices(self, game_state):
        valid_targets = filter(self.criteria, game_state.in_zone(self.search_zone))
        return [{"target":obj} for obj in valid_targets]

    def do(self, game_state: GameState, target):
        self.set(target)
        return Event(self, game_state)

    def set(self, target: GameObject):
        self.bind(target=target)

    def unset(self):
        self.params.pop("target", None)

    @property
    def is_set(self) -> bool:
        return "target" in self.params

    def copy(self, game_state: GameState):
        target = Target(game_state=game_state,
                        criteria=self.criteria,
                        search_zone=self.search_zone)
        target.params = self.params.copy()
        return target
