from .model import Face, NUM_DICE, COMBO_SCORE


def score(n_skulls: int, held: tuple) -> int:
    """
    Compute the score for a completed turn.
    Returns 0 if n_skulls >= 3 (should not normally be called in that case).
    """
    if n_skulls >= 3:
        return 0

    total = 0

    for face in range(1, 6):  # skip SKULL (index 0)
        count = held[face]
        total += COMBO_SCORE.get(count, 0)
        if face in (Face.COIN, Face.DIAMOND):
            total += 100 * count

    # Full treasure chest bonus: all 8 dice must individually contribute to the score.
    # A die contributes if it is a coin/diamond (always +100 each) or part of a combo (count >= 3).
    # Swords, monkeys, and parrots with count 1 or 2 score nothing and forfeit the bonus.
    if n_skulls == 0 and sum(held) == NUM_DICE:
        all_contribute = all(
            held[f] == 0
            or held[f] >= 3
            or f in (Face.COIN, Face.DIAMOND)
            for f in range(1, 6)
        )
        if all_contribute:
            total += 500

    return total
