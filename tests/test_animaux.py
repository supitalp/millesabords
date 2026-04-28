"""Tests for the Animaux card (monkeys and parrots count as the same symbol)."""
import pytest
from solver.model import Face, NUM_FACES, State, CARD_CONFIGS, DEFAULT_CONFIG
from solver.scoring import score
from solver.dp import get_solution

ANIMAUX = CARD_CONFIGS["animaux"]


def held(*pairs):
    counts = [0] * NUM_FACES
    for face, count in pairs:
        counts[face] = count
    return tuple(counts)


# ---------------------------------------------------------------------------
# Scoring: monkey+parrot merged into one combo
# Use n_skulls=1 to avoid full board bonus (requires n_skulls==0)
# ---------------------------------------------------------------------------

def test_merge_increases_combo():
    # 3 monkeys + 3 parrots: default=100+100=200; animaux=6-combo=1000
    h = held((Face.MONKEY, 3), (Face.PARROT, 3), (Face.SWORD, 1))
    assert score(1, h, DEFAULT_CONFIG) == 200
    assert score(1, h, ANIMAUX) == 1000


def test_partial_mix_reaches_threshold():
    # 2 monkeys + 1 parrot = 3 animals → combo of 3 = 100
    h = held((Face.MONKEY, 2), (Face.PARROT, 1), (Face.SWORD, 4))
    assert score(1, h, ANIMAUX) == 300   # animals=3→100; swords=4→200


def test_mixed_animals_and_swords():
    # 2 monkeys + 2 parrots + 3 swords (n_skulls=1, sum=7)
    # animaux: animals=4→200, swords=3→100
    h = held((Face.MONKEY, 2), (Face.PARROT, 2), (Face.SWORD, 3))
    assert score(1, h, ANIMAUX) == 300
    # default: monkeys=2→0, parrots=2→0, swords=3→100
    assert score(1, h, DEFAULT_CONFIG) == 100


def test_8_animals_combo():
    # 5 monkeys + 3 parrots (n_skulls=0, but swords=0 → full board check)
    # full board: animals=8≥3 ✓ → +500
    h = held((Face.MONKEY, 5), (Face.PARROT, 3))
    # animaux: COMBO_SCORE[8]=4000, full board +500
    assert score(0, h, ANIMAUX) == 4500
    # default: monkeys=5→500, parrots=3→100, full board: 5≥3 and 3≥3 ✓ → +500
    assert score(0, h, DEFAULT_CONFIG) == 1100


def test_below_3_animals_no_combo():
    # 1 monkey + 1 parrot — even merged, 2 < 3 → no combo
    h = held((Face.MONKEY, 1), (Face.PARROT, 1), (Face.SWORD, 3), (Face.COIN, 2))
    # animaux: animals=2→0, swords=3→100, coin=2→0+200
    assert score(1, h, ANIMAUX) == 300
    # default: same (no combo for 1 of each)
    assert score(1, h, DEFAULT_CONFIG) == 300


# ---------------------------------------------------------------------------
# Full board bonus with animaux
# ---------------------------------------------------------------------------

def test_full_board_bonus_merged_animals():
    # 3 monkeys + 5 swords (sum=8=total_dice, n_skulls=0)
    # swords=5→500, animals=3→100, full board: sword≥3 ✓, animals≥3 ✓ → +500
    h = held((Face.MONKEY, 3), (Face.SWORD, 5))
    assert score(0, h, ANIMAUX) == 1100


def test_full_board_bonus_mixed_animals():
    # 2 monkeys + 1 parrot + 5 swords → animals=3, swords=5; full board ✓
    h = held((Face.MONKEY, 2), (Face.PARROT, 1), (Face.SWORD, 5))
    assert score(0, h, ANIMAUX) == 1100  # 500 + 100 + 500


def test_no_full_board_bonus_animals_below_3():
    # 1 monkey + 1 parrot + 6 swords → animals=2 < 3 → full board fails
    h = held((Face.MONKEY, 1), (Face.PARROT, 1), (Face.SWORD, 6))
    # swords=6→1000, animals=2→0, no full board bonus (animals don't contribute)
    assert score(0, h, ANIMAUX) == 1000


def test_no_full_board_bonus_animals_below_3_default():
    # Same but default: monkeys=1→0, parrots=1→0, swords=6→1000
    # full board: monkey=1 < 3 and not coin/diamond → bonus fails
    h = held((Face.MONKEY, 1), (Face.PARROT, 1), (Face.SWORD, 6))
    assert score(0, h, DEFAULT_CONFIG) == 1000


# ---------------------------------------------------------------------------
# DP: animaux solution is correctly solved
# ---------------------------------------------------------------------------

def test_dp_solves_animaux():
    sol = get_solution(ANIMAUX)
    assert len(sol.states) > 0
    assert (sol.V >= 0).all()


def test_v_at_least_stop_value_animaux():
    sol = get_solution(ANIMAUX)
    assert (sol.V >= sol.stop_values).all()


def test_merged_animals_higher_stop_value():
    """Same hand scores more with animaux than without, when animals form a larger combo."""
    # 3 monkeys + 3 parrots + 2 swords, n_skulls=0
    h = held((Face.MONKEY, 3), (Face.PARROT, 3), (Face.SWORD, 2))
    # animaux: animals=6→1000, swords=2→0. Full board: sword=2 < 3 → no bonus. Total=1000
    assert score(0, h, ANIMAUX) == 1000
    # default: monkeys=3→100, parrots=3→100, swords=2→0. Full board: sword=2 fails. Total=200
    assert score(0, h, DEFAULT_CONFIG) == 200
