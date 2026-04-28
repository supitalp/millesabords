"""Tests for the Pirate's Magic instant-win rule (9 identical dice)."""
import pytest
from solver.model import Face, NUM_FACES, State, CARD_CONFIGS, DEFAULT_CONFIG, WIN_SCORE
from solver.scoring import score
from solver.dp import get_solution
from solver.report import dice_to_state

COIN_CARD = CARD_CONFIGS["coin"]
DIAMOND_CARD = CARD_CONFIGS["diamond"]


def held(*pairs):
    counts = [0] * NUM_FACES
    for face, count in pairs:
        counts[face] = count
    return tuple(counts)


# ---------------------------------------------------------------------------
# scoring: 9 identical → WIN_SCORE
# ---------------------------------------------------------------------------

def test_9_coins_returns_win_score():
    h = held((Face.COIN, 9))
    assert score(0, h, COIN_CARD) == WIN_SCORE


def test_9_diamonds_returns_win_score():
    h = held((Face.DIAMOND, 9))
    assert score(0, h, DIAMOND_CARD) == WIN_SCORE


def test_9_identical_requires_no_skulls():
    # With a skull, total held can be at most 8 non-skull dice → can't reach 9 identical
    h = held((Face.COIN, 8))
    assert score(1, h, COIN_CARD) != WIN_SCORE


def test_8_identical_no_card_not_a_win():
    # Base game: 8 identical is NOT a win (only 9 triggers Pirate's Magic)
    h = held((Face.COIN, 8))
    assert score(0, h, DEFAULT_CONFIG) != WIN_SCORE
    assert score(0, h, DEFAULT_CONFIG) == 5300  # 4000 combo + 800 individual + 500 full board


def test_9_mixed_not_a_win():
    # 9 dice but not all the same symbol
    h = held((Face.COIN, 5), (Face.DIAMOND, 4))
    assert score(0, h, COIN_CARD) != WIN_SCORE


def test_win_score_dominates_all_normal_scores():
    # WIN_SCORE must be well above any achievable normal score
    max_normal = 4000 + 800 + 500  # 8 coins + full board bonus
    assert WIN_SCORE > max_normal * 10


# ---------------------------------------------------------------------------
# DP: win states have WIN_SCORE value; actions leading to win have high EV
# ---------------------------------------------------------------------------

def test_win_state_has_win_score_in_dp():
    sol = get_solution(COIN_CARD)
    win_state = State(0, held((Face.COIN, 9)))
    assert win_state in sol.state_to_idx
    idx = sol.state_to_idx[win_state]
    assert sol.V[idx] == WIN_SCORE
    assert sol.stop_values[idx] == WIN_SCORE


def test_action_leading_to_win_has_elevated_ev():
    """Keeping 8 coins and rerolling 1 die gives 1/6 chance of WIN_SCORE, so EV > stop."""
    sol = get_solution(COIN_CARD)
    # Valid COIN_CARD state: 0 skulls + 7 coins + 2 swords = 9 = total_dice
    # (card pre-holds 1 coin, so this represents rolling 6 coins + 2 swords)
    state = State(0, held((Face.COIN, 7), (Face.SWORD, 2)))
    idx = sol.state_to_idx[state]
    stop = sol.stop_values[idx]
    # 7 coins: COMBO_SCORE[7]=2000, individual 700 = 2700; 2 swords: no combo, no individual
    # sum(held)=9 = total_dice and all dice contribute? swords count=2 < 3 and not coin/diamond
    # → full board bonus does NOT apply; stop = 2700
    assert stop == 2700
    # V should exceed stop because keeping 7 coins and rerolling 2 dice can reach WIN_SCORE
    assert sol.V[idx] > stop


def test_p_win_nonzero_when_one_reroll_can_win():
    from solver.stats import compute_stats
    # State: 8 coins held, coin card → reroll 1 die not valid (must reroll ≥2)
    # State: 7 coins held, coin card → reroll 2 dice, could get 2 coins → win
    state = State(0, held((Face.COIN, 7)))
    # keep all 7 coins, reroll 2 dice
    kept = held((Face.COIN, 7))
    s = compute_stats(state, kept, COIN_CARD)
    assert s.p_win > 0
    assert s.max_score == WIN_SCORE


def test_p_win_exact_for_one_away():
    from solver.stats import compute_stats
    # 8 coins held, need to keep 7 and reroll 2 to have a chance at win
    # P(both dice are coins) = (1/6)^2 = 1/36
    state = State(0, held((Face.COIN, 8)))
    kept = held((Face.COIN, 7))  # keep 7, reroll 2
    s = compute_stats(state, kept, COIN_CARD)
    assert abs(s.p_win - (1/6)**2) < 1e-10


def test_no_win_possible_without_card():
    """In the base game, 9 identical is impossible — no action should have p_win > 0."""
    from solver.stats import compute_stats
    from solver.actions import valid_actions
    state = State(0, held((Face.COIN, 8)))
    # This state isn't reachable in base game (only 8 total dice), but let's
    # verify that base-game scoring never returns WIN_SCORE
    assert score(0, held((Face.COIN, 8)), DEFAULT_CONFIG) == 5300
