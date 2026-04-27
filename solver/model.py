from enum import IntEnum
from typing import NamedTuple


class Face(IntEnum):
    SKULL = 0
    SWORD = 1
    COIN = 2
    DIAMOND = 3
    MONKEY = 4
    PARROT = 5


NUM_FACES = len(Face)
NUM_DICE = 8

DIE_FACES = tuple(Face)

# Points for a combo of N identical dice (N < 3 → 0)
COMBO_SCORE: dict[int, int] = {3: 100, 4: 200, 5: 500, 6: 1000, 7: 2000, 8: 4000}


class State(NamedTuple):
    """
    n_skulls: accumulated locked skulls (0–2; hitting 3 ends the turn immediately)
    held: length-6 count vector over Face values; held[SKULL] is always 0
    """
    n_skulls: int
    held: tuple  # length NUM_FACES, index = Face value
