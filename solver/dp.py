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
from pathlib import Path
import numpy as np

from .model import State, NUM_FACES, Face, TurnConfig, DEFAULT_CONFIG
from .scoring import score
from .actions import valid_actions, guardian_kept_options
from .roll import roll_outcomes

_cache: dict[TurnConfig, "Solution"] = {}

_DISK_CACHE_DIR = Path(__file__).parent / ".dp_cache"


def _config_key(config: TurnConfig) -> str:
    held = "".join(str(x) for x in config.initial_held)
    return (f"d{config.total_dice}_sk{config.initial_n_skulls}_h{held}"
            f"_ma{int(config.merge_animals)}_sm{config.score_multiplier}"
            f"_rs{config.required_swords}_sb{config.sword_bonus}_sp{config.sword_penalty}"
            f"_sr{int(config.skull_reroll_available)}_ti{int(config.treasure_island)}"
            f"_fsp{config.forbidden_sword_penalty}")


def _add_outcome(kept: tuple, outcome: tuple) -> tuple:
    """Merge kept non-skull dice with newly rolled non-skull outcomes."""
    result = list(kept)
    for face in range(1, NUM_FACES):
        result[face] += outcome[face]
    return tuple(result)


def _all_states(config: TurnConfig) -> list[State]:
    """All valid game states for this config: n_skulls + sum(held) == config.total_dice."""
    states = []
    skull_reroll_variants = [False, True] if config.skull_reroll_available else [False]
    for n_skulls in range(3):
        n_held = config.total_dice - n_skulls
        if n_held < 0:
            continue
        for combo in combinations_with_replacement(range(1, NUM_FACES), n_held):
            counts = [0] * NUM_FACES
            for face in combo:
                counts[face] += 1
            for used in skull_reroll_variants:
                states.append(State(n_skulls, tuple(counts), used))
    return states


@dataclass
class _Action:
    """A single (state, kept) action with its precomputed sparse transition."""
    state_idx: int
    next_idxs: np.ndarray   # shape (k,)
    next_probs: np.ndarray  # shape (k,)
    bust_ev: float = 0.0    # expected value contribution from skull-bust outcomes
    bust_max: float = 0.0   # best-case score from skull-bust outcomes (for max_score DP)


@dataclass
class Solution:
    config: TurnConfig
    states: list[State]
    state_to_idx: dict
    stop_values: np.ndarray  # shape (n_states,)
    V: np.ndarray            # shape (n_states,) — optimal expected score under optimal play
    max_score: np.ndarray    # shape (n_states,) — best achievable score (best-case dice)
    actions: list[_Action]


def _bust_score(new_skulls: int, new_held: tuple, config: TurnConfig) -> float:
    """
    EV contribution from a bust outcome.
    For most cards this is a constant (0 or -sword_penalty).
    For Treasure Island the bust score depends on which dice were held at bust time.
    """
    return float(score(new_skulls, new_held, config))


def _precompute(states: list[State], state_to_idx: dict, config: TurnConfig) -> list[_Action]:
    """Build sparse transition arrays for every (state, reroll-action) pair."""
    result = []
    for i, s in enumerate(states):
        # Normal reroll actions
        for kept in valid_actions(s, config):
            n_reroll = config.total_dice - s.n_skulls - sum(kept)
            if n_reroll == 0:
                continue
            acc: dict[int, float] = {}
            bust_ev = 0.0
            bust_max = float("-inf")
            for outcome, prob in roll_outcomes(n_reroll):
                new_skulls = s.n_skulls + outcome[Face.SKULL]
                if new_skulls >= 3:
                    new_held = _add_outcome(kept, outcome)
                    # TI bust score: only island (kept) dice count, not the rerolled dice
                    # that happened to land non-skull before the bust was triggered.
                    bust_held = kept if config.treasure_island else new_held
                    if config.skull_reroll_available and not s.skull_reroll_used and new_skulls == 3:
                        for rescue_outcome, rescue_prob in roll_outcomes(1):
                            if rescue_outcome[Face.SKULL] > 0:
                                bs = _bust_score(new_skulls, bust_held, config)
                                bust_ev += prob * rescue_prob * bs
                                bust_max = max(bust_max, bs)
                            else:
                                rescue_held = _add_outcome(new_held, rescue_outcome)
                                j = state_to_idx[State(2, rescue_held, True)]
                                acc[j] = acc.get(j, 0.0) + prob * rescue_prob
                    else:
                        bs = _bust_score(new_skulls, bust_held, config)
                        bust_ev += prob * bs
                        bust_max = max(bust_max, bs)
                    continue
                new_held = _add_outcome(kept, outcome)
                j = state_to_idx[State(new_skulls, new_held, s.skull_reroll_used)]
                acc[j] = acc.get(j, 0.0) + prob
            if acc:
                idxs = np.array(list(acc.keys()), dtype=np.int32)
                probs = np.array(list(acc.values()), dtype=np.float64)
                bmax = bust_max if bust_max > float("-inf") else 0.0
                result.append(_Action(i, idxs, probs, bust_ev, bmax))

        # Guardian actions: free 1 skull die into the reroll pool (one-time ability)
        if config.skull_reroll_available and not s.skull_reroll_used and s.n_skulls >= 1:
            for kept in guardian_kept_options(s):
                n_reroll = (sum(s.held) - sum(kept)) + 1  # +1 for the freed skull
                acc: dict[int, float] = {}
                bust_ev = 0.0
                bust_max = float("-inf")
                for outcome, prob in roll_outcomes(n_reroll):
                    new_skulls = (s.n_skulls - 1) + outcome[Face.SKULL]
                    if new_skulls >= 3:
                        new_held = _add_outcome(kept, outcome)
                        bust_held = kept if config.treasure_island else new_held
                        bs = _bust_score(new_skulls, bust_held, config)
                        bust_ev += prob * bs
                        bust_max = max(bust_max, bs)
                        continue
                    new_held = _add_outcome(kept, outcome)
                    j = state_to_idx[State(new_skulls, new_held, True)]
                    acc[j] = acc.get(j, 0.0) + prob
                if acc:
                    idxs = np.array(list(acc.keys()), dtype=np.int32)
                    probs = np.array(list(acc.values()), dtype=np.float64)
                    bmax = bust_max if bust_max > float("-inf") else 0.0
                    result.append(_Action(i, idxs, probs, bust_ev, bmax))

    return result


def _solve(config: TurnConfig) -> Solution:
    states = _all_states(config)
    state_to_idx = {s: i for i, s in enumerate(states)}
    stop_values = np.array([score(s.n_skulls, s.held, config) for s in states], dtype=np.float64)

    actions = _precompute(states, state_to_idx, config)

    # Expected-value DP (value iteration). With the WIN_SCORE sentinel removed,
    # a single value function captures everything: 9-of-a-kind is just the
    # highest combo tier and folds naturally into the same Bellman recursion.
    V = stop_values.copy()
    while True:
        V_new = stop_values.copy()
        for a in actions:
            ev = float(np.dot(a.next_probs, V[a.next_idxs])) + a.bust_ev
            if ev > V_new[a.state_idx]:
                V_new[a.state_idx] = ev
        if np.max(np.abs(V_new - V)) < 1e-9:
            break
        V = V_new

    # Max-score DP (best-case dice, optimal play)
    max_score = stop_values.copy()
    while True:
        max_new = stop_values.copy()
        for a in actions:
            best_next = max(float(np.max(max_score[a.next_idxs])), a.bust_max) if len(a.next_idxs) else a.bust_max
            if best_next > max_new[a.state_idx]:
                max_new[a.state_idx] = best_next
        if np.max(np.abs(max_new - max_score)) < 1e-9:
            break
        max_score = max_new

    return Solution(config, states, state_to_idx, stop_values, V, max_score, actions)


def _save_solution(sol: Solution) -> None:
    _DISK_CACHE_DIR.mkdir(exist_ok=True)
    path = _DISK_CACHE_DIR / f"{_config_key(sol.config)}.npz"
    np.savez_compressed(path,
                        V=sol.V,
                        max_score=sol.max_score,
                        stop_values=sol.stop_values)


def _load_solution(config: TurnConfig) -> Solution | None:
    path = _DISK_CACHE_DIR / f"{_config_key(config)}.npz"
    if not path.exists():
        return None
    data = np.load(path)
    states = _all_states(config)
    state_to_idx = {s: i for i, s in enumerate(states)}
    return Solution(
        config=config,
        states=states,
        state_to_idx=state_to_idx,
        stop_values=data["stop_values"],
        V=data["V"],
        max_score=data["max_score"],
        actions=[],
    )


def get_solution(config: TurnConfig = DEFAULT_CONFIG) -> Solution:
    if config in _cache:
        return _cache[config]
    sol = _load_solution(config)
    if sol is None:
        sol = _solve(config)
        _save_solution(sol)
    _cache[config] = sol
    return sol


def V(state: State, config: TurnConfig = DEFAULT_CONFIG) -> float:
    sol = get_solution(config)
    return float(sol.V[sol.state_to_idx[state]])
