from itertools import product
from .model import State, NUM_DICE, NUM_FACES, Face


def _sub_multisets(counts: tuple) -> list[tuple]:
    """All sub-multisets of a count vector (including empty and full)."""
    ranges = [range(c + 1) for c in counts]
    return list(product(*ranges))


def valid_actions(state: State) -> list[tuple]:
    """
    Return all valid kept_counts tuples for the given state.
    Each tuple is a length-NUM_FACES count vector of dice to keep.

    Includes the stop action (keep everything, n_reroll=0).
    Excludes actions where n_reroll == 1 (not allowed by rules).
    """
    actions = []
    # Only enumerate sub-multisets of the non-skull held dice
    held_non_skull = list(state.held)
    held_non_skull[Face.SKULL] = 0  # skulls are never in held, but be safe

    for kept in _sub_multisets(tuple(held_non_skull)):
        n_kept = sum(kept)
        n_reroll = NUM_DICE - state.n_skulls - n_kept

        # Must keep at least 1 die total (skulls count)
        if state.n_skulls + n_kept < 1:
            continue
        # n_reroll must be 0 (stop) or >= 2 (reroll at least 2)
        if n_reroll < 0 or n_reroll == 1:
            continue

        actions.append(kept)

    return actions
