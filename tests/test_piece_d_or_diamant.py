"""Tests for Pièce d'or and Diamant cards (pre-set coin/diamond extra die)."""
import pytest
from solver.model import Face, NUM_FACES, NUM_DICE, State, TurnConfig, CARD_CONFIGS, DEFAULT_CONFIG, WIN_SCORE
from solver.scoring import score
from solver.actions import valid_actions
from solver.dp import get_solution
from solver.report import dice_to_state

COIN_CARD = CARD_CONFIGS["piece-d-or"]
DIAMOND_CARD = CARD_CONFIGS["diamant"]


def held(*pairs):
    counts = [0] * NUM_FACES
    for face, count in pairs:
        counts[face] = count
    return tuple(counts)


# ---------------------------------------------------------------------------
# TurnConfig sanity
# ---------------------------------------------------------------------------

def test_card_configs_exist():
    assert "piece-d-or" in CARD_CONFIGS
    assert "diamant" in CARD_CONFIGS


def test_piece_d_or_config():
    assert COIN_CARD.total_dice == 9
    assert COIN_CARD.initial_n_skulls == 0
    assert COIN_CARD.initial_held[Face.COIN] == 1
    assert sum(COIN_CARD.initial_held) == 1


def test_diamant_config():
    assert DIAMOND_CARD.total_dice == 9
    assert DIAMOND_CARD.initial_n_skulls == 0
    assert DIAMOND_CARD.initial_held[Face.DIAMOND] == 1
    assert sum(DIAMOND_CARD.initial_held) == 1


# ---------------------------------------------------------------------------
# dice_to_state: card die merged into initial held
# ---------------------------------------------------------------------------

def test_dice_to_state_piece_d_or_no_skulls():
    # 8 swords rolled → held has 8 swords + 1 card coin
    dice = [Face.SWORD] * 8
    s = dice_to_state(dice, COIN_CARD)
    assert s.n_skulls == 0
    assert s.held[Face.SWORD] == 8
    assert s.held[Face.COIN] == 1
    assert s.n_skulls + sum(s.held) == COIN_CARD.total_dice


def test_dice_to_state_diamant_with_rolled_skull():
    # 1 skull + 7 swords rolled → 1 skull, 7 swords, 1 card diamond
    dice = [Face.SKULL] + [Face.SWORD] * 7
    s = dice_to_state(dice, DIAMOND_CARD)
    assert s.n_skulls == 1
    assert s.held[Face.SWORD] == 7
    assert s.held[Face.DIAMOND] == 1
    assert s.n_skulls + sum(s.held) == DIAMOND_CARD.total_dice


def test_card_coin_counts_in_combo():
    # 2 rolled coins + 1 card coin = 3 coins → combo of 3
    # Also 6 swords (combo) + 3 coins (combo+individual) = all 9 dice contribute → +500 bonus
    dice = [Face.COIN, Face.COIN] + [Face.SWORD] * 6
    s = dice_to_state(dice, COIN_CARD)
    assert s.held[Face.COIN] == 3
    # 6 swords: 1000. 3 coins: combo 100 + individual 300 = 400. Full board: +500.
    assert score(s.n_skulls, s.held, COIN_CARD) == 1900


def test_card_diamond_counts_in_combo():
    # 2 rolled diamonds + 1 card diamond = 3 diamonds → combo of 3
    # Also 6 swords (combo) + 3 diamonds (combo+individual) = all 9 dice contribute → +500 bonus
    dice = [Face.DIAMOND, Face.DIAMOND] + [Face.SWORD] * 6
    s = dice_to_state(dice, DIAMOND_CARD)
    assert s.held[Face.DIAMOND] == 3
    # 6 swords: 1000. 3 diamonds: combo 100 + individual 300 = 400. Full board: +500.
    assert score(s.n_skulls, s.held, DIAMOND_CARD) == 1900


# ---------------------------------------------------------------------------
# Scoring: full-board bonus with 9 dice
# ---------------------------------------------------------------------------

def test_full_board_bonus_9_coins():
    # 8 rolled coins + 1 card coin = 9 identical → Magie pirate instant win
    h = held((Face.COIN, 9))
    s = score(0, h, COIN_CARD)
    assert s == WIN_SCORE


def test_full_board_bonus_requires_all_9_to_contribute_coin_card():
    # 1 card coin + 5 rolled coins + 3 rolled swords: swords (3) form combo → all contribute
    h = held((Face.COIN, 6), (Face.SWORD, 3))
    s = score(0, h, COIN_CARD)
    # 6 coins: combo 1000 + individual 600. 3 swords: combo 100. Bonus 500.
    assert s == 1000 + 600 + 100 + 500


def test_full_board_bonus_forfeited_with_non_scoring_dice_coin_card():
    # 1 card coin + 2 rolled coins + 6 rolled swords (2 swords don't form combo,
    # but 6 swords do). Wait: 6 swords is a valid combo. Let's use 2 swords instead.
    # 1 card coin + 2 rolled coins + 5 rolled swords + 1 monkey:
    # swords (5) form combo, coin (3) forms combo, monkey (1) doesn't → no bonus
    h = held((Face.COIN, 3), (Face.SWORD, 5), (Face.MONKEY, 1))
    s = score(0, h, COIN_CARD)
    # 3 coins: 100 + 300. 5 swords: 500. No bonus.
    assert s == 100 + 300 + 500


def test_full_board_bonus_9_all_scoring_diamond_card():
    # 8 rolled swords + 1 card diamond: 8 swords (combo) + 1 diamond (individual) → all contribute
    h = held((Face.SWORD, 8), (Face.DIAMOND, 1))
    s = score(0, h, DIAMOND_CARD)
    # 8 swords: 4000. 1 diamond: 100. Full board: +500.
    assert s == 4000 + 100 + 500


# ---------------------------------------------------------------------------
# State invariant
# ---------------------------------------------------------------------------

def test_all_states_invariant_coin_card():
    sol = get_solution(COIN_CARD)
    for s in sol.states:
        assert s.n_skulls + sum(s.held) == COIN_CARD.total_dice


def test_all_states_invariant_diamond_card():
    sol = get_solution(DIAMOND_CARD)
    for s in sol.states:
        assert s.n_skulls + sum(s.held) == DIAMOND_CARD.total_dice


# ---------------------------------------------------------------------------
# EV: coin/diamond card should increase EV vs no card
# ---------------------------------------------------------------------------

def test_ev_higher_with_coin_card():
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

    assert turn_ev(COIN_CARD) > turn_ev(DEFAULT_CONFIG)
    assert turn_ev(DIAMOND_CARD) > turn_ev(DEFAULT_CONFIG)


def test_coin_and_diamond_cards_have_equal_ev():
    # Coins and diamonds are symmetric (same combo scores, same individual bonus)
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

    assert abs(turn_ev(COIN_CARD) - turn_ev(DIAMOND_CARD)) < 1e-6
