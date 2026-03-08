from mtg_ai.actions import Search
import math
import random
from tqdm import trange
from collections.abc import Iterable
import collections
from dataclasses import dataclass,field
from typing import List, Any, Self, Dict, Callable, Tuple, Optional, TypeVar
from mtg_ai import actions, decklist, getters, zones
from mtg_ai.game import GameState, Action
import logging

logger = logging.getLogger(__name__, )

@dataclass(slots=True)
class MCTSInfo:
    value: float = 0
    visits: int = 0


@dataclass(slots=True)
class HistoryNode:
    game_state: GameState
    parent: Optional['HistoryNode'] = None
    action: Action | None = None
    choice: Any | None = None
    stats: MCTSInfo | None = None

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
    root = HistoryNode(initial)
    queue = collections.deque([root])
    seen = {initial}
    action = None
    choice = None
    for i in range(timeout):
        next_node  = queue.popleft()
        next_state = advance(next_node.game_state)
        if condition(next_state):
            node = HistoryNode(next_state,next_node,action,choice)
            return SearchResult(node,queue,i)
        possible = actions.possible_actions(next_state) or [END_TURN]
        for action in possible:
            choices = action.choices(next_state)
            for choice in choices:
                child = next_state.take_action(action, choice)
                node = HistoryNode(child,next_node,action, choice)
                if condition(child):
                    return SearchResult(node,queue,i)
                elif child not in seen:
                    queue.append(node)
                seen.add(child)
    else:
        return SearchResult(None, queue,i)


class MCTSSearcher:
    def __init__(self, initial_state: GameState,statistics:Dict[GameState, MCTSInfo], condition: Callable[[GameState],bool],
        C: float, max_turns: int = 10, n_iters: int=1000):
        self.root = HistoryNode(initial_state)
        self.stats = statistics
        self.condition = condition
        self.C = C
        self.max_turns = max_turns
        self.n_iters = n_iters


    def expand(self, node: HistoryNode) -> List[HistoryNode]:
        """
        Produce a list of children of the current game state, labelled by the action taken 
        and the choices made for that action. 
        """
        state = node.game_state
        possible = actions.possible_actions(state) or [END_TURN]
        choices = [
            (action,choice) for action in possible for choice in action.choices(state)]
        children = [state.take_action(action,choice) for (action,choice) in choices]
        return [HistoryNode(child,node, action, choice)
            for (child,(action,choice)) in zip(children, choices)
        ]

    def score(self, node: HistoryNode) -> float:
        info = node.stats
        if info is None:
            return 0

        value = info.value / info.visits
        ucb = self.C * math.sqrt(node.parent.stats.visits / info.visits)
        return value + ucb

    def playout(self, state: HistoryNode, max_turns: int) -> float:
        logger.debug("Random playout")
        current = state.game_state
        while current.turn_number < max_turns:
            if self.condition(current):
                logger.debug(f"Found victory by turn {current.turn_number}")
                return 1.0 / current.turn_number ** 2
            possible = actions.possible_actions(current) or [END_TURN]
            choices = [(action,choice) for action in possible for choice in action.choices(current)]
            (action,choice) = random.choice(choices)
            logger.debug(f"Taking {action} with choices {str(choices)}")
            current = current.take_action(action, choice).resolve_stack()
        # failed to find the desired game state soon enough; count this as a failure
        logger.debug(f"failed to find victory before turn {max_turns}")
        return 0

    def backpropogate(self, state: HistoryNode | None, value: float):
        while state:
            if state.stats is None:
                state.stats = MCTSInfo()
            info = state.stats
            info.value += value
            info.visits += 1
            state = state.parent

    def explore_node(self, node: HistoryNode):
        current = node
        while not self.condition(current.game_state):
            if current.game_state.turn_number > self.max_turns:
                value = 0
                break
            children = self.expand(current)
            unexplored = [child for child in children if child.stats is not None]
            if unexplored:
                current = random.choice(children)
                value = self.playout(current,self.max_turns - current.game_state.turn_number)
                break
            else:
                scores = [self.score(child) for child in children]
                def key(i_s):
                    return i_s[1]
                i,_ = max(enumerate(scores, ), key=key)
                current = children[i]
        else:
            value = 1.0 / current.game_state.turn_number
        self.backpropogate(current, value)
        assert current.stats is not None
        assert node.stats is not None

    def explore(self) -> List[HistoryNode]:
        """
        Run an iteration of MCTS to compute the best next move.
        """
        children = self.expand(self.root)

        for i,child in enumerate(children):
            updated = self.explore_node(child)
        assert all(child.stats is not None for child in children)

        def key(i_s):
            return i_s[1]

        for _ in range(self.n_iters):
            scores = [self.score(child) for child in children]
            i,_ = max(enumerate(scores, ), key=key)
            self.explore_node(children[i])

        assert all(child.stats is not None for child in children)
        return children


    def choose(self) -> HistoryNode:
        """
        Choose the best move to take from self.root.

        Explores the game tree starting at :self.root: for :self.n_iters:
        simulations, then selects the child of :self.root: that has been 
        visited the most times. Exception: we always prefer not ending the turn
        to ending the turn.
        """
        children = self.expand(self.root)
        logger.debug("children: %s", children)
        if len(children) == 1:
            return children[0]
        new_children = self.explore()
        assert len(children) == len(new_children)
        nvisits = [(child,child.stats.visits) for child in new_children]
        if len(nvisits) > 1:
            nvisits = [pair for pair in nvisits if pair[0].game_state is not END_TURN]
        return max(nvisits, key=lambda p: p[1])[0]

