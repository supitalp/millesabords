"""Tests for the Treasure Island card (bust-score modifier)."""
import pytest
import numpy as np
from solver.model import Face, NUM_FACES, TurnConfig, CARD_CONFIGS, DEFAULT_CONFIG, State
from solver.scoring import score
from solver.dp import get_solution, _precompute, _all_states, _add_outcome
from solver.report import turn_ev
from solver.roll import roll_outcomes

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
# DP transition: bust must use kept dice only, not post-roll held
# ---------------------------------------------------------------------------

def test_treasure_island_bust_transition_uses_kept_not_post_roll():
    """
    Regression: when the fatal reroll busts with TI, the bust score must count
    only the dice the player had placed on the island (kept) — not the non-skull
    faces that came out of that same reroll.

    Scenario from bug report:
      State: 2 skulls, held = coin×2 + parrot×2 + sword×1 + diamond×1
      Player keeps coin×2 + parrot×2 on the island (score = 200) and rerolls 2 dice.
      Some bust outcomes produce an extra coin or diamond alongside the fatal skull.
      Correct bust score = 200 (island only).
      Buggy bust score = higher (200 + extra coins/diamonds from the fatal roll).
    """
    states = _all_states(TI)
    state_to_idx = {s: i for i, s in enumerate(states)}

    hand   = held((Face.COIN, 2), (Face.PARROT, 2), (Face.SWORD, 1), (Face.DIAMOND, 1))
    island = held((Face.COIN, 2), (Face.PARROT, 2))  # dice kept on the island
    s = State(2, hand, False)
    s_idx = state_to_idx[s]

    n_reroll = TI.total_dice - 2 - sum(island)  # 8 - 2 skulls - 4 kept = 2

    island_score = score(3, island, TI)  # 2 coins × 100 = 200
    assert island_score == 200, "test setup error"

    # Confirm that some bust outcomes would inflate the score under the buggy formula.
    any_inflated = any(
        score(3, _add_outcome(island, outcome), TI) != island_score
        for outcome, _ in roll_outcomes(n_reroll)
        if 2 + outcome[Face.SKULL] >= 3
    )
    assert any_inflated, "test is vacuous: no bust outcome differs between fixed and buggy"

    # Correct bust_ev for the action that keeps exactly the island dice.
    expected_bust_ev = sum(
        prob * island_score
        for outcome, prob in roll_outcomes(n_reroll)
        if 2 + outcome[Face.SKULL] >= 3
    )

    # The precomputed actions must include one with bust_ev matching the correct formula.
    actions = _precompute(states, state_to_idx, TI)
    state_actions = [a for a in actions if a.state_idx == s_idx]
    assert state_actions, "no actions found for this state"

    assert any(
        abs(a.bust_ev - expected_bust_ev) < 1e-9 for a in state_actions
    ), (
        f"No action has the correct bust_ev ({expected_bust_ev:.6f}). "
        f"Got: {sorted(round(a.bust_ev, 6) for a in state_actions)}"
    )


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
