from .model import Face, COMBO_SCORE, WIN_SCORE, TurnConfig, DEFAULT_CONFIG


def score(n_skulls: int, held: tuple, config: TurnConfig = DEFAULT_CONFIG) -> int:
    """
    Compute the score for a completed turn.
    Returns 0 if n_skulls >= 3 (should not normally be called in that case).
    Returns WIN_SCORE if 9 identical dice are achieved (Magie pirate instant win).
    """
    if n_skulls >= 3:
        return 0

    # Magie pirate: exactly 9 identical dice = instant game win.
    # The rule requires specifically 9 — 8 identical in the base game is not a win.
    if n_skulls == 0:
        for f in range(1, 6):
            if held[f] == 9:
                return WIN_SCORE

    total = 0

    for face in range(1, 6):  # skip SKULL (index 0)
        count = held[face]
        total += COMBO_SCORE.get(count, 0)
        if face in (Face.COIN, Face.DIAMOND):
            total += 100 * count

    # Full treasure chest bonus: all dice must individually contribute, no skulls.
    # A die contributes if it is a coin/diamond (always +100 each) or part of a combo (count >= 3).
    if n_skulls == 0 and sum(held) == config.total_dice:
        all_contribute = all(
            held[f] == 0
            or held[f] >= 3
            or f in (Face.COIN, Face.DIAMOND)
            for f in range(1, 6)
        )
        if all_contribute:
            total += 500

    return total
