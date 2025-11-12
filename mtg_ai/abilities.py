from dataclasses import dataclass, field
from typing import Protocol, List, Union, Iterable, Optional
from collections.abc import Callable
from collections import defaultdict
from enum import Enum
from mtg_ai.game import GameObject, GameState, Zone, ObjRef, Mana, Action



class TapSymbol:
    def __init__(self, target):
        """
        Tap a permanent using the tap symbol.
        Target: the permanent to be tapped
        """
        self.card = target
    
    def can(self, gamestate):
        card = gamestate.get(self.card)
        return not card.tapped

    def do(self, gamestate):
        gamestate.get(self.card).tapped = True


class AddMana:
    def __init__(self,mana: Union[Mana,Callable[['GameState'],Mana]]):
        self.mana = mana

    def can(self, _gamestate):
        return True

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
        
    def can(self, game_state: GameState):
        return all(cost.can(game_state) for cost in self.costs)

    def do(self, game_state):
        for cost in self.costs:
            cost.do(game_state)
        if self.uses_stack: 
            new_ability = StackAbility(game_state=game_state,
                                   effects=self.effects,
                                   source=self,
                                   )
            game_state.stack(new_ability)
        for effect in self.effects:
            effect.do(game_state)
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
        
    def can(self, game_state):
        # pinky promise to only try when it's on top of the stack
        return True
        
    def do(self,game_state):
        for effect in  self.effects:
            effect.do(game_state)
        return game_state


class CastSpell:
    def __init__(self,card):
        self.card = card

    def can(self, game_state: GameState):
        card = game_state.get(self.card)
        card_zone = card.zone
        if not isinstance(card_zone, Hand):
            return False

        if card_zone.owner != game_state.priority:
            return False

        return card.cost <= game_state.mana_pool

    def do(self, game_state: GameState):
        card = game_state.get(self.card)
        game_state.mana_pool -= card.cost
        game_state.stack(card)
        return game_state
