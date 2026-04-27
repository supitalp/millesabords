from dataclasses import dataclass
from .model import State, NUM_FACES, Face, TurnConfig, DEFAULT_CONFIG
from .scoring import score
from .roll import roll_outcomes
from .dp import get_solution, _add_outcome


@dataclass
class ActionStats:
    kept: tuple
    n_reroll: int
    stop_score: int
    p_lose: float
    ev: float
    ev_no_lose: float
    min_score: int       # worst stop-score across non-losing outcomes after this roll
    max_score: int       # best achievable final score (best-case dice, optimal play)
    delta_vs_stop: float


def compute_stats(state: State, kept: tuple, config: TurnConfig = DEFAULT_CONFIG) -> ActionStats:
    n_reroll = config.total_dice - state.n_skulls - sum(kept)
    stop_score = score(state.n_skulls, state.held, config)

    if n_reroll == 0:
        return ActionStats(
            kept=kept, n_reroll=0, stop_score=stop_score,
            p_lose=0.0, ev=float(stop_score), ev_no_lose=float(stop_score),
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
        new_skulls = state.n_skulls + outcome[Face.SKULL]
        if new_skulls >= 3:
            p_lose += prob
        else:
            new_held = _add_outcome(kept, outcome)
            next_state = State(new_skulls, new_held)
            idx = sol.state_to_idx[next_state]

            val = float(sol.V[idx])
            ev += prob * val
            p_survive += prob
            ev_survive += prob * val

            next_stop = score(new_skulls, new_held, config)
            if min_score is None or next_stop < min_score:
                min_score = next_stop

            next_max = int(sol.max_score[idx])
            if max_score is None or next_max > max_score:
                max_score = next_max

    ev_no_lose = (ev_survive / p_survive) if p_survive > 0 else 0.0

    return ActionStats(
        kept=kept, n_reroll=n_reroll, stop_score=stop_score,
        p_lose=p_lose, ev=ev, ev_no_lose=ev_no_lose,
        min_score=min_score if min_score is not None else 0,
        max_score=max_score if max_score is not None else 0,
        delta_vs_stop=ev - stop_score,
    )
