"""Tests for the Pirate card (all points doubled)."""
from solver.model import Face, NUM_FACES, State, CARD_CONFIGS, DEFAULT_CONFIG
from solver.scoring import score
from solver.dp import get_solution

PIRATE = CARD_CONFIGS["pirate"]


def held(*pairs):
    counts = [0] * NUM_FACES
    for face, count in pairs:
        counts[face] = count
    return tuple(counts)


# ---------------------------------------------------------------------------
# Scoring: all points doubled
# ---------------------------------------------------------------------------

def test_combo_doubled():
    # n_skulls=1 to avoid full board (requires n_skulls==0)
    h = held((Face.SWORD, 3), (Face.MONKEY, 4))   # sum=7 = total_dice - n_skulls(1)
    assert score(1, h, DEFAULT_CONFIG) == 300   # swords=100, monkeys=200
    assert score(1, h, PIRATE) == 600


def test_coin_individual_and_combo_doubled():
    # n_skulls=1: 4 coins + 3 swords → sum=7
    h = held((Face.COIN, 4), (Face.SWORD, 3))
    assert score(1, h, DEFAULT_CONFIG) == 700   # coins: 200+400, swords: 100
    assert score(1, h, PIRATE) == 1400


def test_full_board_bonus_doubled():
    # 3 swords + 5 monkeys = full board (all ≥ 3): 100+500+500 = 1100
    h = held((Face.SWORD, 3), (Face.MONKEY, 5))
    assert score(0, h, DEFAULT_CONFIG) == 1100
    assert score(0, h, PIRATE) == 2200


def test_zero_score_not_doubled():
    # 3 skulls → always 0 regardless of multiplier
    assert score(3, held((Face.SWORD, 5)), PIRATE) == 0


def test_win_score_not_doubled():
    # 9 identical → WIN_SCORE sentinel, not subject to multiplier
    from solver.model import WIN_SCORE
    h = held((Face.SWORD, 9))
    assert score(0, h, PIRATE) == WIN_SCORE


# ---------------------------------------------------------------------------
# DP: pirate solution is correctly solved
# ---------------------------------------------------------------------------

def test_dp_solves_pirate():
    sol = get_solution(PIRATE)
    assert len(sol.states) > 0
    assert (sol.V >= 0).all()


def test_v_at_least_stop_value_pirate():
    sol = get_solution(PIRATE)
    assert (sol.V >= sol.stop_values).all()


def test_pirate_ev_is_double_base():
    """Turn EV with Pirate should be exactly 2× the base game EV."""
    from solver.report import turn_ev
    base_ev = turn_ev(DEFAULT_CONFIG)
    pirate_ev = turn_ev(PIRATE)
    assert abs(pirate_ev - 2 * base_ev) < 1e-6
