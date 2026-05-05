"""Tests for the After the Storm card (French variant):
one reroll only, coins+diamonds doubled, skull island disabled, no reroll on bust."""
import pytest
from solver.model import Face, NUM_FACES, State, CARD_CONFIGS, DEFAULT_CONFIG
from solver.scoring import score
from solver.dp import get_solution
from solver.report import turn_ev

STORM = CARD_CONFIGS["storm"]


def held(*pairs):
    counts = [0] * NUM_FACES
    for face, count in pairs:
        counts[face] = count
    return tuple(counts)


# ---------------------------------------------------------------------------
# Scoring: only coins and diamonds, doubled
# ---------------------------------------------------------------------------

def test_coins_score_doubled():
    h = held((Face.COIN, 3))
    # 3-of-a-kind combo (100) + 3 individual (300) = 400, doubled → 800
    assert score(0, h, STORM) == 800


def test_diamonds_score_doubled():
    h = held((Face.DIAMOND, 4))
    # 4-of-a-kind combo (200) + 4 individual (400) = 600, doubled → 1200
    assert score(0, h, STORM) == 1200


def test_coins_and_diamonds_combined():
    h = held((Face.COIN, 2), (Face.DIAMOND, 2))
    # No combo for either (< 3). Individual: (2+2)*100 = 400, doubled → 800
    assert score(0, h, STORM) == 800


def test_swords_score_zero():
    h = held((Face.SWORD, 5))
    assert score(0, h, STORM) == 0


def test_monkeys_score_zero():
    h = held((Face.MONKEY, 8))
    assert score(0, h, STORM) == 0


def test_parrots_score_zero():
    h = held((Face.PARROT, 6))
    assert score(0, h, STORM) == 0


def test_mixed_only_coins_diamonds_count():
    # 3 coins + 3 swords + 2 monkeys — only coins score
    h = held((Face.COIN, 3), (Face.SWORD, 3), (Face.MONKEY, 2))
    coin_score = (100 + 3 * 100) * 2  # combo + individual, doubled = 800
    assert score(0, h, STORM) == coin_score


def test_full_chest_bonus_with_all_coins():
    # 8 coins: all dice are coins → full chest applies.
    # 8-of-a-kind (4000) + 8×100 (800) + full chest (500) = 5300, doubled → 10600.
    h = held((Face.COIN, 8))
    assert score(0, h, STORM) == (4000 + 800 + 500) * 2  # 10600

def test_no_full_chest_bonus_with_non_contributing_dice():
    # 5 diamonds + 3 swords: swords don't contribute under storm rules → no full chest.
    # 5-of-a-kind (500) + 5×100 (500) = 1000, doubled → 2000.
    h = held((Face.DIAMOND, 5), (Face.SWORD, 3))
    assert score(0, h, STORM) == (500 + 500) * 2  # 2000


def test_zero_coins_zero_diamonds():
    h = held((Face.SWORD, 4), (Face.PARROT, 4))
    assert score(0, h, STORM) == 0


# ---------------------------------------------------------------------------
# Scoring: bust (3+ skulls) → always 0
# ---------------------------------------------------------------------------

def test_bust_gives_zero():
    h = held((Face.COIN, 5))
    assert score(3, h, STORM) == 0


def test_bust_with_coins_and_diamonds_zero():
    h = held((Face.COIN, 3), (Face.DIAMOND, 2))
    assert score(3, h, STORM) == 0
    assert score(4, h, STORM) == 0


# ---------------------------------------------------------------------------
# DP: solver structure
# ---------------------------------------------------------------------------

def test_dp_solves():
    sol = get_solution(STORM)
    assert len(sol.states) > 0


def test_state_count_doubled_vs_default():
    # one_reroll_only doubles the state space (reroll_used=False/True variants)
    from solver.dp import get_solution as gs
    sol_storm = gs(STORM)
    sol_default = gs(DEFAULT_CONFIG)
    assert len(sol_storm.states) == 2 * len(sol_default.states)


def test_v_at_least_stop_value():
    sol = get_solution(STORM)
    assert (sol.V >= sol.stop_values - 1e-9).all()


def test_ev_is_finite_and_positive():
    ev = turn_ev(STORM)
    assert 0 < ev < 10_000


def test_reroll_used_states_v_equals_stop():
    # States where reroll_used=True have no actions; V must equal stop_value exactly.
    sol = get_solution(STORM)
    for state, idx in sol.state_to_idx.items():
        if state.reroll_used:
            assert abs(sol.V[idx] - sol.stop_values[idx]) < 1e-9


def test_reroll_available_improves_v():
    # From the initial state with a few non-optimal dice, rerolling should be worth more
    # than stopping — i.e. V > stop_value for at least some reroll_used=False states.
    sol = get_solution(STORM)
    improved = any(
        sol.V[sol.state_to_idx[s]] > sol.stop_values[sol.state_to_idx[s]] + 1e-9
        for s in sol.states if not s.reroll_used
    )
    assert improved
