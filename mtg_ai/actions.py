from typing import List, Callable, TYPE_CHECKING
from mtg_ai.game import GameState, Action, ChoiceSet, Event, StackAbility, CardType, StaticEffect, \
    GameObject
from mtg_ai import zones
from mtg_ai.mana import Mana
from itertools import product
from mtg_ai.getters import Get

if TYPE_CHECKING:
    from cards import Card


def possible_actions(game_state: GameState) -> List[Action]:
    player = game_state.players[game_state.active_player]
    hand = game_state.in_zone(zones.Hand(player))
    field = game_state.in_zone(zones.Field(player))
    field_abilities = [ability for card in field for ability in card.abilities.activated]
    return list(
        filter(
            lambda action: len(action.choices(game_state)) > 0, 
            [PlayLand(card) if CardType.Land in card.types else CastSpell(card) for card in hand ] + field_abilities
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
        
        card = deck.pop()
        card.zone = zones.Hand(owner=player)
        return Event(self,game_state,card,None)

class Play(Action):
    def __init__(self, card=None):
        super().__init__()
        if card: 
            self.params['card'] = card
    
    def choices(self, _game_state):
        return [{'card': self.card}] # todo: does the card need to make choices as it enters?
    
    def do(self, game_state: GameState, card):
        card = game_state.get(card)
        card.zone = zones.Field(owner=card.zone.owner)
        if CardType.Creature in card.types:
            game_state.summoning_sick.add(card)
        return Event(self, game_state, source=card,cause=card)
    
class MoveTo(Action):
    zone = Get()
    def __init__(self, zone):
        super().__init__()
        self.zone = zone

    def choices(self, _game_state):
        return [{}]

    def do(self, game_state,card):
        zone = self.zone(game_state)
        if zone.position == zones.TOP:
            top = max(
                card.zone.position
                for card in game_state.objects.values()
                if hasattr(card,'zone')
            )
            zone.position = top + 1
        elif zone.position == zones.BOTTOM:
            in_zone = game_state.in_zone(type(zone)(zone.owner))
            bottom = in_zone[0].zone.position
            zone.position = bottom
            for card in in_zone:
                card.zone.position += 1

        else:
            # position should not matter in this case
            assert zone.position is None
            
        card = game_state.get(card)
        card.zone = zone

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
        return [{'card': c} for c in game_state.objects.values() if self.condition(c)
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
        costs = self.cost.choices(game_state)
        effects = self.effect.choices(game_state)
        return [{'costs_choice': c, 'effects_choice': e} for (c,e) in product(costs, effects)]

    def do(self, game_state: GameState, costs_choice, effects_choice):
        game_state = game_state.take_action(self.cost, costs_choice)
        if self.uses_stack: 
            new_ability = StackAbility(game_state=game_state,
                                   effects=self.effect,
                                   source=self,
                                   )
            game_state.stack(new_ability)
        else:
            game_state = game_state.take_action(self.effect, effects_choice)
        return Event(self, game_state)


class CastSpell(Action):
    def __init__(self,card):
        super().__init__()
        self.card = card

    def choices(self, game_state: GameState):
        card = game_state.get(self.card)
        card_zone = card.zone
        if not isinstance(card_zone, zones.Hand):
            return []

        if game_state.mana_pool.can_pay(card.cost):
            # todo: compute all the ways to pay given the mana available?
            return [{'mana': card.cost}]
        else:
            return []

    def do(self, game_state: GameState, mana: Mana):
        card = game_state.get(self.card)
        game_state.mana_pool -= mana
        game_state.stack(card)
        return Event(self,game_state,source=card,cause=card)

class PlayLand(Action):
    def __init__(self, card):
        super().__init__()
        self.card = card
    
    def choices(self, game_state):
        card = game_state.get(self.card)
        if not zones.Hand().contains(card):
            return []
        if game_state.land_drops == 0:
            return []
        else: 
            return [{}]
    
    def do(self, game_state):
        game_state.land_drops -= 1
        game_state = game_state.take_action(Play(self.card), {})
        return Event(self, game_state)

class Search(Action):
    search_in = Get()
    search_for = Get()

    def __init__(self, search_in, search_for, to_found, to_rest):
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



class EndTurn(Action):
    def __init__(self):
        super().__init__()

    def choices(self, _game_state):
        return [{}]
    
    def do(self,game_state: GameState):
        game_state.mana_pool = Mana()
        for card in game_state.in_zone(zones.Field()):
            card.tapped = False
        game_state.summoning_sick.clear()
        game_state.turn_number += 1
        game_state.land_drops = 1
        game_state.active_player += 1
        game_state.active_player %= len(game_state.players)
        
