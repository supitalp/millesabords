"""Tests for Tête de Mort card (1 and 2 pre-locked skulls)."""
import pytest
from solver.model import Face, NUM_FACES, NUM_DICE, State, TurnConfig, CARD_CONFIGS, DEFAULT_CONFIG
from solver.scoring import score
from solver.actions import valid_actions
from solver.dp import get_solution
from solver.report import dice_to_state


CARD_1 = CARD_CONFIGS["tete-de-mort-1"]
CARD_2 = CARD_CONFIGS["tete-de-mort-2"]


def held(*pairs):
    counts = [0] * NUM_FACES
    for face, count in pairs:
        counts[face] = count
    return tuple(counts)


# ---------------------------------------------------------------------------
# TurnConfig sanity
# ---------------------------------------------------------------------------

def test_card_configs_exist():
    assert "tete-de-mort-1" in CARD_CONFIGS
    assert "tete-de-mort-2" in CARD_CONFIGS


def test_tete_de_mort_1_config():
    assert CARD_1.total_dice == 9
    assert CARD_1.initial_n_skulls == 1


def test_tete_de_mort_2_config():
    assert CARD_2.total_dice == 10
    assert CARD_2.initial_n_skulls == 2


# ---------------------------------------------------------------------------
# dice_to_state: card skulls are added on top of rolled skulls
# ---------------------------------------------------------------------------

def test_dice_to_state_no_card():
    dice = [Face.SKULL, Face.SWORD, Face.SWORD, Face.COIN,
            Face.COIN, Face.DIAMOND, Face.MONKEY, Face.PARROT]
    s = dice_to_state(dice, DEFAULT_CONFIG)
    assert s.n_skulls == 1
    assert sum(s.held) == 7


def test_dice_to_state_tete_de_mort_1():
    # Roll with 0 skulls → total skulls = 0 + 1 card = 1
    dice = [Face.SWORD] * 8
    s = dice_to_state(dice, CARD_1)
    assert s.n_skulls == 1
    assert s.held[Face.SWORD] == 8
    assert sum(s.held) == 8
    assert s.n_skulls + sum(s.held) == CARD_1.total_dice


def test_dice_to_state_tete_de_mort_1_with_rolled_skull():
    # Roll with 1 skull → total = 1 + 1 card = 2
    dice = [Face.SKULL] + [Face.SWORD] * 7
    s = dice_to_state(dice, CARD_1)
    assert s.n_skulls == 2
    assert sum(s.held) == 7
    assert s.n_skulls + sum(s.held) == CARD_1.total_dice


def test_dice_to_state_tete_de_mort_2():
    # Roll with 0 skulls → total = 0 + 2 card = 2
    dice = [Face.COIN] * 8
    s = dice_to_state(dice, CARD_2)
    assert s.n_skulls == 2
    assert s.held[Face.COIN] == 8
    assert s.n_skulls + sum(s.held) == CARD_2.total_dice


def test_dice_to_state_tete_de_mort_2_one_rolled_skull_means_loss():
    # Roll 1 skull → 1 + 2 card = 3 → bust
    dice = [Face.SKULL] + [Face.SWORD] * 7
    s = dice_to_state(dice, CARD_2)
    assert s.n_skulls == 3


# ---------------------------------------------------------------------------
# Scoring: full-board bonus impossible with pre-locked skulls
# ---------------------------------------------------------------------------

def test_no_full_board_bonus_with_card_skull():
    # 8 swords + 1 card skull = 9 total, but n_skulls=1, so no bonus
    h = held((Face.SWORD, 8))
    assert score(1, h, CARD_1) == 4000  # combo only, no +500


def test_full_board_bonus_still_works_no_card():
    h = held((Face.SWORD, 8))
    assert score(0, h, DEFAULT_CONFIG) == 4500  # 4000 + 500 bonus


# ---------------------------------------------------------------------------
# State invariant: n_skulls + sum(held) == total_dice for all states
# ---------------------------------------------------------------------------

def test_all_states_invariant_card_1():
    sol = get_solution(CARD_1)
    for s in sol.states:
        assert s.n_skulls + sum(s.held) == CARD_1.total_dice


def test_all_states_invariant_card_2():
    sol = get_solution(CARD_2)
    for s in sol.states:
        assert s.n_skulls + sum(s.held) == CARD_2.total_dice


# ---------------------------------------------------------------------------
# State counts: total_dice=9 → more states than base game
# ---------------------------------------------------------------------------

def test_state_count_card_1():
    from itertools import combinations_with_replacement
    total = 0
    for n_skulls in range(3):
        n_held = CARD_1.total_dice - n_skulls
        if n_held >= 0:
            total += sum(1 for _ in combinations_with_replacement(range(1, NUM_FACES), n_held))
    sol = get_solution(CARD_1)
    assert len(sol.states) == total


# ---------------------------------------------------------------------------
# DP correctness: EV with card skulls should be lower than base game
# ---------------------------------------------------------------------------

def test_ev_lower_with_one_card_skull():
    """Starting with a skull already locked reduces expected turn score."""
    from solver.roll import roll_outcomes

    def turn_ev(config):
        sol = get_solution(config)
        ev = 0.0
        for outcome, prob in roll_outcomes(NUM_DICE):
            n_skulls = config.initial_n_skulls + outcome[Face.SKULL]
            if n_skulls >= 3:
                continue
            h = list(config.initial_held)
            for face in range(1, NUM_FACES):
                h[face] += outcome[face]
            s = State(n_skulls, tuple(h))
            ev += prob * sol.V[sol.state_to_idx[s]]
        return ev

    ev_base = turn_ev(DEFAULT_CONFIG)
    ev_card1 = turn_ev(CARD_1)
    ev_card2 = turn_ev(CARD_2)

    assert ev_card1 < ev_base, "1 pre-locked skull should reduce EV"
    assert ev_card2 < ev_card1, "2 pre-locked skulls should reduce EV further"


def test_v_geq_stop_score_card_1():
    sol = get_solution(CARD_1)
    from solver.scoring import score as _score
    for s in sol.states:
        assert sol.V[sol.state_to_idx[s]] >= _score(s.n_skulls, s.held, CARD_1)


def test_v_geq_stop_score_card_2():
    sol = get_solution(CARD_2)
    from solver.scoring import score as _score
    for s in sol.states:
        assert sol.V[sol.state_to_idx[s]] >= _score(s.n_skulls, s.held, CARD_2)


# ---------------------------------------------------------------------------
# Action constraints still hold under card configs
# ---------------------------------------------------------------------------

def test_reroll_1_never_valid_card_1():
    sol = get_solution(CARD_1)
    for s in sol.states:
        for kept in valid_actions(s, CARD_1):
            n_reroll = CARD_1.total_dice - s.n_skulls - sum(kept)
            assert n_reroll != 1


def test_with_2_card_skulls_any_rolled_skull_is_fatal():
    # State with 2 skulls (both from card) and 8 swords
    h = held((Face.SWORD, 8))
    s = State(2, h)
    assert s.n_skulls + sum(s.held) == CARD_2.total_dice
    # All actions rerolling ≥1 die risk instant loss
    for kept in valid_actions(s, CARD_2):
        n_reroll = CARD_2.total_dice - s.n_skulls - sum(kept)
        if n_reroll > 0:
            # P(lose) > 0 for any reroll when at 2 skulls
            assert n_reroll >= 2  # rule still holds: no rerolling exactly 1
