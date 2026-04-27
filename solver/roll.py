from functools import lru_cache
from itertools import combinations_with_replacement
from math import factorial, prod
from .model import NUM_FACES, DIE_FACES, Face


def _multinomial_prob(counts: tuple) -> float:
    n = sum(counts)
    numerator = factorial(n)
    denominator = prod(factorial(c) for c in counts)
    return (numerator / denominator) / (NUM_FACES ** n)


@lru_cache(maxsize=None)
def roll_outcomes(n_dice: int) -> list[tuple[tuple, float]]:
    """
    All distinct outcomes of rolling n_dice fair dice.
    Returns list of (counts_tuple, probability) where counts_tuple is
    a length-NUM_FACES vector indexed by Face.
    """
    if n_dice == 0:
        return [(tuple([0] * NUM_FACES), 1.0)]

    results = []
    for combo in combinations_with_replacement(DIE_FACES, n_dice):
        counts = [0] * NUM_FACES
        for face in combo:
            counts[face] += 1
        counts_tuple = tuple(counts)
        prob = _multinomial_prob(counts_tuple)
        results.append((counts_tuple, prob))

    return results
