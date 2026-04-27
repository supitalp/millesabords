"""
Exact DP solver via value iteration.

States can self-loop (keep 2 dice, reroll 6, happen to get the same 6 back
with 0 new skulls), so top-down memoised recursion diverges. Value iteration
converges because P(gaining ≥1 skull) > 0 on any non-zero reroll, making the
Bellman operator a contraction at each skull-count level.

Optimisation: transitions are precomputed once as numpy arrays, so each
iteration is a batch of dot products rather than 7M Python ops.
"""

from itertools import combinations_with_replacement
from dataclasses import dataclass
import numpy as np

from .model import State, NUM_DICE, NUM_FACES, Face
from .scoring import score
from .actions import valid_actions
from .roll import roll_outcomes

_solution: "Solution | None" = None


def _add_outcome(kept: tuple, outcome: tuple) -> tuple:
    result = list(kept)
    for face in range(1, NUM_FACES):
        result[face] += outcome[face]
    return tuple(result)


def _all_states() -> list[State]:
    """All valid game states satisfying n_skulls + sum(held) == NUM_DICE."""
    states = []
    for n_skulls in range(3):
        n_held = NUM_DICE - n_skulls
        for combo in combinations_with_replacement(range(1, NUM_FACES), n_held):
            counts = [0] * NUM_FACES
            for face in combo:
                counts[face] += 1
            states.append(State(n_skulls, tuple(counts)))
    return states


@dataclass
class _Action:
    """A single (state, kept) action with its precomputed sparse transition."""
    state_idx: int
    next_idxs: np.ndarray   # shape (k,) — indices of reachable next states
    next_probs: np.ndarray  # shape (k,) — corresponding probabilities (loss prob implicit)


@dataclass
class Solution:
    states: list[State]
    state_to_idx: dict
    stop_values: np.ndarray  # shape (n_states,)
    V: np.ndarray            # shape (n_states,) — optimal expected score
    max_score: np.ndarray    # shape (n_states,) — best achievable final score (best-case dice)
    actions: list[_Action]   # one per (state, non-stop action) pair


def _precompute(states: list[State], state_to_idx: dict) -> list[_Action]:
    """Build sparse transition arrays for every (state, reroll-action) pair."""
    result = []
    for i, s in enumerate(states):
        for kept in valid_actions(s):
            n_reroll = NUM_DICE - s.n_skulls - sum(kept)
            if n_reroll == 0:
                continue
            acc: dict[int, float] = {}
            for outcome, prob in roll_outcomes(n_reroll):
                new_skulls = s.n_skulls + outcome[Face.SKULL]
                if new_skulls >= 3:
                    continue  # loss: contributes 0 to EV, not stored
                new_held = _add_outcome(kept, outcome)
                j = state_to_idx[State(new_skulls, new_held)]
                acc[j] = acc.get(j, 0.0) + prob
            if acc:
                idxs = np.array(list(acc.keys()), dtype=np.int32)
                probs = np.array(list(acc.values()), dtype=np.float64)
                result.append(_Action(i, idxs, probs))
    return result


def _solve() -> Solution:
    states = _all_states()
    state_to_idx = {s: i for i, s in enumerate(states)}
    stop_values = np.array([score(s.n_skulls, s.held) for s in states], dtype=np.float64)

    actions = _precompute(states, state_to_idx)

    # Value iteration: start from stop values (lower bound on optimal V)
    V = stop_values.copy()
    while True:
        # For each action, compute EV = dot(next_probs, V[next_idxs])
        # Then update each state's value to max(stop, max EV over its actions)
        V_new = stop_values.copy()
        for a in actions:
            ev = float(np.dot(a.next_probs, V[a.next_idxs]))
            if ev > V_new[a.state_idx]:
                V_new[a.state_idx] = ev

        if np.max(np.abs(V_new - V)) < 1e-9:
            break
        V = V_new

    # Max-score DP: same structure as V but takes max over outcomes instead of expectation.
    # Tells us the best final score achievable with lucky dice and optimal play.
    max_score = stop_values.copy()
    while True:
        max_new = stop_values.copy()
        for a in actions:
            best_next = float(np.max(max_score[a.next_idxs]))
            if best_next > max_new[a.state_idx]:
                max_new[a.state_idx] = best_next
        if np.max(np.abs(max_new - max_score)) < 1e-9:
            break
        max_score = max_new

    return Solution(states, state_to_idx, stop_values, V, max_score, actions)


def get_solution() -> Solution:
    global _solution
    if _solution is None:
        _solution = _solve()
    return _solution


def V(state: State) -> float:
    sol = get_solution()
    return float(sol.V[sol.state_to_idx[state]])
