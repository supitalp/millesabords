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

    Includes the stop action (keep everything, n_reroll=0).
    Excludes n_reroll==1 and n_reroll==total_held (must keep at least 1 die when rerolling).
    """
    actions = []
    held_non_skull = list(state.held)
    held_non_skull[Face.SKULL] = 0

    for kept in _sub_multisets(tuple(held_non_skull)):
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
    Total rerolled = (sum(held) - sum(kept)) + 1 skull; must be >= 2,
    so at least 1 non-skull die must also be rerolled.
    Only call when skull_reroll_available and not skull_reroll_used and n_skulls >= 1.
    """
    total_held = sum(state.held)
    return [k for k in _sub_multisets(state.held) if sum(k) <= total_held - 1]
