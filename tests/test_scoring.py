import pytest
from solver.model import Face, NUM_FACES
from solver.scoring import score


def held(*pairs):
    """Build a held tuple from (Face, count) pairs."""
    counts = [0] * NUM_FACES
    for face, count in pairs:
        counts[face] = count
    return tuple(counts)


def test_three_skulls_returns_zero():
    assert score(3, held()) == 0


def test_stop_with_no_dice():
    assert score(0, held()) == 0


def test_combo_3_swords():
    assert score(0, held((Face.SWORD, 3))) == 100


def test_combo_5_swords():
    assert score(0, held((Face.SWORD, 5))) == 500


def test_coin_individual_bonus():
    # 1 coin: no combo, but 100 pts individual
    assert score(0, held((Face.COIN, 1))) == 100


def test_coin_combo_plus_individual():
    # 4 coins: 200 (combo) + 400 (individual) = 600
    assert score(0, held((Face.COIN, 4))) == 600


def test_diamond_individual_bonus():
    assert score(0, held((Face.DIAMOND, 2))) == 200


def test_all_8_coins_with_full_board_bonus():
    # 8 coins: 4000 (combo) + 800 (individual) + 500 (full board) = 5300
    assert score(0, held((Face.COIN, 8))) == 5300


def test_full_board_bonus_requires_no_skulls():
    # 7 non-skull dice + 1 skull: no full-board bonus
    # 7 swords: combo = 2000, no individual bonus
    assert score(1, held((Face.SWORD, 7))) == 2000


def test_full_board_bonus_with_zero_skulls_8_dice():
    # 8 swords: 4000 combo + 500 full board
    assert score(0, held((Face.SWORD, 8))) == 4500


def test_mixed_dice_no_combo():
    # 1 sword, 1 coin, 1 diamond, 1 monkey, 1 parrot — no combos
    # coin: 100, diamond: 100
    h = held((Face.SWORD, 1), (Face.COIN, 1), (Face.DIAMOND, 1),
              (Face.MONKEY, 1), (Face.PARROT, 1))
    assert score(0, h) == 200


def test_full_board_bonus_requires_all_dice_to_contribute():
    # 2 swords, 4 diamonds, 2 monkeys: swords (2) and monkeys (2) don't contribute → no bonus
    h = held((Face.SWORD, 2), (Face.DIAMOND, 4), (Face.MONKEY, 2))
    s = score(0, h)
    # 4 diamonds: combo 200 + individual 400 = 600. No bonus.
    assert s == 600


def test_full_board_bonus_single_non_scoring_die_forfeits():
    # 1 sword alone never contributes — should forfeit the bonus
    h = held((Face.SWORD, 1), (Face.COIN, 7))
    s = score(0, h)
    # 7 coins: combo 2000 + individual 700 = 2700. No bonus.
    assert s == 2700


def test_full_board_bonus_two_non_scoring_dice_forfeits():
    # 2 parrots + 6 swords: parrots (2) don't contribute
    h = held((Face.PARROT, 2), (Face.SWORD, 6))
    s = score(0, h)
    # 6 swords: 1000. No bonus.
    assert s == 1000


def test_full_board_bonus_all_in_combos():
    # 3 swords + 5 coins: both groups form combos → bonus applies
    h = held((Face.SWORD, 3), (Face.COIN, 5))
    s = score(0, h)
    # 3 swords: 100. 5 coins: combo 500 + individual 500 = 1000. Bonus: 500. Total: 1600.
    assert s == 1600


def test_full_board_bonus_coins_and_diamonds_always_contribute():
    # 4 coins + 4 diamonds: all dice are coins/diamonds → bonus applies
    h = held((Face.COIN, 4), (Face.DIAMOND, 4))
    s = score(0, h)
    # 4 coins: 200 + 400 = 600. 4 diamonds: 200 + 400 = 600. Bonus: 500. Total: 1700.
    assert s == 1700


def test_full_board_bonus_single_coin_contributes():
    # 1 coin + 7 swords: coin contributes (individual bonus), swords form combo → bonus applies
    h = held((Face.COIN, 1), (Face.SWORD, 7))
    s = score(0, h)
    # 7 swords: 2000. 1 coin: 100. Bonus: 500. Total: 2600.
    assert s == 2600


def test_worked_example_from_rules():
    # Final dice: 4 coins, 1 diamond, 1 skull, + 2 from somewhere (but card doubles — skip card)
    # Without the Pirate card doubling: 4 coins + 1 diamond, 1 skull
    # 4 coins: 200 (combo) + 400 (individual) = 600
    # 1 diamond: 100 (individual)
    # Total: 700
    h = held((Face.COIN, 4), (Face.DIAMOND, 1))
    assert score(1, h) == 700
