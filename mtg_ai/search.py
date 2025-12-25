import math
import random
from tqdm import trange
from collections.abc import Iterable
import collections
from dataclasses import dataclass
from typing import List, Any, Self, Dict, Callable, Tuple, Optional
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
    final_state: HistoryNode | None
    remaining: Iterable[HistoryNode]
    n_iters: int


def staff_victory(game: GameState) -> bool:
    field = game.in_zone(zones.Field())
    staff = [card for card in field if card.attrs.name == "Staff of Domination"]
    if not staff:
        return False
    
    scalers = [card for card in field
        if card.attrs.name in ("Overgrown Battlement", "Axebane Guardian") ]
    if not scalers:
        return False
    
    if all(card in game.summoning_sick for card in scalers):
        return False
    
    walls = [card for card in field if 'wall' in card.attrs.subtypes]
    return len(walls) >= 5

END_TURN = actions.EndTurn() + actions.Draw(getters.ActivePlayer())
def advance(gs: GameState) -> GameState:
    possible = actions.possible_actions(gs)
    possible_choices = [(a,c) for a in possible for c in a.choices(gs) ]
    while len(possible_choices) == 1:
        gs = gs.take_action(possible_choices[0][0], possible_choices[0][1])
        possible = actions.possible_actions(gs)
        possible_choices = [(a,c) for a in possible for c in a.choices(gs) ]
    return gs

def bfs(initial: GameState, condition, timeout=int(1e6)) -> SearchResult:    
    root = HistoryNode(None, initial,None, None)
    queue = collections.deque([root])
    seen = {initial}
    action = None
    choice = None
    for i in trange(timeout):
        next_node  = queue.popleft()
        next_state = advance(next_node.game_state)
        if condition(next_state):
            node = HistoryNode(next_node,next_state,action,choice)
            return SearchResult(node,queue,i)
        possible = actions.possible_actions(next_state) or [END_TURN]
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

@dataclass(slots=True)
class MCTSInfo:
    value: float
    visits: int

class MCTSSearcher:
    def __init__(self, initial_state: GameState,statistics:Dict[GameState, MCTSInfo], condition: Callable[[GameState],bool],
        C: float, max_turns: int = 10, n_iters: int=1000):
        self.root = HistoryNode(None,
        initial_state,None,None)
        self.stats = statistics
        self.condition = condition
        self.C = C
        self.max_turns = max_turns
        self.n_iters = n_iters


    def expand(self, node: HistoryNode) -> List[HistoryNode]:
        """
        Produce a list of children of the current game state, labelled by the action taken 
        and the choices made for that action
        """
        state = node.game_state
        possible = actions.possible_actions(state) or [END_TURN]
        choices = [
            (action,choice) for action in possible for choice in action.choices(state)]
        children = [state.take_action(action,choice) for (action,choice) in choices]
        return [HistoryNode(node,child, action, choice)
            for (child,(action,choice)) in zip(children, choices)
        ]

    def score(self, node: HistoryNode):
        state = node.game_state
        
        info = self.stats.get(state)
        if info is None:
            return 0

        value = info.value / info.visits
        ucb = self.C * math.sqrt(self.stats[node.parent.game_state].visits / info.visits)
        return value + ucb

    def playout(self, state: HistoryNode, max_turns: int) -> float:
        current = state.game_state
        while current.turn_number < max_turns:
            if self.condition(current):
                return 1.0 / current.turn_number ** 2
            possible = actions.possible_actions(current) or [END_TURN]
            choices = [(action,choice) for action in possible for choice in action.choices(current)]
            (action,choice) = random.choice(choices)
            current = current.take_action(action, choice)
        # failed to find the desired game state soon enough; count this as a failure
        return 0

    def backpropogate(self, state: HistoryNode, value: float):
        while state: 
            info = self.stats.get(state.game_state)
            if info is None:
                info = MCTSInfo(0,0)
            info.value += value
            info.visits += 1
            self.stats[state.game_state] = info
            state = state.parent

    def explore(self):
        current = self.root
        while not self.condition(current.game_state):
            if current.game_state.turn_number > self.max_turns:
                value = 0
                break
            children = self.expand(current)
            if all(child.game_state in self.stats for child in children):
                scores = [self.score(child) for child in children]
                def key(i_s):
                    return i_s[1]
                i,_ = max(enumerate(scores, ), key=key)
                current = children[i]
            else:
                remaining = [child for child in children if child.game_state not in self.stats]
                current = random.choice(remaining)
                value = self.playout(current,self.max_turns - current.game_state.turn_number)
                break
        else:
            value = 1.0 / current.game_state.turn_number
        self.backpropogate(current, value)

    def choose(self) -> GameState:
        """
        Choose the best move to take from self.root.

        Explores the game tree starting at :self.root: for :self.n_iters:
        simulations, then selects the child of :self.root: that has been 
        visited the most times
        """
        children = self.expand(self.root)
        for _ in range(max(self.n_iters, len(children))):
            self.explore()
        assert all(child.game_state in self.stats for child in children)
        nvisits = [(child.game_state, self.stats[child.game_state].visits) for child in children]
        return max(nvisits, key=lambda p: p[1])[0]
