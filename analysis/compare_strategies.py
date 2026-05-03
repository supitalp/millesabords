#!/usr/bin/env python3
"""
compare_strategies.py — Empirically compare the DP optimal strategy against
simple heuristic alternatives.

Simulates N complete turns under each strategy and produces a ranked comparison
table showing how much the DP optimal policy outperforms each heuristic.

Strategies
----------
• DP Optimal       — the exact max-EV policy from the Bellman DP solver.
• Threshold K      — stop as soon as score ≥ K; while below K, keep every die
                     from faces with count ≥ 2 and reroll lone singletons.
• Bold             — never stop voluntarily; always keep only the single most
                     frequent face and reroll everything else.  Stops only when
                     forced (no legal reroll remains).
• One-shot         — stop immediately after the very first roll; never reroll.

Usage:
    uv run python analysis/compare_strategies.py [--card CARD] [--n N] [--seed SEED] [--all]

Examples:
    uv run python analysis/compare_strategies.py
    uv run python analysis/compare_strategies.py --card pirate --n 100000
    uv run python analysis/compare_strategies.py --all --n 50000
"""

import argparse
import random
from statistics import mean, stdev

from solver.model import Face, CARD_CONFIGS, DEFAULT_CONFIG, TurnConfig, State, NUM_FACES
from solver.scoring import score
from solver.dp import get_solution
from solver.report import turn_ev
from analysis.verify_solver import build_policy, simulate_turn, _sample


# ── Heuristic helpers ──────────────────────────────────────────────────────────

def _try_reroll(state: State, config: TurnConfig,
                desired: list[int]) -> tuple[tuple, bool, bool]:
    """
    Validate desired_kept against the game's reroll constraints and return an
    action triple (kept, use_guardian=False, is_stop).

    Constraints enforced:
      • kept[f] is clamped to [initial_held[f], state.held[f]].
      • n_reroll must not be 1 (forbidden by the rules).
      • At least 1 die must be kept when rerolling.
    Falls back to the stop action whenever the desired kept vector would produce
    an illegal reroll.
    """
    kept = tuple(
        max(config.initial_held[f], min(desired[f], state.held[f]))
        for f in range(NUM_FACES)
    )
    n_reroll = config.total_dice - state.n_skulls - sum(kept)

    if n_reroll <= 1 or sum(kept) == 0:
        return state.held, False, True  # stop

    return kept, False, False


# ── Policy builders ────────────────────────────────────────────────────────────

def build_one_shot_policy(config: TurnConfig) -> dict:
    """Stop at every decision state — no rerolls ever."""
    sol = get_solution(config)
    return {s: (s.held, False, True) for s in sol.states}


def build_threshold_policy(config: TurnConfig, K: int) -> dict:
    """
    Stop when current stop_score ≥ K.

    While below threshold:
      • Keep all dice from faces with count ≥ 2.
      • If every face is a singleton, keep the face with the highest count so
        that there is something to build on.
    Fall back to a stop whenever no legal reroll can be constructed.
    """
    sol = get_solution(config)
    policy: dict[State, tuple] = {}

    for state in sol.states:
        if score(state.n_skulls, state.held, config) >= K:
            policy[state] = (state.held, False, True)
            continue

        desired = [0] * NUM_FACES
        for f in range(1, NUM_FACES):
            if state.held[f] >= 2:
                desired[f] = state.held[f]

        if sum(desired[1:]) == 0:  # all singletons
            best_f = max(range(1, NUM_FACES), key=lambda f: state.held[f])
            desired[best_f] = state.held[best_f]

        policy[state] = _try_reroll(state, config, desired)

    return policy


def build_bold_policy(config: TurnConfig) -> dict:
    """
    Never stop voluntarily.

    At each step, keep only the single most frequent non-skull face (and any
    card-locked dice) and reroll everything else.  Stop only when no legal
    reroll remains.

    Note: for the Animals card (merge_animals=True), monkey and parrot are
    treated as separate faces here — the bold heuristic may not group them
    optimally, but it still plays legally.
    """
    sol = get_solution(config)
    policy: dict[State, tuple] = {}

    for state in sol.states:
        best_f = max(range(1, NUM_FACES), key=lambda f: state.held[f])

        desired = list(config.initial_held)
        desired[best_f] = max(desired[best_f], state.held[best_f])

        policy[state] = _try_reroll(state, config, desired)

    return policy


# ── Simulation ─────────────────────────────────────────────────────────────────

def _simulate_all(config: TurnConfig, named_policies: list[tuple[str, dict]],
                  n: int, seed: int | None) -> list[tuple[str, list[float]]]:
    """Run N simulations for each policy; each strategy gets its own seeded RNG."""
    results = []
    for name, policy in named_policies:
        rng    = random.Random(seed)
        scores = [simulate_turn(config, policy, rng) for _ in range(n)]
        results.append((name, scores))
    return results


# ── Report ─────────────────────────────────────────────────────────────────────

def compare_card(card_name: str, config: TurnConfig, n: int,
                 seed: int | None) -> None:
    label = card_name if card_name else "none (default)"
    print(f"\n{'='*66}")
    print(f"  Card: {label}  —  {n:,} simulations per strategy")
    print(f"{'='*66}")

    print("  Building policies...", end=" ", flush=True)
    named_policies = [
        ("DP Optimal",       build_policy(config)),
        ("Threshold K=500",  build_threshold_policy(config, 500)),
        ("Threshold K=200",  build_threshold_policy(config, 200)),
        ("Bold (best face)", build_bold_policy(config)),
        ("One-shot",         build_one_shot_policy(config)),
    ]
    print("done.")

    theoretical_ev = turn_ev(config)
    print(f"  Theoretical EV (DP): {theoretical_ev:.2f} pts")

    print(f"  Simulating...", end=" ", flush=True)
    sim_results = _simulate_all(config, named_policies, n, seed)
    print("done.\n")

    dp_em  = mean(sim_results[0][1])
    dp_sem = stdev(sim_results[0][1]) / n ** 0.5

    header = f"  {'Strategy':<22}  {'EV':>8}  {'±SEM':>5}  {'≤0%':>5}  {'vs DP':>9}  z"
    print(header)
    print(f"  {'-' * (len(header) - 2)}")

    for name, scores in sim_results:
        em  = mean(scores)
        sd  = stdev(scores)
        sem = sd / n ** 0.5
        p0  = sum(1 for s in scores if s <= 0) / n

        if name == "DP Optimal":
            vs_str = "—"
            z_str  = "—"
        else:
            diff         = em - dp_em
            combined_sem = (sem ** 2 + dp_sem ** 2) ** 0.5
            z            = diff / (combined_sem + 1e-15)
            vs_str       = f"{diff:+.1f}"
            z_str        = f"{z:.1f}"

        print(f"  {name:<22}  {em:>8.1f}  {sem:>5.1f}  {p0:>5.1%}  {vs_str:>9}  {z_str}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare DP optimal strategy vs heuristics via Monte Carlo simulation."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--card", default=None, choices=list(CARD_CONFIGS),
        help="Card to test (default: no card).",
    )
    group.add_argument(
        "--all", action="store_true",
        help="Run all cards plus the no-card baseline.",
    )
    parser.add_argument("--n",    type=int, default=50_000,
                        help="Simulations per strategy (default: 50000).")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility.")
    args = parser.parse_args()

    if args.all:
        configs = [("", DEFAULT_CONFIG)] + list(CARD_CONFIGS.items())
    elif args.card:
        configs = [(args.card, CARD_CONFIGS[args.card])]
    else:
        configs = [("", DEFAULT_CONFIG)]

    for name, cfg in configs:
        compare_card(name, cfg, args.n, args.seed)

    print()


if __name__ == "__main__":
    main()
