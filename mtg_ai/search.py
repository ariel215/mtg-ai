from tqdm import trange
from collections.abc import Iterable
import collections
from dataclasses import dataclass
from typing import List, Optional
from typing import List, Any, Self
from mtg_ai import actions, decklist, getters, zones
from mtg_ai.game import GameState, Action

@dataclass(slots=True)
class HistoryNode:
    parent: Self | None
    game_state: GameState
    action: Action | None
    choice: Any | None


@dataclass
class SearchResult:
    final_state: Optional[GameState]
    remaining: List[GameState]
    final_state: HistoryNode | None
    remaining: Iterable[HistoryNode]
    n_iters: int


def staff_victory(game: GameState) -> bool:
    field = game.in_zone(zones.Field())
    staff = [card for card in field if card.name == "Staff of Domination"]
    if not staff:
        return False
    
    scalers = [card for card in field
        if card.name in ("Overgrown Battlement", "Axebane Guardian") ]
    if not scalers:
        return False
    
    if all(card in game.summoning_sick for card in scalers):
        return False
    
    walls = [card for card in field if 'wall' in card.subtypes]
    return len(walls) >= 5

def bfs(initial: GameState, condition, timeout=int(1e6)) -> SearchResult:
    end_turn = actions.EndTurn() + actions.Draw(getters.ActivePlayer())
    root = HistoryNode(None, initial,None, None)
    queue = collections.deque([root])
    seen = {initial}

    for i in trange(timeout):
        next_node  = queue.popleft()
        next_state: GameState = next_node.game_state
        possible = actions.possible_actions(next_state)
        if not possible:
            choice = end_turn.choices(next_state)[0]
            child: GameState = next_state.take_action(end_turn, end_turn.choices(next_state)[0])
            if child not in seen:
                new = HistoryNode(next_node, child, end_turn,choice)
                queue.append(new)
            seen.add(child)
        else:
            for action in possible:
                choices = action.choices(next_state)
                for choice in choices:
                    child = next_state.take_action(action, choice)
                    while child.in_zone(zones.Stack()):
                        child = child.resolve_stack() #todo: make this an Action
                    node = HistoryNode(next_node,child,action, choice)
                    if condition(child):
                        return SearchResult(node,queue,i)
                    elif child not in seen:
                        queue.append(node)
                    seen.add(child)
    else:
        return SearchResult(None, queue,i)
