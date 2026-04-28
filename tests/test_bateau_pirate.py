"""Tests for Bateau pirate cards (sword requirement, bonus on success, penalty on failure)."""
import pytest
from solver.model import Face, NUM_FACES, State, CARD_CONFIGS, DEFAULT_CONFIG
from solver.scoring import score
from solver.dp import get_solution
from solver.report import turn_ev

BP2 = CARD_CONFIGS["bateau-pirate-2"]
BP3 = CARD_CONFIGS["bateau-pirate-3"]
BP4 = CARD_CONFIGS["bateau-pirate-4"]


def held(*pairs):
    counts = [0] * NUM_FACES
    for face, count in pairs:
        counts[face] = count
    return tuple(counts)


# ---------------------------------------------------------------------------
# Scoring: success path (meets requirement)
# ---------------------------------------------------------------------------

def test_bp2_success_adds_bonus():
    # 2 swords + 3 monkeys + 3 parrots, n_skulls=0 → meets ≥2 swords
    # swords=2→0 combo, monkeys=3→100, parrots=3→100, full board (3+3+2≥3? sword=2<3 → fails)
    # n_skulls=0, sum=8=total_dice, sword=2 < 3 → full board NOT met
    h = held((Face.SWORD, 2), (Face.MONKEY, 3), (Face.PARROT, 3))
    base = score(0, h, DEFAULT_CONFIG)   # 100+100 = 200
    assert base == 200
    assert score(0, h, BP2) == 200 + 300  # bonus +300


def test_bp3_success_adds_bonus():
    h = held((Face.SWORD, 3), (Face.MONKEY, 5))
    # swords=3→100, monkeys=5→500, full board (3≥3 ✓, 5≥3 ✓) → +500 → 1100
    assert score(0, h, DEFAULT_CONFIG) == 1100
    assert score(0, h, BP3) == 1100 + 500


def test_bp4_success_adds_bonus():
    h = held((Face.SWORD, 4), (Face.MONKEY, 4))
    # swords=4→200, monkeys=4→200, full board (4≥3 ✓, 4≥3 ✓) → +500 → 900
    assert score(0, h, DEFAULT_CONFIG) == 900
    assert score(0, h, BP4) == 900 + 1000


def test_success_with_excess_swords():
    # 6 swords, n_skulls=1 — exceeding the requirement is fine
    h = held((Face.SWORD, 5), (Face.COIN, 2))
    assert score(1, h, BP2) == 500 + 200 + 300   # sword combo + coin individual + bonus
    assert score(1, h, BP3) == 500 + 200 + 500
    assert score(1, h, BP4) == 500 + 200 + 1000


# ---------------------------------------------------------------------------
# Scoring: failure path (does not meet requirement)
# ---------------------------------------------------------------------------

def test_bp2_failure_returns_penalty():
    h = held((Face.SWORD, 1), (Face.MONKEY, 7))
    assert score(0, h, BP2) == -300


def test_bp3_failure_returns_penalty():
    h = held((Face.SWORD, 2), (Face.MONKEY, 6))
    assert score(0, h, BP3) == -500


def test_bp4_failure_returns_penalty():
    h = held((Face.SWORD, 3), (Face.MONKEY, 5))
    assert score(0, h, BP4) == -1000


def test_no_swords_at_all():
    h = held((Face.MONKEY, 8))
    assert score(0, h, BP2) == -300
    assert score(0, h, BP3) == -500
    assert score(0, h, BP4) == -1000


def test_skull_bust_gives_penalty():
    # 3+ skulls with bateau pirate → skull bust → −penalty (same as sword failure)
    h = held((Face.MONKEY, 5))
    assert score(3, h, BP2) == -300
    assert score(3, h, BP3) == -500
    assert score(3, h, BP4) == -1000


def test_skull_bust_gives_zero_without_bateau_pirate():
    h = held((Face.SWORD, 5))
    assert score(3, h, DEFAULT_CONFIG) == 0


# ---------------------------------------------------------------------------
# DP: solutions are solvable; negative stop values handled
# ---------------------------------------------------------------------------

def test_dp_solves_all_bateau_pirate():
    for config in (BP2, BP3, BP4):
        sol = get_solution(config)
        assert len(sol.states) > 0


def test_v_at_least_stop_value():
    # V must be ≥ stop_values: you can always choose to stop
    for config in (BP2, BP3, BP4):
        sol = get_solution(config)
        assert (sol.V >= sol.stop_values - 1e-9).all()


def test_ev_is_finite_and_computable():
    # Just verify all three variants produce finite, non-trivial EV values
    for config in (BP2, BP3, BP4):
        ev = turn_ev(config)
        assert -1000 < ev < 10_000


def test_penalty_states_have_negative_stop_value():
    # A state with 0 swords under BP4 should have stop_value = -1000
    sol = get_solution(BP4)
    state = State(0, held((Face.MONKEY, 8)))
    idx = sol.state_to_idx[state]
    assert sol.stop_values[idx] == -1000


def test_v_better_than_penalty_when_reroll_possible():
    # From a state with 0 swords (full board of monkeys), V > stop_value because
    # the player can reroll dice to chase 4 swords rather than take -1000.
    sol = get_solution(BP4)
    # Valid BP4 state: n_skulls=0 + held=8 monkeys = total_dice=8
    state = State(0, held((Face.MONKEY, 8)))
    idx = sol.state_to_idx[state]
    assert sol.stop_values[idx] == -1000
    assert sol.V[idx] > -1000
