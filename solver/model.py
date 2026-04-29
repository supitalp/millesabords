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

# Points for a combo of N identical dice (N < 3 → 0). The 9-of-a-kind score
# (reachable only with the Coin or Diamond card, which add a 9th die) extends
# the geometric doubling progression and is treated as just another (very high)
# combo score — no instant-win sentinel.
COMBO_SCORE: dict[int, int] = {3: 100, 4: 200, 5: 500, 6: 1000, 7: 2000, 8: 4000, 9: 8000}

_EMPTY_HELD = tuple([0] * NUM_FACES)


class TurnConfig(NamedTuple):
    """
    All card-specific parameters for a single turn.

    total_dice      : total dice in play this turn (8 + any extra dice from the card).
    initial_n_skulls: skulls pre-locked at turn start (Tête de Mort card).
    initial_held    : non-skull dice pre-set at turn start (Pièce d'or / Diamant card).
                      Length-NUM_FACES count vector; index 0 (SKULL) must be 0.
    merge_animals   : monkeys and parrots count as the same symbol for combos (Animals card).
    score_multiplier       : final score is multiplied by this (Pirate card uses 2).
    required_swords        : minimum swords needed to score (Pirate Ship card).
    sword_bonus            : points added on top of normal score when sword requirement is met.
    sword_penalty          : points subtracted from game score when requirement is NOT met;
                             turn contribution becomes −sword_penalty (skull busts also give −penalty).
    skull_reroll_available : once per turn the player may reroll one skull die (Guardian card).
    """
    total_dice: int = NUM_DICE
    initial_n_skulls: int = 0
    initial_held: tuple = _EMPTY_HELD
    merge_animals: bool = False
    score_multiplier: int = 1
    required_swords: int = 0
    sword_bonus: int = 0
    sword_penalty: int = 0
    skull_reroll_available: bool = False
    treasure_island: bool = False


DEFAULT_CONFIG = TurnConfig()

# Named configs for each card
def _held_with(face: "Face", count: int = 1) -> tuple:
    counts = [0] * NUM_FACES
    counts[face] = count
    return tuple(counts)


CARD_CONFIGS: dict[str, TurnConfig] = {
    "skull-1":       TurnConfig(total_dice=9,  initial_n_skulls=1),
    "skull-2":       TurnConfig(total_dice=10, initial_n_skulls=2),
    "coin":     TurnConfig(total_dice=9,  initial_held=_held_with(Face.COIN)),
    "diamond":       TurnConfig(total_dice=9,  initial_held=_held_with(Face.DIAMOND)),
    "animals":       TurnConfig(merge_animals=True),
    "pirate":        TurnConfig(score_multiplier=2),
    "guardian":      TurnConfig(skull_reroll_available=True),
    "pirate-ship-2": TurnConfig(required_swords=2, sword_bonus=300,  sword_penalty=300),
    "pirate-ship-3": TurnConfig(required_swords=3, sword_bonus=500,  sword_penalty=500),
    "pirate-ship-4": TurnConfig(required_swords=4, sword_bonus=1000, sword_penalty=1000),
    "treasure-island": TurnConfig(treasure_island=True),
}


class State(NamedTuple):
    """
    n_skulls: accumulated locked skulls (0–2; hitting 3 ends the turn immediately)
    held: length-NUM_FACES count vector; held[SKULL] is always 0.
    skull_reroll_used: True once the Guardian one-time skull-reroll ability has been used.

    Invariant: n_skulls + sum(held) == config.total_dice at every decision point.
    """
    n_skulls: int
    held: tuple  # length NUM_FACES, index = Face value
    skull_reroll_used: bool = False
