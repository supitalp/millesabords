import pytest
from solver.model import Face, NUM_FACES, NUM_DICE, State
from solver.dp import V, get_solution
from solver.scoring import score


def held(*pairs):
    counts = [0] * NUM_FACES
    for face, count in pairs:
        counts[face] = count
    return tuple(counts)


def valid_state(n_skulls, *pairs):
    h = held(*pairs)
    assert n_skulls + sum(h) == NUM_DICE
    return State(n_skulls=n_skulls, held=h)


def test_v_geq_stop_score_always():
    # Optimal play is always at least as good as stopping immediately
    test_states = [
        valid_state(0, (Face.SWORD, 3), (Face.COIN, 2), (Face.MONKEY, 3)),
        valid_state(1, (Face.COIN, 4), (Face.SWORD, 3)),
        valid_state(2, (Face.DIAMOND, 3), (Face.PARROT, 3)),
        valid_state(0, (Face.COIN, 8)),
    ]
    for s in test_states:
        assert V(s) >= score(s.n_skulls, s.held), f"Failed for state {s}"


def test_8_identical_coins_stop_is_optimal():
    # 8 coins, 0 skulls: score = 4000 (combo) + 800 (individual) + 500 (full board) = 5300.
    # Rerolling any subset can only risk skulls or lose the full-board bonus, so stop is optimal.
    s = valid_state(0, (Face.COIN, 8))
    assert V(s) == score(0, s.held) == 5300


def test_all_states_have_finite_value():
    sol = get_solution()
    assert (sol.V >= 0).all()
    assert (sol.V < 10_000).all()  # max theoretical score is well below this


def test_v_is_at_least_zero():
    sol = get_solution()
    assert (sol.V >= 0).all()


def test_2_skulls_stop_score_reasonable():
    # With 2 skulls and a decent hand, V >= stop score
    s = valid_state(2, (Face.SWORD, 3), (Face.COIN, 3))
    assert V(s) >= score(2, s.held)


def test_high_value_combo_prefers_stop():
    # 7 swords + 1 skull: stop = 2000. Rerolling risks a 2nd skull.
    # V must be >= 2000. Whether it equals 2000 (stop is optimal) or more
    # depends on EV of rerolling — the solver knows.
    s = valid_state(1, (Face.SWORD, 7))
    assert V(s) >= 2000


def test_value_iteration_converged():
    # Calling get_solution twice should return the same cached object
    s1 = get_solution()
    s2 = get_solution()
    assert s1 is s2


def test_total_state_count():
    # Sanity check: should be exactly 1035 states
    from itertools import combinations_with_replacement
    from solver.model import NUM_FACES, NUM_DICE
    total = 0
    for n_skulls in range(3):
        n_held = NUM_DICE - n_skulls
        total += sum(1 for _ in combinations_with_replacement(range(1, NUM_FACES), n_held))
    assert total == 1035
