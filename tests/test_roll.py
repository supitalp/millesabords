import pytest
from solver.roll import roll_outcomes
from solver.model import Face, NUM_FACES


def test_zero_dice_single_outcome():
    outcomes = roll_outcomes(0)
    assert len(outcomes) == 1
    counts, prob = outcomes[0]
    assert prob == 1.0
    assert sum(counts) == 0


def test_one_die_six_outcomes_uniform():
    outcomes = roll_outcomes(1)
    assert len(outcomes) == NUM_FACES
    for counts, prob in outcomes:
        assert abs(prob - 1/6) < 1e-12
        assert sum(counts) == 1


def test_probabilities_sum_to_one():
    for n in range(1, 9):
        total = sum(prob for _, prob in roll_outcomes(n))
        assert abs(total - 1.0) < 1e-10, f"n={n}: total prob = {total}"


def test_two_dice_skull_prob():
    # P(at least 1 skull in 2 dice) = 1 - (5/6)^2 = 11/36
    outcomes = roll_outcomes(2)
    p_skull = sum(prob for counts, prob in outcomes if counts[Face.SKULL] > 0)
    assert abs(p_skull - 11/36) < 1e-12


def test_cached_same_object():
    # lru_cache should return same list object for same n
    assert roll_outcomes(3) is roll_outcomes(3)
