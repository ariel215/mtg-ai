from dataclasses import dataclass, field
from typing import Protocol, List, Union, Iterable, Optional
from collections.abc import Callable
from collections import defaultdict
from enum import Enum
from mtg_ai.game import GameObject, GameState, ObjRef, Mana, Action, Choice, ChoiceSet, Event
from mtg_ai import zone
from itertools import product


class Draw(Action):
    def __init__(self, player):
        self.player = player

    def choices(self, game_state):
        player = getattr(self.player, 'get', None)
        player = player(game_state) if player is not None else self.player
        deck = game_state.in_zone(zone.Deck(owner=player))
        if not deck:
            return []
        return [{'card': deck.pop()}]

    def do(self, game_state,card):
        card = game_state.get(card)
        card.zone = zone.Hand(self.player)
        return Event(self,card,None)

class Play(Action):
    def __init__(self, card):
        self.card = card
    
    def choices(self, _gamestate):
        return [{}] # todo: does the card need to make choices as it enters?
    
    def do(self, game_state):
        card = game_state.get(self.card)
        card.zone = zone.Field(owner=card.zone.owner)
        return Event(action=self, source=card,cause=card)

class TapSymbol(Action):
    def __init__(self, target):
        """
        Tap a permanent using the tap symbol.
        Target: the permanent to be tapped
        """
        self.card = target
    
    def choices(self, gamestate):
        card = gamestate.get(self.card)
        return [] if card.tapped else [{}]

    def do(self, gamestate):
        gamestate.get(self.card).tapped = True
        return Event(self)

class AddMana(Action):
    def __init__(self,mana: Union[Mana,Callable[[GameState],Mana]]):
        self.mana = mana

    def choices(self, _gamestate) -> ChoiceSet:
        return [{}]

    def do(self, gamestate):
        if isinstance(self.mana, Mana):
           gamestate.mana_pool += self.mana
        else:
            mana = self.mana(gamestate)
            gamestate.mana_pool += mana


class ActivatedAbility(Action):
    def __init__(self, costs: List[Action], effects: List[Action],
                 uses_stack: bool = False):
        # todo: change default for activated abilities to use stack
        # once fully implemented
        self.costs = costs
        self.effects = effects
        self.uses_stack = uses_stack
        
    def choices(self, game_state: GameState):
        costs = product(*[cost.choices(game_state) for cost in self.costs])
        effects = product(*[effect.choices(game_state) for effect in self.effects])
        return [{'costs_choice': c, 'effects_choice': e} for (c,e) in product(costs, effects)]

    def do(self, game_state, costs_choice, effects_choice):
        for (cost, cc) in zip(self.costs, costs_choice):
            cost.do(game_state,**cc)
        if self.uses_stack: 
            new_ability = StackAbility(game_state=game_state,
                                   effects=self.effects,
                                   source=self,
                                   )
            game_state.stack(new_ability)
        else:
            for (effect, ec) in zip(self.effects, effects_choice):
                effect.do(game_state, **ec)
            return game_state

class Trigger:
    def __init__(self, condition, action):
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
        super().__init__(game_state)
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
        return self.effect.do(game_state,**choices)
        

class CastSpell(Action):
    def __init__(self,card):
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
        return Event(action=self,source=card,cause=card)
