# Action Plan — Phase 1: Core Turn Solver (No Cards)

## Goal

A Python program that takes a set of 8 dice values as input and produces a ranked report of all valid actions, each annotated with P(lose), expected score, and min/max reachable score. No Pirate cards, no Skull Island.

---

## Step 1 — Data Model

**File:** `solver/model.py`

Define the vocabulary shared by all other modules.

- `Face` enum: `SKULL, SWORD, COIN, DIAMOND, MONKEY, PARROT`
- `DIE_FACES`: tuple of all 6 faces (the sample space per die)
- `State`: named tuple or dataclass `(n_skulls: int, held: tuple[int, ...])` where `held` is a length-6 count vector indexed by `Face` (counts of each non-skull face currently held). Skulls in `held` are always 0.
- `COMBO_SCORE`: dict mapping count → points `{3:100, 4:200, 5:500, 6:1000, 7:2000, 8:4000}` (0 for < 3)

**Key decision**: represent `held` as a sorted count-tuple (not a list of individual dice) so states are hashable and combinatorially identical dice are not double-counted.

**Test:** round-trip a few states through repr/hash, confirm distinct dice arrangements collapse to the same state.

---

## Step 2 — Scoring Function

**File:** `solver/scoring.py`

```
def score(n_skulls: int, held_counts: tuple[int, ...]) -> int
```

Logic:
1. If `n_skulls >= 3`: return 0 (should not be called, but defensive)
2. Sum combination scores: for each non-skull face, look up count in `COMBO_SCORE`
3. Add 100 × (count_COIN + count_DIAMOND) for individual bonuses
4. If `n_skulls == 0` and `sum(held_counts) == 8`: add 500 (full treasure chest)
5. Return total

**Unit tests** (hardcode expected values from the rules and the worked example):
- 4 coins + 1 diamond + 3 other: verify combo + individual bonuses
- Full board with 0 skulls: verify +500 bonus
- Full board with 1 skull: verify bonus absent
- 3 skulls: verify 0

---

## Step 3 — Action Enumeration

**File:** `solver/actions.py`

```
def valid_actions(state: State) -> list[tuple[int, ...]]
```

Returns all valid `kept_counts` (same format as `held`) the player can choose from the current `held_counts`, given `state.n_skulls`.

Logic — enumerate all sub-multisets of `state.held`:
- For each sub-multiset `kept` of `state.held`:
  - `n_reroll = 8 - state.n_skulls - sum(kept)`
  - Valid if `n_reroll == 0` (stop) OR (`n_reroll >= 2` AND `state.n_skulls + sum(kept) >= 1`)
  - `n_reroll == 1` is never valid (can't reroll exactly 1 die)

The "stop" action is `kept = state.held` (keep everything, reroll 0). It is always valid.

**Implementation note**: enumerate sub-multisets using itertools or a recursive generator. Given at most 8 dice and 5 symbols, the number of sub-multisets is at most ~500 per state — no performance concern.

**Unit tests:**
- State with 2 skulls and 6 non-skull dice: verify stop is valid, reroll-all-6 is valid, reroll-1 is absent
- State with 0 skulls and 8 non-skull dice: verify that keeping 0 dice (rerolling all 8) is invalid
- State with 0 skulls and 2 non-skull dice: verify only "stop" is valid (can't reroll 2 and keep ≥1 with only 2 free dice)

---

## Step 4 — Outcome Distribution for a Roll

**File:** `solver/roll.py`

```
def roll_outcomes(n_dice: int) -> list[tuple[tuple[int,...], float]]
```

Returns all distinct outcomes of rolling `n_dice` dice, each as `(counts_tuple, probability)`.

- Enumerate multisets of size `n_dice` over 6 faces using `itertools.combinations_with_replacement`
- For each multiset, compute multinomial probability: `multinomial(n_dice; k1..k6) / 6^n_dice`
- Returns list of `(counts_6tuple, prob)` pairs; probabilities sum to 1.0

**Why precompute this**: the same roll distribution (e.g. "roll 3 dice") is reused across many DP states, so cache by `n_dice`.

**Unit test:** for n_dice=1, verify 6 outcomes each with probability 1/6. For n_dice=2, verify probabilities sum to 1.

---

## Step 5 — Exact DP Solver

**File:** `solver/dp.py`

```
def solve(state: State) -> tuple[int, dict]
```

Returns `(optimal_value, policy)` where `policy` maps each reachable state to its optimal action.

Core: memoized recursive value function.

```python
@lru_cache(maxsize=None)
def V(state: State) -> float:
    stop_value = score(state.n_skulls, state.held)
    best = stop_value
    for kept in valid_actions_excluding_stop(state):
        n_reroll = 8 - state.n_skulls - sum(kept)
        ev = 0.0
        for outcome_counts, prob in roll_outcomes(n_reroll):
            new_skulls = state.n_skulls + outcome_counts[SKULL]
            if new_skulls >= 3:
                ev += prob * 0  # lose
            else:
                new_held = add_held(kept, outcome_counts_non_skull)
                ev += prob * V(State(new_skulls, new_held))
        best = max(best, ev)
    return best
```

The function also collects, for each action at the initial state, the full per-action statistics (see Step 6).

**Memoisation key:** `State` is hashable via its tuple representation. The full DP converges on first call; subsequent calls to the same state return cached results.

**State space size estimate:** n_skulls ∈ {0,1,2} × multisets of up to 8 non-skull dice over 5 symbols → ≤ 1035 states. Solves in milliseconds.

---

## Step 6 — Per-Action Statistics

**File:** `solver/stats.py`

```
def action_stats(state: State, kept: tuple[int,...]) -> ActionStats
```

where `ActionStats` is a dataclass:

```python
@dataclass
class ActionStats:
    kept: tuple          # multiset of dice kept
    n_reroll: int
    p_lose: float        # probability of ending with 0 points
    ev: float            # expected final score (optimal play, losses count as 0)
    ev_no_lose: float    # expected score conditioned on not losing
    min_score: int       # minimum non-zero score reachable (optimal play)
    max_score: int       # maximum non-zero score reachable (optimal play)
    delta_vs_stop: float # ev - score(stop right now)
```

For the stop action (`n_reroll == 0`): p_lose=0, ev=score(state), min=max=score(state), delta=0.

For a reroll action, compute stats by recursively traversing all outcome paths (using the DP value function):
- p_lose: sum of probabilities of paths that eventually reach 3 skulls
- ev: sum over all paths of (prob × final_score)
- min_score / max_score: min/max of `V(next_state)` across outcomes where no loss occurs

**Note on min/max semantics**: these represent the range of optimal-play outcomes, not worst/best-case play. The player minimising/maximising their score is not the goal — the range shows the volatility of the action.

---

## Step 7 — Report Generator

**File:** `solver/report.py`

```
def report(initial_dice: list[Face]) -> str
```

Given 8 die values (the first roll), prints a ranked table:

1. Parse input into a `State(n_skulls, held_counts)`
2. Compute `ActionStats` for every valid action at this state
3. Sort by `ev` descending
4. Print:
   - Current state summary (dice values, current score if stopping now)
   - Table: rank | action description | P(lose) | EV | EV|no-lose | min | max | delta
   - Mark the top action as "★ RECOMMENDED"

**Action description**: human-readable string like "keep [3×COIN, 2×SWORD], reroll 3 dice".

---

## Step 8 — CLI Entry Point

**File:** `main.py`

```
python main.py SKULL SWORD COIN COIN DIAMOND MONKEY PARROT SWORD
```

Accepts 8 face names as command-line arguments (case-insensitive), runs the solver, prints the report to stdout.

---

## Step 9 — Tests & Validation

**File:** `tests/`

Key test cases:

| Scenario | Expected behaviour |
|---|---|
| 3 skulls on first roll | Immediate loss, no valid reroll actions |
| 8 identical non-skull dice | Only stop action valid; full-board bonus applies |
| 1 skull + 7 swords | Stopping gives 2000 pts; solver should recommend stop (rerolling risks skull #2) |
| 2 skulls + 6 non-skull | Any reroll risks losing; solver weights EV correctly |
| All 8 coins | Score = 4000 (combo) + 800 (individual) + 500 (full board) = 5300 |
| Worked example from rules | Verify each decision step matches expected scores |

---

## Implementation Order & Dependencies

```
model.py  ──►  scoring.py
          ──►  actions.py  ──►  roll.py  ──►  dp.py  ──►  stats.py  ──►  report.py  ──►  main.py
```

Each step is independently testable. Suggested order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8, with tests written alongside each step.

---

## Open Questions Before Implementing

1. **Die face distribution**: ✅ Confirmed — each die is a standard fair die with one face per symbol (uniform 1/6 probability each).

2. **Monkey/parrot combo without Animals card**: the rules only merge monkey+parrot counts when the Animals card is active. Without it, monkeys and parrots are distinct symbols. Confirm this understanding.

3. **Full treasure chest with forced skulls (Skull card)**: if the card adds 1 skull at the start, can the player ever achieve the full-board bonus? Per the rules, skulls from the card count as dice, so with n_skulls ≥ 1 the bonus is impossible. Relevant only for Phase 3.
