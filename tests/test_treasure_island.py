"""Tests for the Treasure Island card (bust-score modifier)."""
import pytest
import numpy as np
from solver.model import Face, NUM_FACES, TurnConfig, CARD_CONFIGS, DEFAULT_CONFIG
from solver.scoring import score
from solver.dp import get_solution
from solver.report import turn_ev

TI = CARD_CONFIGS["treasure-island"]


def held(*pairs):
    counts = [0] * NUM_FACES
    for face, count in pairs:
        counts[face] = count
    return tuple(counts)


# ---------------------------------------------------------------------------
# Scoring: bust branch
# ---------------------------------------------------------------------------

def test_default_bust_is_zero():
    assert score(3, held((Face.COIN, 4)), DEFAULT_CONFIG) == 0


def test_default_bust_with_held_is_always_zero():
    assert score(3, held((Face.SWORD, 5)), DEFAULT_CONFIG) == 0


def test_treasure_island_bust_scores_held_coins():
    # 4 coins: combo(4)=200 + 4×100 individual = 600
    assert score(3, held((Face.COIN, 4)), TI) == 600


def test_treasure_island_bust_scores_held_swords():
    # 3 swords: combo(3) = 100
    assert score(3, held((Face.SWORD, 3)), TI) == 100


def test_treasure_island_bust_with_no_held_is_zero():
    assert score(3, held(), TI) == 0


def test_treasure_island_bust_partial_combo_no_score():
    # 2 monkeys: no combo (< 3), no individual bonus → 0
    assert score(3, held((Face.MONKEY, 2)), TI) == 0


def test_treasure_island_non_bust_unchanged_stop():
    # Stopping (n_skulls=0) should give identical results for TI and default
    h = held((Face.COIN, 3), (Face.SWORD, 3))
    assert score(0, h, TI) == score(0, h, DEFAULT_CONFIG)


def test_treasure_island_non_bust_one_skull_unchanged():
    h = held((Face.DIAMOND, 4))
    assert score(1, h, TI) == score(1, h, DEFAULT_CONFIG)


def test_treasure_island_bust_with_multiplier():
    # TI + score_multiplier=2: bust score should also be multiplied
    ti_x2 = TurnConfig(treasure_island=True, score_multiplier=2)
    # 3 swords = combo(3)=100, ×2 = 200
    assert score(3, held((Face.SWORD, 3)), ti_x2) == 200


def test_treasure_island_bust_no_full_chest_bonus():
    # Even if all 8 non-skull dice are held, full-chest bonus doesn't apply on bust
    # because the player has 3+ skulls (more than 8 dice total is impossible in 8-die
    # game, but we can test with a hypothetical: all non-skull slots filled)
    # Use 5 coins + 3 swords (8 total) but bust → no +500 full chest
    h = held((Face.COIN, 5), (Face.SWORD, 3))
    ti_score = score(3, h, TI)
    # combo(5 coins)=500, 5×100=500, combo(3 swords)=100 → 1100; no +500 since bust
    assert ti_score == 1100


def test_treasure_island_bust_pirate_ship_penalty_still_applies():
    # With TI + pirate-ship, busting with swords < required still gives penalty
    ti_ship = TurnConfig(treasure_island=True, required_swords=3, sword_bonus=500, sword_penalty=500)
    # Only 2 swords held: requirement not met → -500 penalty
    assert score(3, held((Face.SWORD, 2), (Face.COIN, 4)), ti_ship) == -500


def test_treasure_island_bust_pirate_ship_met():
    # With TI + pirate-ship, busting with swords >= required scores normally
    ti_ship = TurnConfig(treasure_island=True, required_swords=2, sword_bonus=300, sword_penalty=300)
    # 3 swords (>= 2): combo(3)=100 + sword_bonus=300 = 400
    assert score(3, held((Face.SWORD, 3)), ti_ship) == 400


# ---------------------------------------------------------------------------
# State space: TI must NOT inflate the state count
# ---------------------------------------------------------------------------

def test_treasure_island_state_space_unchanged():
    sol_default = get_solution(DEFAULT_CONFIG)
    sol_ti = get_solution(TI)
    assert len(sol_ti.states) == len(sol_default.states)


# ---------------------------------------------------------------------------
# DP / EV ordering
# ---------------------------------------------------------------------------

def test_treasure_island_v_dominates_default():
    """V[TI] >= V[default] for every state (bust shield never hurts)."""
    sol_default = get_solution(DEFAULT_CONFIG)
    sol_ti = get_solution(TI)
    # Both solutions share the same state ordering (same _all_states)
    assert np.all(sol_ti.V >= sol_default.V - 1e-9)


def test_treasure_island_strictly_improves_some_states():
    """TI must strictly improve V for at least some states (non-trivial benefit)."""
    sol_default = get_solution(DEFAULT_CONFIG)
    sol_ti = get_solution(TI)
    delta = sol_ti.V - sol_default.V
    assert float(np.max(delta)) > 0.0, "TI should strictly improve at least one state's EV"


def test_turn_ev_treasure_island_higher_than_default():
    """Whole-turn EV with Treasure Island must be strictly better than no card."""
    assert turn_ev(TI) > turn_ev(DEFAULT_CONFIG)


# ---------------------------------------------------------------------------
# Catalog / registration
# ---------------------------------------------------------------------------

def test_treasure_island_in_card_configs():
    assert "treasure-island" in CARD_CONFIGS


def test_treasure_island_config_has_flag():
    assert CARD_CONFIGS["treasure-island"].treasure_island is True


def test_treasure_island_config_standard_dice():
    # No extra dice, no pre-locked skulls
    assert CARD_CONFIGS["treasure-island"].total_dice == 8
    assert CARD_CONFIGS["treasure-island"].initial_n_skulls == 0
