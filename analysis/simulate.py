#!/usr/bin/env python3
"""
simulate.py — Trace turns and/or collect score distributions under the optimal DP policy.

The DP solution is loaded from disk cache (.dp_cache/) if available, or computed and
saved on first run. Policy decisions are evaluated lazily at each step (no full
policy pre-computation), so each turn is near-instant after the cache is warm.

Usage:
    uv run python analysis/simulate.py [--card CARD] [--seed SEED] [--n N] [--quiet]

Options:
    --card CARD    Fortune card (default: none).
    --seed SEED    Random seed for reproducibility.
    --n N          Number of turns to simulate (default: 1).
    --quiet        Suppress per-turn traces; only show the stats summary.

Behaviour:
    --n 1          Full trace, no stats summary.
    --n N (N > 1)  Full traces for every turn, then a stats summary.
    --n N --quiet  No traces, just the stats summary (good for large N).

Examples:
    uv run python analysis/simulate.py --card guardian --seed 1
    uv run python analysis/simulate.py --card guardian --n 5 --seed 42
    uv run python analysis/simulate.py --card pirate --n 10000 --quiet
    uv run python analysis/simulate.py                              # no card, random seed
"""
import argparse
import random
from statistics import mean, stdev

from solver.model import Face, CARD_CONFIGS, DEFAULT_CONFIG, TurnConfig, NUM_FACES, State
from solver.scoring import score
from solver.actions import valid_actions, guardian_kept_options
from solver.stats import compute_stats
from solver.dp import get_solution, _add_outcome


# ── Face display ──────────────────────────────────────────────────────────────

FACE_SYMBOL: dict[int, str] = {
    Face.SKULL:   "💀",
    Face.SWORD:   "⚔️ ",
    Face.COIN:    "🪙",
    Face.DIAMOND: "💎",
    Face.MONKEY:  "🐒",
    Face.PARROT:  "🦜",
}


def _counts_to_faces(counts: tuple) -> list[int]:
    faces: list[int] = []
    for f in Face:
        faces.extend([int(f)] * counts[f])
    return faces


def _fmt(counts: tuple) -> str:
    faces = _counts_to_faces(counts)
    return " ".join(FACE_SYMBOL[f] for f in faces) if faces else "(none)"


def _fmt_split(before: tuple, after: tuple) -> tuple[str, str]:
    """Return (kept_str, rerolled_str) showing what changed between two count vectors."""
    kept:     list[int] = []
    rerolled: list[int] = []
    for f in Face:
        kept.extend([int(f)] * after[f])
        rerolled.extend([int(f)] * max(0, before[f] - after[f]))
    kept_str     = " ".join(FACE_SYMBOL[f] for f in kept)     or "(none)"
    rerolled_str = " ".join(FACE_SYMBOL[f] for f in rerolled) or "(none)"
    return kept_str, rerolled_str


# ── Dice rolling ──────────────────────────────────────────────────────────────

def _roll(n: int, rng: random.Random) -> tuple:
    counts = [0] * NUM_FACES
    for _ in range(n):
        counts[rng.randint(0, NUM_FACES - 1)] += 1
    return tuple(counts)


# ── Policy lookup (memoized per config) ──────────────────────────────────────

# Keyed by (config, state) so multiple cards can coexist in one process.
_policy_memo: dict[tuple, tuple] = {}


def _best_action(state: State, config: TurnConfig) -> tuple:
    """
    Return (kept, use_guardian, is_stop) for the given state under the optimal policy.
    Result is memoized: each distinct (config, state) pair is computed only once,
    so repeated visits within a batch run are O(1) dict lookups.
    """
    key = (config, state)
    if key in _policy_memo:
        return _policy_memo[key]

    # Zombie: no player choice — always keep swords, reroll everything else.
    # Stop when n_reroll==0 (all dice settled) OR when ≥4 skulls (guaranteed fail).
    if config.zombie:
        n_swords = state.held[Face.SWORD]
        n_reroll = config.total_dice - state.n_skulls - n_swords
        kept = tuple(state.held[f] if f == Face.SWORD else 0 for f in range(NUM_FACES))
        guaranteed_fail = (config.total_dice - state.n_skulls) < 5  # max possible swords < 5
        is_stop = n_reroll == 0 or guaranteed_fail
        result = kept, False, is_stop
        _policy_memo[key] = result
        return result

    # Storm card: reroll already used → only the stop action is available.
    if config.one_reroll_only and state.reroll_used:
        result = state.held, False, True  # kept=held, use_guardian=False, is_stop=True
        _policy_memo[key] = result
        return result

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
    result = best.kept, best.use_guardian, best.n_reroll == 0
    _policy_memo[key] = result
    return result


# ── Trace simulation ──────────────────────────────────────────────────────────

def simulate(config: TurnConfig, rng: random.Random,
             card_name: str = "", verbose: bool = True) -> float:
    """
    Simulate one turn under the optimal policy.
    When verbose=True, prints a full human-readable trace.
    Returns the final score.
    """
    W = 58

    def out(s: str = "") -> None:
        if verbose:
            print(s)

    if verbose:
        label = card_name if card_name else "no card (default)"
        print(f"\n{'═' * W}")
        print(f"  Card: {label}")
        if config.skull_reroll_available:
            print(f"  Guardian power: may reroll ONE skull die once this turn.")
        print(f"{'═' * W}")

    roll_num = 0

    def _show_state(n_skulls: int, held: tuple, guardian_used: bool) -> None:
        skull_str = f"💀 x{n_skulls}" if n_skulls else "none"
        held_str  = _fmt(held)
        if config.skull_reroll_available:
            guard_str = " [guardian used]" if guardian_used else " [guardian available]"
        else:
            guard_str = ""
        out(f"  Skulls locked : {skull_str}{guard_str}")
        out(f"  Dice in hand  : {held_str}")

    if verbose and (config.initial_n_skulls or sum(config.initial_held)):
        print(f"\n  [ Card gives you at the start ]")
        if config.initial_n_skulls:
            print(f"    Pre-locked skulls : 💀 x{config.initial_n_skulls}")
        if sum(config.initial_held):
            print(f"    Pre-held dice     : {_fmt(config.initial_held)}")

    # ── Initial roll ──────────────────────────────────────────────────────────
    n_initial = config.total_dice - config.initial_n_skulls - sum(config.initial_held)
    outcome   = _roll(n_initial, rng)
    roll_num += 1
    new_skulls = config.initial_n_skulls + outcome[Face.SKULL]
    new_held   = _add_outcome(config.initial_held, outcome)

    out(f"\n  ┌─ ROLL {roll_num} ({n_initial} dice) {'─' * max(0, W - 16 - len(str(n_initial)))}")
    out(f"  │  Rolled  : {_fmt(outcome)}")

    if config.zombie:
        # No bust; only track skulls and swords — other faces will be rerolled.
        zombie_held = [0] * NUM_FACES
        zombie_held[Face.SWORD] = new_held[Face.SWORD]
        state = State(new_skulls, tuple(zombie_held), False, False)
        _show_state(state.n_skulls, state.held, False)
    elif new_skulls >= 3:
        initial_bust = float(score(new_skulls, config.initial_held, config))
        out(f"  │  Result  : 💀 x{new_skulls} — BUST immediately!")
        if config.skull_reroll_available and new_skulls == 3:
            # Guardian: use skull-reroll proactively — same mechanic as any other turn.
            # Find the best keeper choice (max EV), then apply it with a real random roll.
            virtual_state = State(new_skulls, new_held, skull_reroll_used=False, reroll_used=False)
            best_stats = max(
                (compute_stats(virtual_state, kept, config, use_guardian=True)
                 for kept in guardian_kept_options(virtual_state)),
                key=lambda s: s.ev,
            )
            best_kept = best_stats.kept
            n_reroll   = best_stats.n_reroll
            kept_str, rerolled_str = _fmt_split(new_held, best_kept)
            out(f"  │  Guardian: proactive reroll — keep {kept_str}, "
                f"reroll {rerolled_str} + 💀 [{n_reroll} dice]")
            g_roll     = _roll(n_reroll, rng)
            out(f"  │    → Rolled: {_fmt(g_roll)}")
            new_g_skulls = 2 + g_roll[Face.SKULL]  # 2 locked skulls + reroll result
            if new_g_skulls >= 3:
                out(f"  │    → Rolled a skull — bust confirmed.")
                out(f"  └─ FINAL SCORE: {int(initial_bust)} pts")
                return initial_bust
            state = State(2, _add_outcome(best_kept, g_roll), skull_reroll_used=True, reroll_used=False)
            out(f"  │    → Saved! Continuing with 2 skulls.")
            _show_state(state.n_skulls, state.held, state.skull_reroll_used)
        else:
            out(f"  └─ FINAL SCORE: {int(initial_bust)} pts")
            return initial_bust
    else:
        state = State(new_skulls, new_held, skull_reroll_used=False, reroll_used=False)
        _show_state(state.n_skulls, state.held, False)

    # ── Decision loop ─────────────────────────────────────────────────────────
    while True:
        kept, use_guardian, is_stop = _best_action(state, config)

        if is_stop:
            final = float(score(state.n_skulls, state.held, config))
            out(f"  │  Decision : STOP")
            out(f"  └─ FINAL SCORE: {int(final)} pts")
            return final

        kept_str, rerolled_str = _fmt_split(state.held, kept)

        if use_guardian:
            n_reroll              = (sum(state.held) - sum(kept)) + 1
            n_skulls_base         = state.n_skulls - 1
            skull_reroll_used_next = True
            storm_reroll_used_next = state.reroll_used
            out(f"  │  Decision : Keep {kept_str}")
            out(f"  │             Reroll {rerolled_str}  +  💀 (guardian: rerolling 1 skull)")
            out(f"  │             [{n_reroll} dice total]")
        else:
            n_reroll              = config.total_dice - state.n_skulls - sum(kept)
            n_skulls_base         = state.n_skulls
            skull_reroll_used_next = state.skull_reroll_used
            storm_reroll_used_next = True if config.one_reroll_only else state.reroll_used
            out(f"  │  Decision : Keep {kept_str}")
            out(f"  │             Reroll {rerolled_str}  [{n_reroll} dice]")

        outcome    = _roll(n_reroll, rng)
        new_skulls = n_skulls_base + outcome[Face.SKULL]
        new_held   = _add_outcome(kept, outcome)
        # TI bust: only island (kept) dice score, not those rerolled this turn.
        bust_held  = kept if config.treasure_island else new_held
        roll_num  += 1

        out(f"  ├─ ROLL {roll_num} ({n_reroll} dice) {'─' * max(0, W - 16 - len(str(n_reroll)))}")
        out(f"  │  Rolled  : {_fmt(outcome)}")

        if config.zombie:
            # No bust; accumulate skulls and swords only; discard other faces.
            zombie_held = [0] * NUM_FACES
            zombie_held[Face.SWORD] = kept[Face.SWORD] + outcome[Face.SWORD]
            state = State(new_skulls, tuple(zombie_held), False, False)
            _show_state(state.n_skulls, state.held, False)
        elif new_skulls >= 3:
            can_rescue = (
                config.skull_reroll_available
                and not skull_reroll_used_next
                and new_skulls == 3
            )
            bust_score = float(score(new_skulls, bust_held, config))
            out(f"  │  Result  : 💀 x{new_skulls} — BUST!")
            if can_rescue:
                out(f"  │  Guardian: rerolling the 3rd skull...")
                rescue     = _roll(1, rng)
                rescue_sym = FACE_SYMBOL[_counts_to_faces(rescue)[0]] if sum(rescue) else "?"
                out(f"  │    → Rolled: {rescue_sym}")
                if rescue[Face.SKULL]:
                    out(f"  │    → Still a skull — bust confirmed.")
                    out(f"  └─ FINAL SCORE: {int(bust_score)} pts")
                    return bust_score
                state = State(2, _add_outcome(new_held, rescue),
                             skull_reroll_used=True, reroll_used=storm_reroll_used_next)
                out(f"  │    → Saved! Continuing with 2 skulls.")
                _show_state(state.n_skulls, state.held, state.skull_reroll_used)
            else:
                out(f"  └─ FINAL SCORE: {int(bust_score)} pts")
                return bust_score
        else:
            state = State(new_skulls, new_held,
                         skull_reroll_used=skull_reroll_used_next,
                         reroll_used=storm_reroll_used_next)
            _show_state(state.n_skulls, state.held, state.skull_reroll_used)


# ── Stats summary ─────────────────────────────────────────────────────────────

def print_stats(scores: list[float], config: TurnConfig) -> None:
    """Print mean/std/min/max and an ASCII histogram of score distribution."""
    n     = len(scores)
    mu    = mean(scores)
    sd    = stdev(scores) if n > 1 else 0.0
    lo    = int(min(scores))
    hi    = int(max(scores))

    # Bust = score <= 0 (0 for normal cards, negative for pirate-ship penalty)
    n_bust = sum(1 for s in scores if s <= 0)

    print(f"\n{'━' * 58}")
    print(f"  SCORE DISTRIBUTION  (n={n:,})")
    print(f"{'━' * 58}")
    print(f"  Mean   : {mu:>8.1f} pts")
    print(f"  Std    : {sd:>8.1f} pts")
    print(f"  Min    : {lo:>8d} pts")
    print(f"  Max    : {hi:>8d} pts")
    print(f"  Bust   : {n_bust / n:>8.1%}  ({n_bust:,} turns)")

    # ── Histogram ─────────────────────────────────────────────────────────────
    # Bust bucket is always shown separately; remaining scores go into equal-width bins.
    non_bust = [s for s in scores if s > 0]
    print()

    BAR_WIDTH = 30

    if not non_bust:
        print("  (all turns busted)")
        return

    s_min = int(min(non_bust))
    s_max = int(max(non_bust))

    # Choose a round bucket size so we get ~15–25 buckets.
    raw_step = max(1, (s_max - s_min + 1) / 20)
    for step in [50, 100, 200, 250, 500, 1000, 2000]:
        if step >= raw_step:
            bucket_size = step
            break
    else:
        bucket_size = int(raw_step)

    # Build buckets from 0 upward so bucket boundaries are always multiples of bucket_size.
    start = (s_min // bucket_size) * bucket_size
    edges = []
    v = start
    while v <= s_max:
        edges.append(v)
        v += bucket_size
    edges.append(v)  # one past the end

    buckets: list[int] = [0] * (len(edges) - 1)
    for s in non_bust:
        idx = min(int((s - edges[0]) // bucket_size), len(buckets) - 1)
        buckets[idx] += 1

    peak = max(buckets) if buckets else 1

    # Print bust row first
    bust_bar_len = round(n_bust / n * BAR_WIDTH * (peak / max(peak, n_bust / n * len(scores) / max(len(scores), 1))))
    # Simpler: normalise all bars (including bust) by n so heights are comparable.
    def _bar(count: int) -> str:
        length = round(count / n * BAR_WIDTH / (peak / n))
        return "█" * max(length, 1 if count else 0)

    peak_frac = peak / n
    def _bar2(count: int) -> str:
        if count == 0:
            return ""
        length = max(1, round(count / n / peak_frac * BAR_WIDTH))
        return "█" * length

    print(f"  {'Score range':>18}   {'Count':>6}   {'Freq':>5}   {'':30}")
    print(f"  {'─' * 18}   {'─' * 6}   {'─' * 5}   {'─' * BAR_WIDTH}")

    bust_label = f"{'bust (≤0)':>18}"
    bust_pct   = f"{n_bust/n:5.1%}"
    print(f"  {bust_label}   {n_bust:>6,}   {bust_pct}   {_bar2(n_bust)}")

    for i, count in enumerate(buckets):
        lo_b = edges[i]
        hi_b = edges[i + 1] - 1
        label = f"{lo_b:>6} – {hi_b:>6}"
        pct   = f"{count/n:5.1%}"
        print(f"  {label:>18}   {count:>6,}   {pct}   {_bar2(count)}")

    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate turns under the optimal DP policy, with optional tracing."
    )
    parser.add_argument(
        "--card", default=None, choices=[*CARD_CONFIGS, 'zombie'],
        help="Fortune card to use (default: none).",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--n", type=int, default=1,
        help="Number of turns to simulate (default: 1).",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-turn traces; only show the stats summary.",
    )
    parser.add_argument(
        "--save", metavar="FILE", default=None,
        help="Save per-game scores as a .npy file.",
    )
    args = parser.parse_args()

    card_name = args.card or ""
    config    = TurnConfig(zombie=True) if args.card == 'zombie' else (CARD_CONFIGS[args.card] if args.card else DEFAULT_CONFIG)
    verbose   = not args.quiet

    if not config.zombie:
        print(f"  Loading DP solution for '{card_name or 'default'}'...", end=" ", flush=True)
        get_solution(config)
        print("done.")

    rng    = random.Random(args.seed)
    scores: list[float] = []

    for i in range(args.n):
        if verbose and args.n > 1:
            print(f"\n{'━' * 58}")
            print(f"  Turn {i + 1} / {args.n}")
        scores.append(simulate(config, rng, card_name=card_name, verbose=verbose))

    if args.save:
        import numpy as np
        import os
        os.makedirs(os.path.dirname(args.save), exist_ok=True) if os.path.dirname(args.save) else None
        np.save(args.save, np.array(scores, dtype=np.float32))
        print(f"  Saved {len(scores):,} scores → {args.save}")

    if args.n > 1:
        print_stats(scores, config)
    elif args.quiet:
        # --quiet with --n 1: still show the score
        print(f"  Score: {int(scores[0])} pts")

    print()


if __name__ == "__main__":
    main()
