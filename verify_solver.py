#!/usr/bin/env python3
"""
verify_solver.py — Monte-Carlo verification of the DP solver's expected values.

Runs whole-turn simulations following the max-EV strategy at each decision point
and compares the empirical average score to the theoretical value from turn_ev().

Usage:
    uv run python verify_solver.py [--card CARD] [--n N] [--seed SEED] [--all]

Examples:
    uv run python verify_solver.py --card pirate --n 100000
    uv run python verify_solver.py --card guardian --n 200000
    uv run python verify_solver.py --all --n 50000
    uv run python verify_solver.py --n 50000          # default (no card)
"""
import argparse
import random
import sys
from statistics import mean, stdev

from solver.model import (
    Face, CARD_CONFIGS, DEFAULT_CONFIG, TurnConfig, State, NUM_FACES, WIN_SCORE,
)
from solver.scoring import score
from solver.actions import valid_actions, guardian_kept_options
from solver.stats import compute_stats
from solver.report import turn_ev
from solver.dp import get_solution, _add_outcome


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sample(n: int, rng: random.Random) -> tuple:
    """Roll n dice and return a face-count vector (length NUM_FACES)."""
    counts = [0] * NUM_FACES
    for _ in range(n):
        counts[rng.randint(0, NUM_FACES - 1)] += 1
    return tuple(counts)


# ── Policy pre-computation ────────────────────────────────────────────────────

def build_policy(config: TurnConfig) -> dict:
    """
    Pre-compute the optimal action for every non-terminal state.
    Returns a dict: State → (kept_tuple, use_guardian, is_stop).
    Building this once makes batch simulation ~10x faster than calling
    compute_stats on every simulated step.
    """
    sol = get_solution(config)   # warms the cache; prints nothing
    policy: dict[State, tuple] = {}

    for state in sol.states:
        current_score = score(state.n_skulls, state.held, config)
        if current_score == WIN_SCORE:
            policy[state] = (state.held, False, True)   # instant win → stop
            continue

        candidates = [
            compute_stats(state, kept, config)
            for kept in valid_actions(state, config)
        ]
        if config.skull_reroll_available and not state.skull_reroll_used and state.n_skulls >= 1:
            candidates += [
                compute_stats(state, kept, config, use_guardian=True)
                for kept in guardian_kept_options(state)
            ]

        best = max(candidates, key=lambda s: s.ev)
        policy[state] = (best.kept, best.use_guardian, best.n_reroll == 0)

    return policy


# ── Single-turn simulation ────────────────────────────────────────────────────

def _check_state(state: State, config: TurnConfig, label: str = "") -> None:
    """
    Assert the two fundamental invariants that must hold at every decision point.
    Only called when debug=True.
    """
    # 1. Skulls never stored in held (held[SKULL] is always 0).
    assert state.held[Face.SKULL] == 0, (
        f"{label}: skull leaked into held: {state}"
    )
    # 2. n_skulls + sum(held) == total_dice.
    total = state.n_skulls + sum(state.held)
    assert total == config.total_dice, (
        f"{label}: invariant broken — n_skulls({state.n_skulls}) + "
        f"sum(held)({sum(state.held)}) = {total} ≠ {config.total_dice}"
    )
    # 3. Pre-locked dice from card are always present in held.
    for f in range(1, NUM_FACES):
        assert state.held[f] >= config.initial_held[f], (
            f"{label}: initial_held[{f}]={config.initial_held[f]} "
            f"not in held={state.held}"
        )


def simulate_turn(config: TurnConfig, policy: dict, rng: random.Random,
                  debug: bool = False) -> float:
    """
    Simulate one complete turn following the optimal (max-EV) policy.

    Return value follows the V_normal convention used by turn_ev():
      - bust (3+ skulls)   → 0 for normal cards, -penalty for pirate-ship cards
      - instant win        → 0  (WIN_SCORE events excluded from normal EV)
      - normal stop        → stop score
    """
    bust_score = float(-config.sword_penalty if config.sword_penalty else 0)

    # ── Initial roll ──────────────────────────────────────────────────────────
    n_initial = config.total_dice - config.initial_n_skulls - sum(config.initial_held)
    outcome   = _sample(n_initial, rng)
    new_skulls = config.initial_n_skulls + outcome[Face.SKULL]
    # _add_outcome skips face=0 (SKULL), so skulls only go into new_skulls.
    new_held   = _add_outcome(config.initial_held, outcome)

    if new_skulls >= 3:
        if config.skull_reroll_available and new_skulls == 3:
            rescue = _sample(1, rng)
            if rescue[Face.SKULL]:
                return bust_score
            state = State(2, _add_outcome(new_held, rescue), skull_reroll_used=True)
        else:
            return bust_score
    else:
        state = State(new_skulls, new_held, skull_reroll_used=False)

    if debug:
        _check_state(state, config, "after initial roll")

    # ── Decision loop ─────────────────────────────────────────────────────────
    while True:
        kept, use_guardian, is_stop = policy[state]

        if debug and not is_stop:
            # Verify n_reroll is never 1 (game rule).
            if use_guardian:
                nr = (sum(state.held) - sum(kept)) + 1
            else:
                nr = config.total_dice - state.n_skulls - sum(kept)
            assert nr != 1, (
                f"n_reroll==1 reached: state={state}, kept={kept}, "
                f"use_guardian={use_guardian}"
            )
            assert nr == 0 or sum(kept) > 0, (
                f"n_reroll>0 but kept is empty: state={state}, kept={kept}"
            )

        if is_stop:
            s = score(state.n_skulls, state.held, config)
            return 0.0 if s == WIN_SCORE else float(s)

        if use_guardian:
            n_reroll       = (sum(state.held) - sum(kept)) + 1
            n_skulls_base  = state.n_skulls - 1
            reroll_used_next = True
        else:
            n_reroll       = config.total_dice - state.n_skulls - sum(kept)
            n_skulls_base  = state.n_skulls
            reroll_used_next = state.skull_reroll_used

        outcome    = _sample(n_reroll, rng)
        new_skulls = n_skulls_base + outcome[Face.SKULL]
        new_held   = _add_outcome(kept, outcome)

        if new_skulls >= 3:
            can_rescue = (
                config.skull_reroll_available
                and not reroll_used_next
                and new_skulls == 3
            )
            if can_rescue:
                rescue = _sample(1, rng)
                if rescue[Face.SKULL]:
                    return bust_score
                state = State(2, _add_outcome(new_held, rescue), skull_reroll_used=True)
            else:
                return bust_score
        else:
            state = State(new_skulls, new_held, skull_reroll_used=reroll_used_next)

        if debug:
            _check_state(state, config, "after reroll")


# ── Report ────────────────────────────────────────────────────────────────────

def report_card(card_name: str, config: TurnConfig, n: int, seed: int | None,
                debug: bool = False) -> None:
    label = card_name if card_name else "none (default)"
    print(f"\n{'='*62}")
    print(f"  Card : {label}")
    print(f"{'='*62}")

    print("  Building policy...", end=" ", flush=True)
    policy = build_policy(config)
    print("done.")

    theoretical = turn_ev(config)
    print(f"  Theoretical EV (turn_ev): {theoretical:>10.2f} pts")

    if debug:
        print(f"  Running {n:,} simulations (debug assertions ON)...", end=" ", flush=True)
    else:
        print(f"  Running {n:,} simulations...", end=" ", flush=True)
    rng    = random.Random(seed)
    scores = [simulate_turn(config, policy, rng, debug=debug) for _ in range(n)]
    print("done.")

    emp  = mean(scores)
    sd   = stdev(scores) if n > 1 else 0.0
    sem  = sd / n ** 0.5
    z    = abs(emp - theoretical) / (sem + 1e-15)
    rel  = abs(emp - theoretical) / (abs(theoretical) + 1e-9) * 100

    busts = sum(1 for s in scores if s < 0)
    zeros = sum(1 for s in scores if s == 0) - busts  # 0-point stops (not bust)
    wins  = sum(1 for s in scores if s == WIN_SCORE)

    print(f"  Empirical mean           : {emp:>10.2f} pts  (±{sem:.2f} SEM)")
    print(f"  Std deviation            : {sd:>10.2f} pts")
    print(f"  Relative error           : {rel:>9.3f}%")
    print(f"  |z-score|                : {z:>9.2f}  (< 3 → consistent)")
    print(f"  Bust rate                : {sum(1 for s in scores if s <= 0) / n:>9.1%}")
    if busts:
        print(f"  Bust (negative score)    : {busts/n:>9.1%}")
    if wins:
        print(f"  Instant wins (excluded)  : {wins:>9d}")
    print(f"  Score range              : [{int(min(scores))}, {int(max(scores))}]")

    status = "\033[32mPASS ✓\033[0m" if z < 3 else "\033[31mFAIL ✗\033[0m"
    print(f"  Result                   : {status}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Monte-Carlo verification of the DP solver's expected values."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--card", default=None, choices=list(CARD_CONFIGS),
        help="Card to simulate (default: no card).",
    )
    group.add_argument(
        "--all", action="store_true",
        help="Run all cards plus the default (no card).",
    )
    parser.add_argument("--n",    type=int,  default=100_000, help="Simulations per card (default: 100000).")
    parser.add_argument("--seed", type=int,  default=None,    help="Random seed for reproducibility.")
    parser.add_argument("--debug", action="store_true",
                        help="Enable runtime assertions (skulls in held, invariant, n_reroll rules).")
    args = parser.parse_args()

    if args.all:
        configs = [("", DEFAULT_CONFIG)] + list(CARD_CONFIGS.items())
    elif args.card:
        configs = [(args.card, CARD_CONFIGS[args.card])]
    else:
        configs = [("", DEFAULT_CONFIG)]

    for name, cfg in configs:
        report_card(name, cfg, args.n, args.seed, debug=args.debug)

    print()


if __name__ == "__main__":
    main()
