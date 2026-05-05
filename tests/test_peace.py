"""Tests for the Peace card (BGA variant: no swords, else −1000/sword, no doubling)."""
import pytest
from solver.model import Face, NUM_FACES, State, CARD_CONFIGS, DEFAULT_CONFIG
from solver.scoring import score
from solver.dp import get_solution
from solver.report import turn_ev

PEACE = CARD_CONFIGS["peace"]


def held(*pairs):
    counts = [0] * NUM_FACES
    for face, count in pairs:
        counts[face] = count
    return tuple(counts)


# ---------------------------------------------------------------------------
# Scoring: no swords → normal score, no multiplier
# ---------------------------------------------------------------------------

def test_no_swords_scores_normally():
    h = held((Face.MONKEY, 3), (Face.PARROT, 5))
    assert score(0, h, PEACE) == score(0, h, DEFAULT_CONFIG)


def test_no_swords_full_chest_applies():
    h = held((Face.PARROT, 8))
    # 8 of a kind = 4000, full chest +500
    assert score(0, h, PEACE) == 4500


def test_no_swords_no_multiplier():
    h = held((Face.MONKEY, 8))
    assert score(0, h, PEACE) == score(0, h, DEFAULT_CONFIG)
    assert score(0, h, PEACE) != score(0, h, CARD_CONFIGS["pirate"])


# ---------------------------------------------------------------------------
# Scoring: swords present → −1000 × n_swords, overrides everything
# ---------------------------------------------------------------------------

def test_one_sword_penalty():
    h = held((Face.SWORD, 1), (Face.MONKEY, 7))
    assert score(0, h, PEACE) == -1000


def test_two_swords_penalty():
    h = held((Face.SWORD, 2), (Face.MONKEY, 6))
    assert score(0, h, PEACE) == -2000


def test_three_swords_penalty():
    h = held((Face.SWORD, 3), (Face.MONKEY, 5))
    assert score(0, h, PEACE) == -3000


def test_sword_penalty_overrides_combo():
    # 8 swords would be 4000 pts normally — Peace turns it into the worst penalty
    h = held((Face.SWORD, 8))
    assert score(0, h, PEACE) == -8000


def test_sword_penalty_with_skulls_non_bust():
    h = held((Face.SWORD, 2), (Face.MONKEY, 5))
    assert score(1, h, PEACE) == -2000
    assert score(2, h, PEACE) == -2000


# ---------------------------------------------------------------------------
# Scoring: bust (3+ skulls)
# ---------------------------------------------------------------------------

def test_bust_no_swords_gives_zero():
    h = held((Face.MONKEY, 5))
    assert score(3, h, PEACE) == 0


def test_bust_with_swords_gives_penalty():
    h = held((Face.SWORD, 2), (Face.MONKEY, 3))
    assert score(3, h, PEACE) == -2000


def test_bust_one_sword_penalty():
    h = held((Face.SWORD, 1), (Face.PARROT, 4))
    assert score(3, h, PEACE) == -1000


# ---------------------------------------------------------------------------
# DP: solver produces valid solutions
# ---------------------------------------------------------------------------

def test_dp_solves():
    sol = get_solution(PEACE)
    assert len(sol.states) > 0


def test_v_at_least_stop_value():
    sol = get_solution(PEACE)
    assert (sol.V >= sol.stop_values - 1e-9).all()


def test_ev_is_finite():
    ev = turn_ev(PEACE)
    assert -10_000 < ev < 10_000


def test_stop_value_negative_with_sword():
    # A state with a sword held should have a negative stop value
    sol = get_solution(PEACE)
    state = State(0, held((Face.SWORD, 1), (Face.MONKEY, 7)))
    idx = sol.state_to_idx[state]
    assert sol.stop_values[idx] == -1000


def test_v_better_than_stop_when_sword_held():
    # From a state with 1 sword, the solver should prefer rerolling over stopping
    sol = get_solution(PEACE)
    state = State(0, held((Face.SWORD, 1), (Face.MONKEY, 7)))
    idx = sol.state_to_idx[state]
    assert sol.V[idx] > sol.stop_values[idx]
