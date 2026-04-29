from dataclasses import dataclass
from .model import State, NUM_FACES, Face, TurnConfig, DEFAULT_CONFIG
from .scoring import score
from .roll import roll_outcomes
from .dp import get_solution, _add_outcome


@dataclass
class ActionStats:
    kept: tuple
    n_reroll: int
    use_guardian: bool    # True when this action uses the Guardian skull-reroll ability
    stop_score: int
    p_lose: float
    ev: float
    ev_no_lose: float
    min_score: int        # worst stop-score across non-losing outcomes
    max_score: int        # best achievable score along this action's transition tree
    delta_vs_stop: float


def compute_stats(state: State, kept: tuple, config: TurnConfig = DEFAULT_CONFIG,
                  use_guardian: bool = False) -> ActionStats:
    if use_guardian:
        # Free 1 skull into reroll pool; n_skulls_base decreases by 1
        n_reroll = (sum(state.held) - sum(kept)) + 1
        n_skulls_base = state.n_skulls - 1
    else:
        n_reroll = config.total_dice - state.n_skulls - sum(kept)
        n_skulls_base = state.n_skulls

    stop_score = score(state.n_skulls, state.held, config)

    if n_reroll == 0:
        return ActionStats(
            kept=kept, n_reroll=0, use_guardian=False, stop_score=stop_score,
            p_lose=0.0,
            ev=float(stop_score), ev_no_lose=float(stop_score),
            min_score=stop_score, max_score=stop_score, delta_vs_stop=0.0,
        )

    sol = get_solution(config)

    p_lose = 0.0
    ev = 0.0
    p_survive = 0.0
    ev_survive = 0.0
    min_score = None
    max_score = None

    for outcome, prob in roll_outcomes(n_reroll):
        new_skulls = n_skulls_base + outcome[Face.SKULL]
        if new_skulls >= 3:
            bust_held = _add_outcome(kept, outcome)
            this_bust_score = float(score(new_skulls, bust_held, config))
            if config.skull_reroll_available and not state.skull_reroll_used and not use_guardian and new_skulls == 3:
                for rescue_outcome, rescue_prob in roll_outcomes(1):
                    if rescue_outcome[Face.SKULL] > 0:
                        p_lose += prob * rescue_prob
                        ev += prob * rescue_prob * this_bust_score
                    else:
                        rescue_held = _add_outcome(bust_held, rescue_outcome)
                        next_state = State(2, rescue_held, True)
                        idx = sol.state_to_idx[next_state]
                        val = float(sol.V[idx])
                        ev += prob * rescue_prob * val
                        p_survive += prob * rescue_prob
                        ev_survive += prob * rescue_prob * val
                        next_max = int(sol.max_score[idx])
                        if max_score is None or next_max > max_score:
                            max_score = next_max
                        next_stop = score(2, rescue_held, config)
                        if min_score is None or next_stop < min_score:
                            min_score = next_stop
            else:
                p_lose += prob
                ev += prob * this_bust_score
        else:
            new_held = _add_outcome(kept, outcome)
            new_skull_reroll_used = True if use_guardian else state.skull_reroll_used
            next_state = State(new_skulls, new_held, new_skull_reroll_used)
            idx = sol.state_to_idx[next_state]

            val = float(sol.V[idx])
            ev += prob * val
            p_survive += prob
            ev_survive += prob * val

            next_max = int(sol.max_score[idx])
            if max_score is None or next_max > max_score:
                max_score = next_max

            next_stop = score(new_skulls, new_held, config)
            if min_score is None or next_stop < min_score:
                min_score = next_stop

    ev_no_lose = (ev_survive / p_survive) if p_survive > 0 else 0.0

    return ActionStats(
        kept=kept, n_reroll=n_reroll, use_guardian=use_guardian,
        stop_score=stop_score, p_lose=p_lose,
        ev=ev, ev_no_lose=ev_no_lose,
        min_score=min_score if min_score is not None else 0,
        max_score=max_score if max_score is not None else 0,
        delta_vs_stop=ev - stop_score,
    )
