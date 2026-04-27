from .model import State, Face, NUM_FACES, NUM_DICE, TurnConfig, DEFAULT_CONFIG
from .actions import valid_actions
from .scoring import score
from .stats import compute_stats, ActionStats


FACE_NAMES = {
    Face.SKULL:   "Skull",
    Face.SWORD:   "Sword",
    Face.COIN:    "Coin",
    Face.DIAMOND: "Diamond",
    Face.MONKEY:  "Monkey",
    Face.PARROT:  "Parrot",
}


def dice_to_state(dice: list[Face], config: TurnConfig = DEFAULT_CONFIG) -> State:
    """
    Convert a list of NUM_DICE rolled Face values into a State, merging any
    pre-set dice and skulls from the card config.
    """
    assert len(dice) == NUM_DICE
    counts = list(config.initial_held)
    for f in dice:
        counts[f] += 1
    n_skulls = config.initial_n_skulls + counts[Face.SKULL]
    counts[Face.SKULL] = 0
    return State(n_skulls=n_skulls, held=tuple(counts))


def _describe_kept(kept: tuple) -> str:
    parts = []
    for face_val in range(1, NUM_FACES):
        c = kept[face_val]
        if c > 0:
            parts.append(f"{c}×{FACE_NAMES[Face(face_val)]}")
    return ", ".join(parts) if parts else "nothing"


def _describe_dice(dice: list[Face]) -> str:
    from collections import Counter
    counts = Counter(dice)
    parts = [f"{counts[f]}×{FACE_NAMES[f]}" for f in Face if counts[f] > 0]
    return ", ".join(parts)


def report(dice: list[Face], config: TurnConfig = DEFAULT_CONFIG) -> str:
    state = dice_to_state(dice, config)
    current_score = score(state.n_skulls, state.held, config)

    lines = []
    lines.append("=" * 70)
    lines.append("MILLE SABORDS — TURN SOLVER")
    lines.append("=" * 70)
    lines.append(f"Dice rolled : {_describe_dice(dice)}")
    if config.initial_n_skulls:
        lines.append(f"Card skulls : {config.initial_n_skulls} (pre-locked)")
    if any(config.initial_held):
        lines.append(f"Card dice   : {_describe_kept(config.initial_held)}")
    lines.append(f"Skulls locked: {state.n_skulls}")
    lines.append(f"Score if stopping now: {current_score} pts")

    if state.n_skulls >= 3:
        lines.append("\n💀 Three skulls — turn is lost (0 points).")
        return "\n".join(lines)

    actions = valid_actions(state, config)
    all_stats: list[ActionStats] = [compute_stats(state, kept, config) for kept in actions]
    all_stats.sort(key=lambda s: s.ev, reverse=True)

    lines.append("")
    header = (f"{'#':>3}  {'Action':<40}  {'P(lose)':>8}  {'EV':>7}  "
              f"{'EV|safe':>8}  {'Min':>6}  {'Max':>6}  {'ΔvsStop':>8}")
    lines.append(header)
    lines.append("-" * len(header))

    for i, s in enumerate(all_stats):
        if s.n_reroll == 0:
            action_desc = "STOP"
        else:
            action_desc = f"keep {_describe_kept(s.kept)}, reroll {s.n_reroll}"

        marker = "★" if i == 0 else " "
        row = (
            f"{marker}{i+1:>2}  "
            f"{action_desc:<40}  "
            f"{s.p_lose:>7.1%}  "
            f"{s.ev:>7.1f}  "
            f"{s.ev_no_lose:>8.1f}  "
            f"{s.min_score:>6}  "
            f"{s.max_score:>6}  "
            f"{s.delta_vs_stop:>+8.1f}"
        )
        lines.append(row)

    lines.append("")
    lines.append("★ = recommended action (highest expected value)")
    lines.append("EV|safe = expected score conditioned on not losing")
    lines.append("Min/Max = range of reachable scores (excl. loss)")
    lines.append("ΔvsStop = EV gain vs stopping right now")
    lines.append("=" * 70)

    return "\n".join(lines)
