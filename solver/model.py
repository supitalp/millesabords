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
NUM_DICE = 8  # dice rolled per turn (always 8; cards add extra dice on top)

DIE_FACES = tuple(Face)

# Points for a combo of N identical dice (N < 3 → 0)
COMBO_SCORE: dict[int, int] = {3: 100, 4: 200, 5: 500, 6: 1000, 7: 2000, 8: 4000}

# Sentinel for the "9 identical dice" instant-win (Magie pirate rule).
# Large enough to dominate all normal scores; finite so numpy value iteration stays stable.
WIN_SCORE = 1_000_000

_EMPTY_HELD = tuple([0] * NUM_FACES)


class TurnConfig(NamedTuple):
    """
    All card-specific parameters for a single turn.

    total_dice      : total dice in play this turn (8 + any extra dice from the card).
    initial_n_skulls: skulls pre-locked at turn start (Tête de Mort card).
    initial_held    : non-skull dice pre-set at turn start (Pièce d'or / Diamant card).
                      Length-NUM_FACES count vector; index 0 (SKULL) must be 0.
    merge_animals   : monkeys and parrots count as the same symbol for combos (Animaux card).
    score_multiplier: final score is multiplied by this (Pirate card uses 2).
    """
    total_dice: int = NUM_DICE
    initial_n_skulls: int = 0
    initial_held: tuple = _EMPTY_HELD
    merge_animals: bool = False
    score_multiplier: int = 1


DEFAULT_CONFIG = TurnConfig()

# Named configs for each card
def _held_with(face: "Face", count: int = 1) -> tuple:
    counts = [0] * NUM_FACES
    counts[face] = count
    return tuple(counts)


CARD_CONFIGS: dict[str, TurnConfig] = {
    "tete-de-mort-1": TurnConfig(total_dice=9,  initial_n_skulls=1),
    "tete-de-mort-2": TurnConfig(total_dice=10, initial_n_skulls=2),
    "piece-d-or":     TurnConfig(total_dice=9,  initial_held=_held_with(Face.COIN)),
    "diamant":        TurnConfig(total_dice=9,  initial_held=_held_with(Face.DIAMOND)),
    "animaux":        TurnConfig(merge_animals=True),
    "pirate":         TurnConfig(score_multiplier=2),
}


class State(NamedTuple):
    """
    n_skulls: accumulated locked skulls (0–2; hitting 3 ends the turn immediately)
    held: length-NUM_FACES count vector; held[SKULL] is always 0.

    Invariant: n_skulls + sum(held) == config.total_dice at every decision point.
    """
    n_skulls: int
    held: tuple  # length NUM_FACES, index = Face value
