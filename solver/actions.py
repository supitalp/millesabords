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
    Excludes actions where n_reroll == 1 (not allowed by rules).
    """
    actions = []
    held_non_skull = list(state.held)
    held_non_skull[Face.SKULL] = 0

    for kept in _sub_multisets(tuple(held_non_skull)):
        n_kept = sum(kept)
        n_reroll = config.total_dice - state.n_skulls - n_kept

        if state.n_skulls + n_kept < 1:
            continue
        if n_reroll < 0 or n_reroll == 1:
            continue

        actions.append(kept)

    return actions
