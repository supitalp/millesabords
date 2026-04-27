# Card Implementation Plan

Cards are implemented in order of increasing complexity. Each group unlocks infrastructure
used by the next.

---

## Group A — Parameterise `total_dice` (foundation for everything)

The solver hard-codes `NUM_DICE = 8`. Any card that introduces an extra die (skull or non-skull)
requires the DP to be rebuilt with a different `total_dice`. This refactor is the first step,
using Tête de Mort as the vehicle.

A `TurnConfig` NamedTuple is introduced in `model.py` and threaded through all modules.
The solution cache is keyed by `TurnConfig` so each distinct config is solved once.

### 1. Tête de Mort — 1 skull (`tete-de-mort-1`)
- **Effect:** player starts with 1 skull pre-locked; rolls 8 dice as usual.
  Total dice pool = 9. A 3rd skull ends the turn (card skull counts).
- **Config:** `TurnConfig(total_dice=9, initial_n_skulls=1)`
- **Code changes:**
  - `model.py`: add `TurnConfig(total_dice, initial_n_skulls, initial_held)`
  - `scoring.py`: use `config.total_dice` for full-board bonus check
  - `actions.py`: use `config.total_dice` for `n_reroll` calculation
  - `dp.py`: `_all_states` and `_solve` parameterised by config; cache keyed by config
  - `stats.py`, `report.py`: thread config through
  - `main.py`: add optional `--card` flag

### 2. Tête de Mort — 2 skulls (`tete-de-mort-2`)
- **Effect:** player starts with 2 skulls pre-locked; any skull on first roll ends the turn.
  Total dice = 10.
- **Config:** `TurnConfig(total_dice=10, initial_n_skulls=2)`
- **Code changes:** zero — just a new config entry.

---

## Group B — Pre-set held dice (trivial once Group A is done)

### 3. Pièce d'or (`piece-d-or`)
- **Effect:** player starts with 1 coin already in hand (card counts as extra die).
  Total dice = 9. Coin always contributes to scoring.
- **Config:** `TurnConfig(total_dice=9, initial_held=(0,0,1,0,0,0))`
- **Code changes:** new config entry; `dice_to_state` already merges `initial_held` into state.

### 4. Diamant (`diamant`)
- **Effect:** same as Pièce d'or but with diamond.
- **Config:** `TurnConfig(total_dice=9, initial_held=(0,0,0,1,0,0))`
- **Code changes:** zero — just a new config entry.

---

## Group C — Scoring modifiers (independent of state/DP structure)

### 5. Animaux (`animaux`)
- **Effect:** monkey and parrot count as the same symbol for combos.
- **Config:** `TurnConfig(merge_animals=True)`
- **Code changes:**
  - `scoring.py`: when `merge_animals`, sum monkey+parrot counts before combo lookup.
  - `dp.py`: scoring change propagates automatically through value iteration.
  - State representation stays the same (monkeys and parrots remain distinct in state;
    only scoring collapses them).

### 6. Pirate (`pirate`)
- **Effect:** final score × 2.
- **Config:** `TurnConfig(score_multiplier=2)`
- **Code changes:**
  - `scoring.py`: multiply final score by `config.score_multiplier`.
  - DP values naturally double; optimal policy is unchanged (doubling is monotone).

---

## Group D — New state dimensions (moderate complexity)

### 7. Gardienne (`gardienne`)
- **Effect:** once per turn, the player may reroll one skull die.
- **Config:** `TurnConfig(skull_reroll_available=True)`
- **Code changes:**
  - `model.py`: add `skull_reroll_used: bool` to `State` (doubles state space to ~2070).
  - `actions.py`: when `skull_reroll_available and not skull_reroll_used and n_skulls >= 1`,
    add actions that reroll 1 skull (combined with any normal reroll of non-skull dice).
  - `dp.py`: state space change, otherwise same value iteration.

### 8. Bateau pirate (`bateau-pirate-N-B-P`)
- **Effect:** player must accumulate at least N swords by end of turn.
  - If swords >= N at stop: +B bonus points.
  - If swords < N at stop: score = 0, -P points subtracted from player's total.
  - Skull Island is disabled (4+ skulls on first roll = immediate turn loss, not island mode).
- **Config:** `TurnConfig(required_swords=N, sword_bonus=B, sword_penalty=P)`
- **Multiple variants** in the deck (different N/B/P values — e.g. 2 swords/+300/-500,
  4 swords/+600/-1000, etc.). Each is a distinct config.
- **Code changes:**
  - `scoring.py`: apply bonus/penalty based on final sword count vs requirement.
  - `report.py`: display sword requirement and current sword count prominently.

---

## Group E — New state multiset (hardest)

### 9. L'île au Trésor (`ile-au-tresor`)
- **Effect:** after each roll, the player may "freeze" any number of dice on the card.
  Frozen dice contribute to the final score even if the player later gets 3 skulls.
  Frozen dice can be taken back and rerolled on subsequent turns.
- **Config:** `TurnConfig(treasure_island=True)`
- **Code changes:**
  - `model.py`: state gains a `frozen: tuple` field (same count-vector format as `held`).
    Score = score(held + frozen) but frozen are safe from skull-bust.
  - `actions.py`: at each decision, player also chooses which held dice to move to frozen
    (any subset, zero or more). Combined with keep/reroll choice.
  - `scoring.py`: bust score (3 skulls) = score of frozen dice only (not 0).
  - `dp.py`: state space grows significantly (held × frozen combinations).
    Still finite; value iteration applies.

---

## Implementation status

| # | Card | Config key | Status |
|---|---|---|---|
| 1 | Tête de Mort (1 skull) | `tete-de-mort-1` | ✅ Done |
| 2 | Tête de Mort (2 skulls) | `tete-de-mort-2` | ✅ Done |
| 3 | Pièce d'or | `piece-d-or` | ✅ Done |
| 4 | Diamant | `diamant` | ✅ Done |
| 5 | Animaux | `animaux` | pending |
| 6 | Pirate | `pirate` | pending |
| 7 | Gardienne | `gardienne` | pending |
| 8 | Bateau pirate | `bateau-pirate-*` | pending |
| 9 | L'île au Trésor | `ile-au-tresor` | pending |
