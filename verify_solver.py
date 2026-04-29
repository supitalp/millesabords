#!/usr/bin/env python3
"""
verify_solver.py — Monte-Carlo verification of the DP solver's expected values.

Runs whole-turn simulations following the max-EV strategy at each decision point
and compares the empirical average score to the theoretical value from turn_ev().

Also supports a Q-check mode that empirically estimates Q(s, a) for every action
at a sample of states and verifies the DP's chosen action is always the best one.

Usage:
    uv run python verify_solver.py [--card CARD] [--n N] [--seed SEED] [--all]
    uv run python verify_solver.py --q-check [--card CARD] [--q-states N] [--q-rollouts N]

Examples:
    uv run python verify_solver.py --card pirate --n 100000
    uv run python verify_solver.py --card guardian --n 200000
    uv run python verify_solver.py --all --n 50000
    uv run python verify_solver.py --n 50000                    # default (no card)
    uv run python verify_solver.py --q-check --q-states 200 --q-rollouts 3000
    uv run python verify_solver.py --q-check --card pirate --q-states 100
"""
import argparse
import random
import sys
from statistics import mean, stdev

from solver.model import (
    Face, CARD_CONFIGS, DEFAULT_CONFIG, TurnConfig, State, NUM_FACES,
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

    Return value matches turn_ev():
      - bust (3+ skulls)   → 0 for normal cards, -penalty for pirate-ship cards,
                             held-dice score for treasure-island
      - normal stop        → stop score (including 9-of-a-kind = 8000 + bonuses)
    """
    # ── Initial roll ──────────────────────────────────────────────────────────
    n_initial = config.total_dice - config.initial_n_skulls - sum(config.initial_held)
    outcome   = _sample(n_initial, rng)
    new_skulls = config.initial_n_skulls + outcome[Face.SKULL]
    # _add_outcome skips face=0 (SKULL), so skulls only go into new_skulls.
    new_held   = _add_outcome(config.initial_held, outcome)

    if new_skulls >= 3:
        # On the initial roll the player has not yet placed anything on Treasure
        # Island, so the bust score is based on config.initial_held only (= 0
        # for the standard TI card).
        initial_bust = float(score(new_skulls, config.initial_held, config))
        if config.skull_reroll_available and new_skulls == 3:
            rescue = _sample(1, rng)
            if rescue[Face.SKULL]:
                return initial_bust
            state = State(2, _add_outcome(new_held, rescue), skull_reroll_used=True)
        else:
            return initial_bust
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
            return float(score(state.n_skulls, state.held, config))

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
                    return float(score(new_skulls, new_held, config))
                state = State(2, _add_outcome(new_held, rescue), skull_reroll_used=True)
            else:
                return float(score(new_skulls, new_held, config))
        else:
            state = State(new_skulls, new_held, skull_reroll_used=reroll_used_next)

        if debug:
            _check_state(state, config, "after reroll")


# ── Q-check helpers ───────────────────────────────────────────────────────────

def _simulate_continuation(state: State, config: TurnConfig, policy: dict,
                            rng: random.Random) -> float:
    """
    Follow the DP policy from a mid-turn state until the turn ends.
    Identical semantics to the decision loop inside simulate_turn, but without
    the optional debug assertions so it can be called in tight inner loops.
    """
    while True:
        kept, use_guardian, is_stop = policy[state]

        if is_stop:
            return float(score(state.n_skulls, state.held, config))

        if use_guardian:
            n_reroll      = (sum(state.held) - sum(kept)) + 1
            n_skulls_base = state.n_skulls - 1
            reroll_used_next = True
        else:
            n_reroll      = config.total_dice - state.n_skulls - sum(kept)
            n_skulls_base = state.n_skulls
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
                    return float(score(new_skulls, new_held, config))
                state = State(2, _add_outcome(new_held, rescue), skull_reroll_used=True)
            else:
                return float(score(new_skulls, new_held, config))
        else:
            state = State(new_skulls, new_held, skull_reroll_used=reroll_used_next)


def _estimate_q(state: State, kept: tuple, use_guardian: bool,
                config: TurnConfig, policy: dict,
                rng: random.Random, n_rollouts: int) -> tuple[float, float]:
    """
    Estimate Q(state, action=(kept, use_guardian)) via Monte Carlo.

    Executes one step of the given action, then follows the DP policy for the
    rest of the turn.  Returns (empirical_mean, sem).

    The stop action (n_reroll == 0) is deterministic, so it returns immediately
    with sem=0.
    """
    if use_guardian:
        n_reroll         = (sum(state.held) - sum(kept)) + 1
        n_skulls_base    = state.n_skulls - 1
        reroll_used_next = True
    else:
        n_reroll         = config.total_dice - state.n_skulls - sum(kept)
        n_skulls_base    = state.n_skulls
        reroll_used_next = state.skull_reroll_used

    if n_reroll == 0:
        return float(score(state.n_skulls, state.held, config)), 0.0

    results: list[float] = []
    for _ in range(n_rollouts):
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
                    results.append(float(score(new_skulls, new_held, config)))
                    continue
                next_state = State(2, _add_outcome(new_held, rescue), skull_reroll_used=True)
                results.append(_simulate_continuation(next_state, config, policy, rng))
            else:
                results.append(float(score(new_skulls, new_held, config)))
        else:
            next_state = State(new_skulls, new_held, skull_reroll_used=reroll_used_next)
            results.append(_simulate_continuation(next_state, config, policy, rng))

    m   = mean(results)
    sem = stdev(results) / n_rollouts ** 0.5
    return m, sem


def q_check_card(card_name: str, config: TurnConfig, n_states: int,
                 n_rollouts: int, seed: int | None) -> bool:
    """
    For a random sample of non-trivial states, estimate Q(s, a) for every valid
    action via Monte Carlo and verify that the DP-chosen action achieves the
    highest empirical Q-value.

    A "violation" is flagged when a non-DP action beats the DP action by more
    than 3.5 combined standard errors (controls false-positive rate for the
    multiple comparisons across all states × actions).

    Returns True when no violations are found.
    """
    label = card_name if card_name else "none (default)"
    print(f"\n{'='*62}")
    print(f"  Q-Check Card : {label}")
    print(f"{'='*62}")

    print("  Building policy...", end=" ", flush=True)
    policy = build_policy(config)
    sol    = get_solution(config)
    print("done.")

    # States where at least one reroll action exists (non-trivial decisions).
    def _has_reroll(state: State) -> bool:
        for k in valid_actions(state, config):
            if config.total_dice - state.n_skulls - sum(k) > 0:
                return True
        if config.skull_reroll_available and not state.skull_reroll_used and state.n_skulls >= 1:
            return len(guardian_kept_options(state)) > 0
        return False

    checkable   = [s for s in sol.states if _has_reroll(s)]
    rng         = random.Random(seed)
    sample_size = min(n_states, len(checkable))
    sampled     = rng.sample(checkable, sample_size)

    print(f"  Non-trivial states  : {len(checkable):,}  (sampled {sample_size})")
    print(f"  Rollouts per action : {n_rollouts:,}")
    print(f"  Violation threshold : z > 3.5")
    print(f"  Running...", flush=True)

    total_actions = 0
    violations: list[tuple] = []
    worst_z     = 0.0
    worst_info: tuple | None = None

    for i, state in enumerate(sampled):
        # All (kept, use_guardian) pairs for this state.
        all_actions: list[tuple[tuple, bool]] = [
            (k, False) for k in valid_actions(state, config)
        ]
        if config.skull_reroll_available and not state.skull_reroll_used and state.n_skulls >= 1:
            all_actions += [(k, True) for k in guardian_kept_options(state)]

        dp_kept, dp_use_guardian, _ = policy[state]
        dp_action = (dp_kept, dp_use_guardian)
        dp_analytical = float(sol.V[sol.state_to_idx[state]])

        # Estimate Q for every action.
        q_results: dict[tuple, tuple[float, float]] = {}
        for action in all_actions:
            q_results[action] = _estimate_q(
                state, action[0], action[1], config, policy, rng, n_rollouts
            )

        total_actions += len(q_results)

        dp_q, dp_sem = q_results[dp_action]
        best_action  = max(q_results, key=lambda a: q_results[a][0])
        best_q, best_sem = q_results[best_action]

        if best_action != dp_action:
            gap          = best_q - dp_q
            combined_sem = (dp_sem ** 2 + best_sem ** 2) ** 0.5
            z            = gap / (combined_sem + 1e-15)

            info = (state, dp_action, dp_analytical, dp_q, dp_sem,
                    best_action, best_q, best_sem, z)
            if z > worst_z:
                worst_z    = z
                worst_info = info
            if z > 3.5:
                violations.append(info)

        if (i + 1) % 10 == 0 or (i + 1) == sample_size:
            print(f"    [{i+1:3d}/{sample_size}]  violations so far: {len(violations)}", end="\r")

    print()  # clear progress line

    print(f"\n  States checked      : {sample_size}")
    print(f"  Actions evaluated   : {total_actions:,}")
    print(f"  Violations (z>3.5)  : {len(violations)}")

    if worst_info:
        (state, dp_action, dp_analytical, dp_q, dp_sem,
         best_action, best_q, best_sem, z) = worst_info
        print(f"\n  Worst near-miss (z={z:.2f}):")
        print(f"    State        : {state.n_skulls} skull(s), held={state.held}, "
              f"guardian_used={state.skull_reroll_used}")
        print(f"    DP action    : kept={dp_action[0]}, guardian={dp_action[1]}")
        print(f"    DP analytical: {dp_analytical:.2f} pts")
        print(f"    DP empirical : {dp_q:.2f} ± {dp_sem:.2f}")
        print(f"    Best alt     : kept={best_action[0]}, guardian={best_action[1]}")
        print(f"    Alt empirical: {best_q:.2f} ± {best_sem:.2f}")

    if violations:
        print(f"\n  VIOLATIONS (first {min(5, len(violations))}):")
        for (state, dp_action, dp_analytical, dp_q, dp_sem,
             best_action, best_q, best_sem, z) in violations[:5]:
            print(f"    State: {state.n_skulls} skull(s), held={state.held}")
            print(f"      DP : kept={dp_action[0]}  Q={dp_q:.1f}±{dp_sem:.1f}"
                  f"  (analytical={dp_analytical:.1f})")
            print(f"      Alt: kept={best_action[0]}  Q={best_q:.1f}±{best_sem:.1f}"
                  f"  z={z:.1f}")

    status = "\033[32mPASS ✓\033[0m" if not violations else "\033[31mFAIL ✗\033[0m"
    print(f"  Result              : {status}")
    return not violations


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

    print(f"  Empirical mean           : {emp:>10.2f} pts  (±{sem:.2f} SEM)")
    print(f"  Std deviation            : {sd:>10.2f} pts")
    print(f"  Relative error           : {rel:>9.3f}%")
    print(f"  |z-score|                : {z:>9.2f}  (< 3 → consistent)")
    print(f"  Bust rate                : {sum(1 for s in scores if s <= 0) / n:>9.1%}")
    if busts:
        print(f"  Bust (negative score)    : {busts/n:>9.1%}")
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
        help="Card to test (default: no card).",
    )
    group.add_argument(
        "--all", action="store_true",
        help="Run all cards plus the default (no card).",
    )
    parser.add_argument("--n",    type=int,  default=100_000, help="Simulations per card for EV check (default: 100000).")
    parser.add_argument("--seed", type=int,  default=None,    help="Random seed for reproducibility.")
    parser.add_argument("--debug", action="store_true",
                        help="Enable runtime assertions in EV check (skulls in held, invariant, n_reroll rules).")

    # Q-check mode
    parser.add_argument("--q-check", action="store_true",
                        help="Run Q-value check: estimate Q(s,a) for every action at sampled states "
                             "and verify the DP policy always picks the empirically best action.")
    parser.add_argument("--q-states",   type=int, default=100,
                        help="Number of states to sample per card in Q-check (default: 100).")
    parser.add_argument("--q-rollouts", type=int, default=2_000,
                        help="Monte-Carlo rollouts per action per state in Q-check (default: 2000).")

    args = parser.parse_args()

    if args.all:
        configs = [("", DEFAULT_CONFIG)] + list(CARD_CONFIGS.items())
    elif args.card:
        configs = [(args.card, CARD_CONFIGS[args.card])]
    else:
        configs = [("", DEFAULT_CONFIG)]

    if args.q_check:
        all_pass = True
        for name, cfg in configs:
            passed = q_check_card(name, cfg, args.q_states, args.q_rollouts, args.seed)
            all_pass = all_pass and passed
        print()
        sys.exit(0 if all_pass else 1)
    else:
        for name, cfg in configs:
            report_card(name, cfg, args.n, args.seed, debug=args.debug)
        print()


if __name__ == "__main__":
    main()
