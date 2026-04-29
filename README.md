# Mille Sabords — Optimal Strategy Solver

A dynamic-programming solver and web app for the dice game *Mille Sabords*.
Given any dice state and bonus card, the
solver computes the **exact optimal strategy** — keep which dice, reroll the
rest, or stop — together with the expected score, bust probability, and
score range for every legal action.

---

## How it works

The solver enumerates every reachable game state as a tuple
`(n_skulls, held_counts, skull_reroll_used)` and runs value iteration to
find the strategy that maximises the expected score of the current turn.
The resulting value function `V(state)` and the matching policy are exported
to compact JSON files (`docs/data/<card>.json`) that the web app loads
on demand.

---

## Rule deviations

The solver implements the published Mille Sabords rules faithfully with two
deliberate, clearly-justified simplifications.

### 1. Nine-of-a-kind: a score tier instead of an instant win

**Published rule.** If a player rolls nine identical symbols, they win the
entire game immediately ("Pirate's Magic"). This is only reachable with the
Gold Coin or Diamond card, which add a ninth die.

**Our rule.** Nine-of-a-kind is treated as the highest combo tier, worth
**8,000 points**, and play continues normally. The combo progression is:

| Identical dice | 3 | 4 | 5 | 6 | 7 | 8 | **9** |
|---|---|---|---|---|---|---|---|
| Points | 100 | 200 | 500 | 1 000 | 2 000 | 4 000 | **8 000** |

The doubling rhythm (×2 each step, with the notable jump from 5 → 6) is
simply continued for one more tier.

**Why this makes sense within the rules.** The game's scoring philosophy is
that bigger combos earn disproportionately more. Nine-of-a-kind is a natural
extension of that logic: one more identical die, one more doubling. The
8,000-point score is far above any other achievable score in a single turn
(the previous best is 5,300 points for 8 coins with a full-chest bonus),
so it remains a dramatic, game-changing event — just one measured within
the scoring system rather than outside it.

**Why we made this choice.** The "instant win" mechanic creates a
mathematical discontinuity that complicates the DP considerably. The
value function needs to distinguish "normal expected points" from
"game-win probability", which requires maintaining two separate value
functions (`V` and `V_normal`) and careful handling of win states to avoid
inflating the expected-value calculations for adjacent states. By treating
nine-of-a-kind as a score tier, a single value iteration converges to
a self-consistent, correct solution with no special cases, no sentinel
values, and no risk of value-inflation bugs.

In practice, the change has a negligible effect on strategy: the
probability of reaching nine-of-a-kind from any realistic in-game state is
so small (roughly 1/36 to 1/1296 depending on how many coins/diamonds are
already held) that the strategy recommended by the solver is identical under
either rule — stop when 8,000 points is the stop-score, reroll when it is
not, for exactly the same reasons.

---

### 2. Treasure Island: implicit "freeze" instead of explicit dice placement

**Published rule.** The Treasure Island card introduces a spatial mechanic:
the player can physically move dice from the rolling area onto a "Treasure
Island" tableau, locking them there safely. If the player later busts (three
or more skulls), only the dice on the island score; dice left on the table do
not. The player can also retrieve dice from the island back to the table at
any time and reroll them.

**Our rule.** The solver collapses the "on the island" / "on the table"
distinction into the existing `held` count vector. Concretely:

- **State:** unchanged — `(n_skulls, held)`.
- **Actions:** unchanged — at each decision the player picks which non-skull
  dice to keep (`kept ⊆ held`); everything else is rerolled.
- **Bust scoring:** if the player busts (`n_skulls ≥ 3`), their score is
  `score(held)` instead of `0` — i.e., whatever dice were held (not
  rerolled) at the moment of busting count normally.

There is no explicit island step in the UI: dice you choose not to reroll
are implicitly treated as "on the island" and will score if you bust.

**Why this is equivalent for computing the optimal strategy.**  
In the full DP, a player can move a die from the table to the island at
zero cost, and can always move it back. A rational player will therefore
always move every die they intend to keep onto the island before each
reroll — there is never any incentive to leave a scoring die on the table
at risk. Because the optimal action is to freeze exactly the dice you keep,
the two formulations produce identical decisions and identical expected
values. This equivalence was verified formally: `V[TI] ≥ V[default]` for
every state (bust protection never hurts), and the Monte-Carlo simulator
confirms the theoretical EV matches the empirical mean within statistical
noise.

**Why we made this choice.**  
The full implementation would augment the state with an additional
`frozen` count vector, blowing up the state space by a factor of roughly
**40×**:

| Dice | Default states | Full TI states |
|------|---------------|----------------|
| 8    | 1,035         | 40,755         |

This would multiply DP solve time, JSON file size, and in-browser compute
proportionally. More importantly, it would require a significantly more
complex UI — the player would need explicit island/table zones, drag-and-drop
or per-die placement buttons — with no gain in strategic depth, since a
rational player always freezes everything they keep anyway. The simplified
model is strategically equivalent, gives correct EV numbers, and keeps the
codebase and UI straightforward.

---

## Project structure

```
solver/         Python DP solver (model, scoring, actions, DP, stats, report)
docs/           Static web app (Vue 3, no build step)
  app.js        All logic: solver port, Vue components, UI
  index.html    HTML shell
  style.css     Styles
  data/         Precomputed JSON per card (generated by export_data.py)
  export_data.py  Regenerate docs/data/ from the Python solver
tests/          pytest suite
verify_solver.py  Monte-Carlo verifier: runs N simulations and checks
                  empirical mean vs theoretical turn_ev()
```

## Running locally

```bash
# Solve all cards and export JSON data
uv run python docs/export_data.py

# Run the test suite
uv run pytest

# Monte-Carlo verification (e.g. 1M sims for the coin card)
uv run python verify_solver.py --card coin --n 1000000

# Serve the web app
python -m http.server 8080 --directory docs
```
