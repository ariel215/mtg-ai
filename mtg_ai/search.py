import collections
from dataclasses import dataclass
from typing import List
from mtg_ai import actions, decklist, getters, zones
from mtg_ai.game import GameState

@dataclass
class SearchResult:
    final_state: GameState
    remaining: List[GameState]
    n_iters: int

def staff_victory(game: GameState) -> bool:
    field = game.in_zone(zones.Field())
    staff = [card for card in field if isinstance(card, decklist.Staff)]
    if not staff: 
        return False
    
    scalers = [card for card in field if isinstance(card, (decklist.Battlement, decklist.Axebane))]
    if not scalers:
        return False
    
    if all(card in game.summoning_sick for card in scalers):
        return False
    
    walls = [card for card in field if 'wall' in card.subtypes]
    return len(walls) >= 5

def bfs(initial: GameState, condition, timeout=int(1e6)) -> SearchResult:
    end_turn = actions.EndTurn() + actions.Draw(getters.ActivePlayer())
    queue = collections.deque()
    seen = {initial}
    queue.append(initial)
    for i in range(timeout):
        next_state : GameState = queue.popleft()
        possible = actions.possible_actions(next_state)
        if not possible:
            child = next_state.take_action(end_turn, end_turn.choices(next_state)[0])
            if child not in seen:
                queue.append(child)
            seen.add(child)
        else:
            for action in possible:
                choices = action.choices(next_state)
                for choice in choices:
                    child = next_state.take_action(action, choice)
                    while child.in_zone(zones.Stack()):
                        child = child.resolve_stack() #todo: make this an Action
                    if condition(child):
                        return SearchResult(child,queue,i)
                    elif child not in seen:
                        queue.append(child)
                    seen.add(child)
        if i % 100 == 0:
            pass 
    else:
        return (None, queue,i)
