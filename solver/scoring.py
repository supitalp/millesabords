from .model import Face, COMBO_SCORE, TurnConfig, DEFAULT_CONFIG


def _score_combos(held: tuple, config: TurnConfig) -> int:
    """
    Compute combo + coin/diamond individual bonuses + sword bonus/penalty + multiplier.
    Does NOT check the full-chest bonus; that is the caller's responsibility.
    Safe to call on a busted hand (with n_skulls >= 3).
    """
    total = 0

    if config.merge_animals:
        animal_count = held[Face.MONKEY] + held[Face.PARROT]
        for face in range(1, 6):  # skip SKULL
            if face in (Face.MONKEY, Face.PARROT):
                continue
            count = held[face]
            total += COMBO_SCORE.get(count, 0)
            if face in (Face.COIN, Face.DIAMOND):
                total += 100 * count
        total += COMBO_SCORE.get(animal_count, 0)
    else:
        for face in range(1, 6):  # skip SKULL (index 0)
            count = held[face]
            total += COMBO_SCORE.get(count, 0)
            if face in (Face.COIN, Face.DIAMOND):
                total += 100 * count

    # Pirate Ship: sword requirement not met → fixed penalty, no multiplier.
    if config.required_swords > 0 and held[Face.SWORD] < config.required_swords:
        return -config.sword_penalty

    total += config.sword_bonus
    return total * config.score_multiplier


def score(n_skulls: int, held: tuple, config: TurnConfig = DEFAULT_CONFIG) -> int:
    """
    Compute the score for a completed turn.
    Returns 0 if n_skulls >= 3 (bust), except with the Treasure Island card which scores
    the held dice even on a bust. A 9-of-a-kind (reachable only with the Coin/Diamond
    card) is just the highest combo tier — no special-case win sentinel.
    """
    # Peace card: any held sword → penalty overrides all other scoring (including bust).
    if config.forbidden_sword_penalty > 0 and held[Face.SWORD] > 0:
        return -(config.forbidden_sword_penalty * held[Face.SWORD])

    if n_skulls >= 3:
        if config.treasure_island:
            # Score the held dice even on bust. Full-chest is impossible with 3+ skulls
            # (need every die contributing), so we skip that check and just score combos.
            return _score_combos(held, config)
        return -config.sword_penalty if config.sword_penalty else 0

    total = 0

    if config.merge_animals:
        animal_count = held[Face.MONKEY] + held[Face.PARROT]
        for face in range(1, 6):  # skip SKULL
            if face in (Face.MONKEY, Face.PARROT):
                continue
            count = held[face]
            total += COMBO_SCORE.get(count, 0)
            if face in (Face.COIN, Face.DIAMOND):
                total += 100 * count
        total += COMBO_SCORE.get(animal_count, 0)
    else:
        animal_count = None
        for face in range(1, 6):  # skip SKULL (index 0)
            count = held[face]
            total += COMBO_SCORE.get(count, 0)
            if face in (Face.COIN, Face.DIAMOND):
                total += 100 * count

    # Full treasure chest bonus: all dice must individually contribute, no skulls.
    # A die contributes if it is a coin/diamond (always +100 each) or part of a combo (count >= 3).
    # With merge_animals, monkey+parrot together must form a combo of >= 3.
    if n_skulls == 0 and sum(held) == config.total_dice:
        if config.merge_animals:
            all_contribute = all(
                held[f] == 0 or held[f] >= 3 or f in (Face.COIN, Face.DIAMOND)
                for f in (Face.SWORD,)
            ) and (animal_count == 0 or animal_count >= 3)
        else:
            all_contribute = all(
                held[f] == 0
                or held[f] >= 3
                or f in (Face.COIN, Face.DIAMOND)
                for f in range(1, 6)
            )
        if all_contribute:
            total += 500

    # Pirate Ship: sword requirement not met → fixed penalty, no multiplier.
    if config.required_swords > 0 and held[Face.SWORD] < config.required_swords:
        return -config.sword_penalty

    total += config.sword_bonus
    return total * config.score_multiplier
