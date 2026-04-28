import pytest
from solver.model import Face, NUM_FACES, NUM_DICE, State, CARD_CONFIGS
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


def test_2_skulls_cannot_reroll_all_non_skull():
    # must keep at least 1 non-skull die when rerolling, even with 2 skull safety net
    s = valid_state(2, (Face.SWORD, 6))
    empty = tuple([0] * NUM_FACES)
    assert empty not in valid_actions(s)


def test_1_skull_cannot_reroll_all_non_skull():
    # must keep at least 1 non-skull die when rerolling
    s = valid_state(1, (Face.SWORD, 7))
    empty = tuple([0] * NUM_FACES)
    assert empty not in valid_actions(s)


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


# ── Coin / Diamond card: initial_held dice must never appear in reroll column ──

def test_coin_card_locked_die_never_rerolled():
    """The coin from the coin card must always stay in 'kept', never be rerolled."""
    config = CARD_CONFIGS["coin"]
    # State with 1 skull, coin card die + 3 swords + 4 monkeys held (total_dice=9)
    h = held((Face.COIN, 1), (Face.SWORD, 3), (Face.MONKEY, 4))
    state = State(n_skulls=1, held=h)
    for kept in valid_actions(state, config):
        assert kept[Face.COIN] >= 1, (
            f"Coin card's locked die appeared in reroll for kept={kept}"
        )


def test_diamond_card_locked_die_never_rerolled():
    """The diamond from the diamond card must always stay in 'kept', never be rerolled."""
    config = CARD_CONFIGS["diamond"]
    h = held((Face.DIAMOND, 1), (Face.SWORD, 3), (Face.MONKEY, 4))
    state = State(n_skulls=1, held=h)
    for kept in valid_actions(state, config):
        assert kept[Face.DIAMOND] >= 1, (
            f"Diamond card's locked die appeared in reroll for kept={kept}"
        )


def test_coin_card_stop_action_has_correct_coin_count():
    """Stop action for coin card should preserve all coins including the locked card die."""
    config = CARD_CONFIGS["coin"]
    h = held((Face.COIN, 2), (Face.SWORD, 2), (Face.MONKEY, 4))
    state = State(n_skulls=1, held=h)
    actions = valid_actions(state, config)
    stop = next((k for k in actions if k == state.held), None)
    assert stop is not None, "Stop action (keep all) must always be present"
    assert stop[Face.COIN] == 2
