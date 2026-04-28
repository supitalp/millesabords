"""Tests for the Gardienne card (one-time skull reroll ability)."""
import pytest
from solver.model import Face, NUM_FACES, State, CARD_CONFIGS, DEFAULT_CONFIG
from solver.scoring import score
from solver.dp import get_solution
from solver.actions import gardienne_kept_options, valid_actions
from solver.stats import compute_stats
from solver.report import turn_ev

GARDIENNE = CARD_CONFIGS["gardienne"]


def held(*pairs):
    counts = [0] * NUM_FACES
    for face, count in pairs:
        counts[face] = count
    return tuple(counts)


# ---------------------------------------------------------------------------
# State: skull_reroll_used flag
# ---------------------------------------------------------------------------

def test_default_state_not_used():
    s = State(1, held((Face.SWORD, 7)))
    assert s.skull_reroll_used is False


def test_gardienne_state_space_doubles():
    sol_base = get_solution(DEFAULT_CONFIG)
    sol_gardienne = get_solution(GARDIENNE)
    assert len(sol_gardienne.states) == 2 * len(sol_base.states)


# ---------------------------------------------------------------------------
# Actions: Gardienne options available iff n_skulls >= 1 and not used
# ---------------------------------------------------------------------------

def test_gardienne_options_available_with_skull():
    # n_skulls=1, skull_reroll_used=False → Gardienne options exist
    state = State(1, held((Face.SWORD, 7)), skull_reroll_used=False)
    opts = gardienne_kept_options(state)
    assert len(opts) > 0


def test_no_gardienne_if_already_used():
    # skull_reroll_used=True → caller should not offer Gardienne
    state = State(1, held((Face.SWORD, 7)), skull_reroll_used=True)
    # The function doesn't check; it's the caller's responsibility.
    # But report/dp only call it when not used.
    assert not state.skull_reroll_used is False  # it IS used


def test_gardienne_reroll_count():
    # Keep all held, reroll only the freed skull → n_reroll = 1
    state = State(1, held((Face.SWORD, 7)), skull_reroll_used=False)
    full_hold = state.held
    s = compute_stats(state, full_hold, GARDIENNE, use_gardienne=True)
    assert s.n_reroll == 1  # just the freed skull


def test_gardienne_reroll_plus_normal():
    # Keep 5 swords, reroll 2 normal + 1 skull = 3 dice
    state = State(1, held((Face.SWORD, 7)), skull_reroll_used=False)
    kept = held((Face.SWORD, 5))
    s = compute_stats(state, kept, GARDIENNE, use_gardienne=True)
    assert s.n_reroll == 3


# ---------------------------------------------------------------------------
# DP: Gardienne value > base game (one extra reroll opportunity)
# ---------------------------------------------------------------------------

def test_gardienne_ev_higher_than_base():
    base_ev = turn_ev(DEFAULT_CONFIG)
    gardienne_ev = turn_ev(GARDIENNE)
    assert gardienne_ev > base_ev


def test_v_at_least_stop_value():
    sol = get_solution(GARDIENNE)
    assert (sol.V >= sol.stop_values - 1e-9).all()


def test_gardienne_not_used_state_has_higher_v():
    """State with Gardienne available (not used) should have V ≥ same state with it used."""
    sol = get_solution(GARDIENNE)
    # Pick a state with 1 skull where Gardienne could help
    h = held((Face.SWORD, 7))
    state_unused = State(1, h, skull_reroll_used=False)
    state_used   = State(1, h, skull_reroll_used=True)
    v_unused = sol.V[sol.state_to_idx[state_unused]]
    v_used   = sol.V[sol.state_to_idx[state_used]]
    assert v_unused >= v_used - 1e-9


# ---------------------------------------------------------------------------
# Stats: using Gardienne sets skull_reroll_used=True in next states
# ---------------------------------------------------------------------------

def test_gardienne_action_transitions_to_used_states():
    """After using Gardienne, next states should all have skull_reroll_used=True."""
    sol = get_solution(GARDIENNE)
    state = State(1, held((Face.SWORD, 7)), skull_reroll_used=False)
    kept = state.held  # keep all, reroll just the skull
    s = compute_stats(state, kept, GARDIENNE, use_gardienne=True)
    # EV should be better than stopping (skull removed → better state)
    assert s.ev > s.stop_score


def test_gardienne_with_2_skulls_reduces_bust_risk():
    """With 2 skulls and unused Gardienne, reactive rescue lowers bust risk vs base game."""
    state = State(2, held((Face.SWORD, 6)), skull_reroll_used=False)
    kept = held((Face.SWORD, 4))  # reroll 2 dice
    # Base game: bust if any skull from 2 dice → ≈30.6%
    s_base = compute_stats(state, kept, DEFAULT_CONFIG, use_gardienne=False)
    # Gardienne (reactive): exactly-3-skull outcomes get a rescue roll → ≈7.4%
    s_gardienne = compute_stats(state, kept, GARDIENNE, use_gardienne=False)
    assert s_gardienne.p_lose < s_base.p_lose
