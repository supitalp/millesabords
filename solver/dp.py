"""
Exact DP solver via value iteration, parameterised by TurnConfig.

States can self-loop (keep 2 dice, reroll 6, happen to get the same 6 back
with 0 new skulls), so top-down memoised recursion diverges. Value iteration
converges because P(gaining ≥1 skull) > 0 on any non-zero reroll, making the
Bellman operator a contraction at each skull-count level.

Optimisation: transitions are precomputed once as numpy arrays, so each
iteration is a batch of dot products rather than 7M Python ops.

Solutions are cached per TurnConfig so each distinct card situation is solved once.
"""

from itertools import combinations_with_replacement
from dataclasses import dataclass
import numpy as np

from .model import State, NUM_FACES, Face, TurnConfig, DEFAULT_CONFIG
from .scoring import score
from .actions import valid_actions
from .roll import roll_outcomes

_cache: dict[TurnConfig, "Solution"] = {}


def _add_outcome(kept: tuple, outcome: tuple) -> tuple:
    """Merge kept non-skull dice with newly rolled non-skull outcomes."""
    result = list(kept)
    for face in range(1, NUM_FACES):
        result[face] += outcome[face]
    return tuple(result)


def _all_states(config: TurnConfig) -> list[State]:
    """All valid game states for this config: n_skulls + sum(held) == config.total_dice."""
    states = []
    for n_skulls in range(3):
        n_held = config.total_dice - n_skulls
        if n_held < 0:
            continue
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
    next_idxs: np.ndarray   # shape (k,)
    next_probs: np.ndarray  # shape (k,)


@dataclass
class Solution:
    config: TurnConfig
    states: list[State]
    state_to_idx: dict
    stop_values: np.ndarray  # shape (n_states,)
    V: np.ndarray            # shape (n_states,) — optimal expected score (WIN_SCORE for win states)
    V_normal: np.ndarray     # shape (n_states,) — expected normal points (win → 0, not WIN_SCORE)
    max_score: np.ndarray    # shape (n_states,) — best achievable score (best-case dice)
    actions: list[_Action]


def _precompute(states: list[State], state_to_idx: dict, config: TurnConfig) -> list[_Action]:
    """Build sparse transition arrays for every (state, reroll-action) pair."""
    result = []
    for i, s in enumerate(states):
        for kept in valid_actions(s, config):
            n_reroll = config.total_dice - s.n_skulls - sum(kept)
            if n_reroll == 0:
                continue
            acc: dict[int, float] = {}
            for outcome, prob in roll_outcomes(n_reroll):
                new_skulls = s.n_skulls + outcome[Face.SKULL]
                if new_skulls >= 3:
                    continue
                new_held = _add_outcome(kept, outcome)
                j = state_to_idx[State(new_skulls, new_held)]
                acc[j] = acc.get(j, 0.0) + prob
            if acc:
                idxs = np.array(list(acc.keys()), dtype=np.int32)
                probs = np.array(list(acc.values()), dtype=np.float64)
                result.append(_Action(i, idxs, probs))
    return result


def _solve(config: TurnConfig) -> Solution:
    states = _all_states(config)
    state_to_idx = {s: i for i, s in enumerate(states)}
    stop_values = np.array([score(s.n_skulls, s.held, config) for s in states], dtype=np.float64)

    actions = _precompute(states, state_to_idx, config)

    # Expected-value DP (value iteration)
    V = stop_values.copy()
    while True:
        V_new = stop_values.copy()
        for a in actions:
            ev = float(np.dot(a.next_probs, V[a.next_idxs]))
            if ev > V_new[a.state_idx]:
                V_new[a.state_idx] = ev
        if np.max(np.abs(V_new - V)) < 1e-9:
            break
        V = V_new

    # V_normal: expected points excluding instant-win (win states contribute 0)
    from .model import WIN_SCORE
    stop_values_normal = np.where(stop_values >= WIN_SCORE, 0.0, stop_values)
    V_normal = stop_values_normal.copy()
    while True:
        V_normal_new = stop_values_normal.copy()
        for a in actions:
            ev = float(np.dot(a.next_probs, V_normal[a.next_idxs]))
            if ev > V_normal_new[a.state_idx]:
                V_normal_new[a.state_idx] = ev
        if np.max(np.abs(V_normal_new - V_normal)) < 1e-9:
            break
        V_normal = V_normal_new

    # Max-score DP (best-case dice, optimal play)
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

    return Solution(config, states, state_to_idx, stop_values, V, V_normal, max_score, actions)


def get_solution(config: TurnConfig = DEFAULT_CONFIG) -> Solution:
    if config not in _cache:
        _cache[config] = _solve(config)
    return _cache[config]


def V(state: State, config: TurnConfig = DEFAULT_CONFIG) -> float:
    sol = get_solution(config)
    return float(sol.V[sol.state_to_idx[state]])
