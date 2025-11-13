from dataclasses import dataclass, field
from typing import Protocol, List, Union, Iterable, Optional
from collections.abc import Callable
from collections import defaultdict
from enum import Enum
from mtg_ai.game import GameObject, GameState, Zone, ObjRef, Mana, Action, Choice, ChoiceSet, Hand
from itertools import product


class TapSymbol:
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


class AddMana:
    def __init__(self,mana: Union[Mana,Callable[['GameState'],Mana]]):
        self.mana = mana

    def choices(self, _gamestate) -> ChoiceSet:
        return [{}]

    def do(self, gamestate):
        if isinstance(self.mana, Mana):
           gamestate.mana_pool += self.mana
        else:
            mana = self.mana(gamestate)
            gamestate.mana_pool += mana


class ActivatedAbility:
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

class StackAbility(GameObject):
    def __init__(self,game_state: GameState,
                 source,
                 effects: List[Action]):
        self.zone = None 
        super().__init__(game_state)
        game_state.stack(self)
        self.source = source
        self.effects = effects

    def copy(self):
        return StackAbility(
            game_state=self.game_state,
            source = self.source,
            effects = self.effects
        )
        
    def choices(self, game_state):
        # pinky promise to only try when it's on top of the stack
        return product(effect.choices(game_state) for effect in self.effects)
        
    def do(self,game_state, choices):
        for (choice,effect) in  zip(choices, self.effects):
            effect.do(game_state,**choice)
        return game_state


class CastSpell:
    def __init__(self,card):
        self.card = card

    def choices(self, game_state: GameState):
        card = game_state.get(self.card)
        card_zone = card.zone
        if not isinstance(card_zone, Hand):
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
        return game_state
