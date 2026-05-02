from itertools import product
from .model import State, NUM_FACES, Face, TurnConfig, DEFAULT_CONFIG


def _sub_multisets(counts: tuple) -> list[tuple]:
    """All sub-multisets of a count vector (including empty and full)."""
    ranges = [range(c + 1) for c in counts]
    return list(product(*ranges))


def valid_actions(state: State, config: TurnConfig = DEFAULT_CONFIG) -> list[tuple]:
    """
    Return all valid kept_counts tuples for the given state.
    Each tuple is a length-NUM_FACES count vector of non-skull dice to keep.

    The card's initial_held dice are always kept (they are locked and cannot be rerolled).
    Includes the stop action (keep everything, n_reroll=0).
    Excludes n_reroll==1 and n_reroll==total_held (must keep at least 1 die when rerolling).
    """
    actions = []
    # Variable dice: held minus the card's locked initial_held dice (skulls always 0).
    held_variable = tuple(
        max(0, state.held[f] - config.initial_held[f]) if f != Face.SKULL else 0
        for f in range(NUM_FACES)
    )

    for kept_variable in _sub_multisets(held_variable):
        # Card's initial dice are always included on top of the chosen variable kept.
        kept = tuple(kv + ih for kv, ih in zip(kept_variable, config.initial_held))
        n_kept = sum(kept)
        n_reroll = config.total_dice - state.n_skulls - n_kept

        if n_reroll < 0 or n_reroll == 1:
            continue
        if n_reroll > 0 and n_kept == 0:
            continue  # must keep at least 1 die when rerolling

        actions.append(kept)

    return actions


def guardian_kept_options(state: State) -> list[tuple]:
    """
    Valid 'kept' tuples when using the Guardian skull-reroll ability.
    Total rerolled = (sum(held) - sum(kept)) + 1 skull; must be in [2, 7]:
    - at least 1 non-skull die must also be rerolled (sum(k) <= total_held - 1)
    - at least 1 die must be kept, never reroll all dice (sum(k) >= 1)
    Only call when skull_reroll_available and not skull_reroll_used and n_skulls >= 1.
    """
    total_held = sum(state.held)
    return [k for k in _sub_multisets(state.held) if 1 <= sum(k) <= total_held - 1]
