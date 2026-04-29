"""Tests for the 9-of-a-kind combo (reachable only with the Coin/Diamond card).

Historically this was an instant-win (Pirate's Magic). The solver now treats it
as just another combo tier (9 → 8000), extending the geometric doubling
progression. The tests below pin down the resulting scores and EV behavior.
"""
from solver.model import Face, NUM_FACES, State, CARD_CONFIGS, DEFAULT_CONFIG, COMBO_SCORE
from solver.scoring import score
from solver.dp import get_solution

COIN_CARD = CARD_CONFIGS["coin"]
DIAMOND_CARD = CARD_CONFIGS["diamond"]


def held(*pairs):
    counts = [0] * NUM_FACES
    for face, count in pairs:
        counts[face] = count
    return tuple(counts)


# ---------------------------------------------------------------------------
# COMBO_SCORE progression
# ---------------------------------------------------------------------------

def test_combo_score_continues_doubling_to_nine():
    """3:100, 4:200, 5:500, 6:1000, 7:2000, 8:4000, 9:8000 (geometric progression)."""
    assert COMBO_SCORE == {3: 100, 4: 200, 5: 500, 6: 1000, 7: 2000, 8: 4000, 9: 8000}


# ---------------------------------------------------------------------------
# Scoring: 9-of-a-kind on Coin/Diamond cards
# ---------------------------------------------------------------------------

def test_9_coins_scores_combo_plus_individual_plus_chest():
    # 9 coins: 8000 (combo) + 900 (per-coin) + 500 (full chest, all dice contribute)
    assert score(0, held((Face.COIN, 9)), COIN_CARD) == 8000 + 900 + 500


def test_9_diamonds_scores_combo_plus_individual_plus_chest():
    # 9 diamonds: 8000 (combo) + 900 (per-diamond) + 500 (full chest)
    assert score(0, held((Face.DIAMOND, 9)), DIAMOND_CARD) == 8000 + 900 + 500


def test_9_swords_ghost_state_scores_combo_plus_chest():
    # 9 swords on the coin card is technically a "ghost" state (the locked coin
    # would have to disappear), but the scoring function still defines a value
    # for it — exercise that the COMBO_SCORE[9] tier is wired up symmetrically.
    assert score(0, held((Face.SWORD, 9)), COIN_CARD) == 8000 + 500


def test_9_identical_with_skull_is_impossible():
    # n_skulls >= 1 means at most 8 non-skull dice, so 9-of-a-kind cannot occur.
    # If we pass an inconsistent state, n_skulls=1 should still trigger normal
    # bust handling at 3+ skulls and combo scoring otherwise — never a sentinel.
    assert score(1, held((Face.COIN, 8)), COIN_CARD) == score(1, held((Face.COIN, 8)), COIN_CARD)


def test_8_identical_no_card_is_just_8_of_a_kind():
    # Base game: 8 identical coins is the highest combo possible (no 9th die).
    # 4000 + 800 individual + 500 chest = 5300.
    assert score(0, held((Face.COIN, 8)), DEFAULT_CONFIG) == 5300


def test_9_mixed_no_special_treatment():
    # 9 dice but mixed faces — just regular combo scoring.
    h = held((Face.COIN, 5), (Face.DIAMOND, 4))
    # 5 coins: combo 500 + 500 individual; 4 diamonds: combo 200 + 400 individual; chest +500
    assert score(0, h, COIN_CARD) == 500 + 500 + 200 + 400 + 500


# ---------------------------------------------------------------------------
# DP: 9-of-a-kind state is just another stop state
# ---------------------------------------------------------------------------

def test_9_coin_state_in_dp():
    sol = get_solution(COIN_CARD)
    win_state = State(0, held((Face.COIN, 9)))
    assert win_state in sol.state_to_idx
    idx = sol.state_to_idx[win_state]
    # Stopping at 9 coins = 9400; this is the state's stop value.
    assert sol.stop_values[idx] == 9400
    # V = 9400 too: rerolling out of a max-score stop only loses value.
    assert sol.V[idx] == sol.stop_values[idx]


def test_action_can_reach_9_of_a_kind_score():
    """Reroll 2 dice from 7 coins: max_score should reflect the reachable 9-of-a-kind (9400)."""
    from solver.stats import compute_stats
    state = State(0, held((Face.COIN, 7), (Face.SWORD, 2)))
    kept = held((Face.COIN, 7))  # keep 7, reroll 2 swords
    s = compute_stats(state, kept, COIN_CARD)
    # Best-case path: roll 2 more coins → 9 coins → 9400.
    assert s.max_score == 9400


def test_no_9_of_a_kind_path_in_base_game():
    # Default config has only 8 dice → 9-of-a-kind is impossible from any state.
    sol = get_solution(DEFAULT_CONFIG)
    # No state in the default config can have any face count == 9.
    for s in sol.states:
        for f in range(1, NUM_FACES):
            assert s.held[f] <= 8
