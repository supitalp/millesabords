import tabulate as _tabulate_mod
_tabulate_mod.WIDE_CHARS_MODE = True
from tabulate import tabulate

from .model import State, Face, NUM_FACES, NUM_DICE, TurnConfig, DEFAULT_CONFIG, WIN_SCORE
from .actions import valid_actions, guardian_kept_options
from .scoring import score
from .stats import compute_stats, ActionStats
from .roll import roll_outcomes
from .dp import get_solution, _add_outcome


FACE_EMOJI = {
    Face.SKULL:   "💀",
    Face.SWORD:   "⚔️",
    Face.COIN:    "🪙",
    Face.DIAMOND: "💎",
    Face.MONKEY:  "🐒",
    Face.PARROT:  "🦜",
}


def dice_to_state(dice: list[Face], config: TurnConfig = DEFAULT_CONFIG) -> State:
    """
    Convert a list of rolled Face values into a State, merging any
    pre-set dice and skulls from the card config.
    """
    assert len(dice) == config.total_dice - config.initial_n_skulls - sum(config.initial_held)
    counts = list(config.initial_held)
    for f in dice:
        counts[f] += 1
    n_skulls = config.initial_n_skulls + counts[Face.SKULL]
    counts[Face.SKULL] = 0
    return State(n_skulls=n_skulls, held=tuple(counts))


def _fmt_counts(counts: tuple, include_skull: bool = False) -> str:
    """Render a count vector as repeated emojis: 3 monkeys → 🐒🐒🐒."""
    parts = []
    start = 0 if include_skull else 1
    for face_val in range(start, NUM_FACES):
        c = counts[face_val]
        if c > 0:
            parts.append(FACE_EMOJI[Face(face_val)] * c)
    return " ".join(parts) if parts else "—"


def _describe_dice(dice: list[Face]) -> str:
    """Show each rolled die as an emoji (one per die, in order by face)."""
    from collections import Counter
    counts = Counter(dice)
    parts = []
    for f in Face:
        parts.extend([FACE_EMOJI[f]] * counts[f])
    return "  ".join(parts)


def _keep_str(state: State, s: ActionStats, config: TurnConfig = DEFAULT_CONFIG) -> str:
    base = state.held if s.n_reroll == 0 else s.kept
    shown = tuple(max(0, base[f] - config.initial_held[f]) for f in range(NUM_FACES))
    return _fmt_counts(shown) if any(shown) else "—"


def _reroll_str(state: State, s: ActionStats) -> str:
    if s.n_reroll == 0:
        return "—"
    rerolled = [state.held[f] - s.kept[f] for f in range(NUM_FACES)]
    if s.use_guardian:
        rerolled[Face.SKULL] += 1
    return _fmt_counts(tuple(rerolled), include_skull=True)


def report(dice: list[Face], config: TurnConfig = DEFAULT_CONFIG, verbose: bool = False) -> str:
    state = dice_to_state(dice, config)
    current_score = score(state.n_skulls, state.held, config)

    lines = []
    lines.append("=" * 60)
    lines.append("MILLE SABORDS — TURN SOLVER")
    lines.append("=" * 60)
    lines.append(f"Dice rolled  : {_describe_dice(dice)}")
    if config.initial_n_skulls:
        lines.append(f"Card skulls  : {'💀' * config.initial_n_skulls} (pre-locked)")
    if any(config.initial_held):
        lines.append(f"Card die     : {_fmt_counts(config.initial_held)}")
    if state.n_skulls:
        lines.append(f"Skulls locked: {'💀' * state.n_skulls}")
    lines.append(f"Stop score   : {current_score} pts")

    if state.n_skulls >= 3:
        lines.append("\n💀💀💀 Three skulls — turn is lost.")
        return "\n".join(lines)

    if current_score == WIN_SCORE:
        lines.append("\n🏆 9 identical dice — INSTANT WIN (Pirate's Magic)!")
        return "\n".join(lines)

    all_stats: list[ActionStats] = [
        compute_stats(state, kept, config) for kept in valid_actions(state, config)
    ]
    if config.skull_reroll_available and not state.skull_reroll_used and state.n_skulls >= 1:
        all_stats += [
            compute_stats(state, kept, config, use_guardian=True)
            for kept in guardian_kept_options(state)
        ]
    all_stats.sort(key=lambda s: (-s.ev, s.p_lose))

    any_win_possible = any(s.p_win > 0 for s in all_stats)

    base_headers = ["", "Keep", "Reroll", "P(lose)", "EV", "ΔvsStop"]
    base_align   = ("right", "left", "left", "right", "right", "right")
    if verbose:
        extra_h = ["P(win)", "EV|safe", "Min", "Max"] if any_win_possible else ["EV|safe", "Min", "Max"]
        extra_a = ("right",) * len(extra_h)
        headers   = base_headers[:5] + list(extra_h) + [base_headers[-1]]
        col_align = base_align[:5]   + extra_a        + (base_align[-1],)
    else:
        headers, col_align = base_headers, base_align

    rows = []
    for i, s in enumerate(all_stats):
        is_stop = s.n_reroll == 0
        is_best = i == 0
        if is_stop and is_best:
            marker = "🛑⭐"
        elif is_stop:
            marker = "🛑"
        elif is_best:
            marker = "⭐"
        else:
            marker = f"{i + 1}"
        max_str = "WIN" if s.max_score == WIN_SCORE else str(s.max_score)
        row = [marker, _keep_str(state, s, config), _reroll_str(state, s),
               f"{s.p_lose:.1%}", f"{s.ev:.1f}", f"{s.delta_vs_stop:+.1f}"]
        if verbose:
            extras = ([f"{s.p_win:.2%}"] if any_win_possible else []) + \
                     [f"{s.ev_no_lose:.1f}", str(s.min_score), max_str]
            row = row[:-1] + extras + [row[-1]]
        rows.append(row)

    lines.append("")
    lines.append(tabulate(rows, headers=headers, colalign=col_align, tablefmt="simple"))
    lines.append("")
    lines.append("⭐ = recommended action  |  🛑 = stop  |  ΔvsStop = EV gain vs stopping now")
    if verbose:
        lines.append("EV|safe = expected score if no bust  |  Min/Max = score range")
        if any_win_possible:
            lines.append("P(win) = probability of 9 identical dice (instant game win)")
    lines.append("=" * 60)

    return "\n".join(lines)


def turn_ev(config: TurnConfig = DEFAULT_CONFIG) -> float:
    """Expected score for a fresh turn (before any dice are rolled), using optimal play."""
    sol = get_solution(config)
    n_roll = config.total_dice - config.initial_n_skulls - sum(config.initial_held)
    ev = 0.0
    for outcome, prob in roll_outcomes(n_roll):
        new_skulls = config.initial_n_skulls + outcome[Face.SKULL]
        if new_skulls >= 3:
            new_held = _add_outcome(config.initial_held, outcome)
            # On the initial roll, the player has not yet had a chance to place
            # any dice on Treasure Island, so the bust score is always based on
            # config.initial_held only (= 0 for the standard TI card).
            initial_bust_score = float(score(new_skulls, config.initial_held, config))
            if config.skull_reroll_available and new_skulls == 3:
                for rescue_outcome, rescue_prob in roll_outcomes(1):
                    if rescue_outcome[Face.SKULL] == 0:
                        rescue_held = _add_outcome(new_held, rescue_outcome)
                        state = State(2, rescue_held, True)
                        idx = sol.state_to_idx[state]
                        ev += prob * rescue_prob * float(sol.V_normal[idx])
                    else:
                        ev += prob * rescue_prob * initial_bust_score
            else:
                ev += prob * initial_bust_score
            continue
        new_held = _add_outcome(config.initial_held, outcome)
        state = State(new_skulls, new_held, False)
        idx = sol.state_to_idx[state]
        ev += prob * float(sol.V_normal[idx])
    return ev


def report_turn_start(config: TurnConfig = DEFAULT_CONFIG) -> str:
    ev = turn_ev(config)
    lines = ["=" * 60, "MILLE SABORDS — TURN SOLVER", "=" * 60]
    if config.initial_n_skulls:
        lines.append(f"Card skulls : {'💀' * config.initial_n_skulls} (pre-locked)")
    if any(config.initial_held):
        lines.append(f"Card die    : {_fmt_counts(config.initial_held)}")
    lines.append(f"\nExpected score this turn (optimal play): {ev:.1f} pts")
    lines.append("=" * 60)
    return "\n".join(lines)
