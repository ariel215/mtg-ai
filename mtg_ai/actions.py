from dataclasses import dataclass, field
from typing import Protocol, List, Union, Iterable, Optional
from collections.abc import Callable
from collections import defaultdict
from enum import Enum
from mtg_ai.game import GameObject, GameState, Mana, Action, Choice, ChoiceSet, Event
from mtg_ai import zone, getters
from mtg_ai.mana import Mana
from itertools import product


class ActionProp:
    """
    Adapter to let us assign either getters or values 
    to a property
    """
        
    def __set_name__(self, owner, name):
        self.private_name = f"_{name}"
        self.public_name =name

    def __set__(self, owner, value):
        if callable(value):
            setattr(owner, self.private_name, value)
        else:
            def default(*args):
                return value
            setattr(owner, self.private_name, default)
        
    def __get__(self,owner, _objname):
        return getattr(owner, self.private_name)


class Draw(Action):
    
    player = ActionProp()

    def __init__(self, player):
        super().__init__()
        self.player = player

    def choices(self, game_state: GameState):
        player = self.player(game_state)
        if player is None:
            return [{'player': p} for p in game_state.players]
        else:
            return [{'player': player}]

    def do(self, game_state, player):
        deck = game_state.in_zone(zone.Deck(owner=player))
        if not deck:
            return None # todo: game loss
        
        card = deck.pop()
        card.zone = zone.Hand(owner=player)
        return Event(self,game_state,card,None)

class Play(Action):
    def __init__(self, card):
        super().__init__()
        self.card = card
    
    def choices(self, _game_state):
        return [{}] # todo: does the card need to make choices as it enters?
    
    def do(self, game_state):
        card = game_state.get(self.card)
        card.zone = zone.Field(owner=card.zone.owner)
        return Event(self, game_state, source=card,cause=card)

class TapSymbol(Action):
    def __init__(self, target):
        super().__init__()
        """
        Tap a permanent using the tap symbol.
        Target: the permanent to be tapped
        """
        self.card = target
    
    def choices(self, game_state):
        card = game_state.get(self.card)
        return [] if card.tapped else [{}]

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

    mana=ActionProp()

    def __init__(self,mana):
        super().__init__()
        self.mana = mana

    def choices(self, _game_state) -> ChoiceSet:
        return [{}]

    def do(self, game_state):
        mana = self.mana(game_state)
        game_state.mana_pool += mana

class All(Action):
    def __init__(self, *actions):
        super().__init__()
        self.actions = actions

    def choices(self,game_state):
        subchoices = [action.choices(game_state) for action in self.actions]
        combinations = list(product(*subchoices))
        return [{'choices': option }
        for option in combinations]
    
    def do(self, game_state, choices):
        # todo: this isn't actually the right signature for Action.do()
        return [
            action.perform(game_state,**choice)
            for action, choice in zip(self.actions, choices)
        ]

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

    def do(self, game_state, costs_choice, effects_choice):
        self.cost.perform(game_state,**costs_choice)
        if self.uses_stack: 
            new_ability = StackAbility(game_state=game_state,
                                   effects=self.effect,
                                   source=self,
                                   )
            game_state.stack(new_ability)
        else:
            self.effect.perform(game_state, **effects_choice)
            return game_state

class Trigger:
    def __init__(self, condition, action):
        super().__init__()
        self.condition = condition
        self.action = action

    def stack(self,game_state: GameState, event):
        return StackAbility(game_state, self.action)

class StackAbility(GameObject, Action):
    """
    An ability that is on the stack, waiting to resolve
    """

    def __init__(self,game_state: GameState,
                 effect: Action):
        self.zone = None
        GameObject.__init__(self,game_state)
        Action.__init__(self)
        game_state.stack(self)
        self.effect: Action = effect

    def copy(self):
        return StackAbility(
            game_state=self.game_state,
            effect=self.effect
        )
        
    def choices(self, game_state):
        # pinky promise to only try when it's on top of the stack
        return self.effect.choices(game_state) 

    def do(self,game_state, **choices):
        return self.effect.perform(game_state,**choices)
        

class CastSpell(Action):
    def __init__(self,card):
        super().__init__()
        self.card = card

    def choices(self, game_state: GameState):
        card = game_state.get(self.card)
        card_zone = card.zone
        if not isinstance(card_zone, zone.Hand):
            return []

        # if card_zone.owner != game_state.priority:
        #     return []

        if game_state.mana_pool.can_pay(card.cost):
            # todo: compute all the ways to pay given the mana available
            return [{'mana': card.cost}]
        else:
            return []

    def do(self, game_state: GameState, mana: Mana):
        card = game_state.get(self.card)
        game_state.mana_pool -= mana
        game_state.stack(card)
        return Event(self,game_state,source=card,cause=card)
