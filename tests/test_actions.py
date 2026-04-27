import pytest
from solver.model import Face, NUM_FACES, NUM_DICE, State
from solver.actions import valid_actions


def held(*pairs):
    counts = [0] * NUM_FACES
    for face, count in pairs:
        counts[face] = count
    return tuple(counts)


def valid_state(n_skulls, *pairs):
    """Build a State satisfying the invariant n_skulls + sum(held) == NUM_DICE."""
    h = held(*pairs)
    assert n_skulls + sum(h) == NUM_DICE, "Invalid state: dice don't add up to 8"
    return State(n_skulls=n_skulls, held=h)


def test_stop_always_valid():
    s = valid_state(0, (Face.SWORD, 3), (Face.COIN, 3), (Face.MONKEY, 2))
    actions = valid_actions(s)
    assert s.held in actions


def test_reroll_1_die_never_valid():
    # Any action must have n_reroll != 1
    s = valid_state(0, (Face.SWORD, 8))
    for kept in valid_actions(s):
        n_reroll = NUM_DICE - s.n_skulls - sum(kept)
        assert n_reroll != 1


def test_reroll_all_dice_never_valid_with_zero_skulls():
    # With 0 skulls, keeping 0 dice would violate "must keep >= 1 die"
    s = valid_state(0, (Face.SWORD, 8))
    empty = tuple([0] * NUM_FACES)
    assert empty not in valid_actions(s)


def test_2_skulls_can_reroll_all_non_skull():
    # 2 skulls count as the mandatory kept die, so all 6 non-skull dice can be rerolled
    s = valid_state(2, (Face.SWORD, 6))
    empty = tuple([0] * NUM_FACES)
    assert empty in valid_actions(s)


def test_1_skull_can_reroll_all_non_skull():
    # 1 skull counts as kept die; can reroll all 7 non-skull dice
    s = valid_state(1, (Face.SWORD, 7))
    empty = tuple([0] * NUM_FACES)
    assert empty in valid_actions(s)


def test_all_actions_satisfy_constraints():
    s = valid_state(1, (Face.SWORD, 3), (Face.COIN, 2), (Face.MONKEY, 1), (Face.PARROT, 1))
    for kept in valid_actions(s):
        n_reroll = NUM_DICE - s.n_skulls - sum(kept)
        assert n_reroll >= 0, "Can't reroll negative dice"
        assert n_reroll != 1, "Rerolling exactly 1 die is forbidden"
        assert s.n_skulls + sum(kept) >= 1, "Must keep at least 1 die total"


def test_full_board_no_skulls_always_has_reroll_options():
    # Even with 8 non-skull dice, you can keep 6 and reroll 2
    s = valid_state(0, (Face.SWORD, 4), (Face.COIN, 4))
    non_stop = [k for k in valid_actions(s) if k != s.held]
    assert len(non_stop) > 0


def test_2_skulls_always_has_reroll_options():
    # With 2 skulls and 6 non-skull dice, can keep 4 and reroll 2 (minimum)
    s = valid_state(2, (Face.SWORD, 6))
    non_stop = [k for k in valid_actions(s) if sum(k) != sum(s.held)]
    assert len(non_stop) > 0
