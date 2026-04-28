# Mille Sabords — Game Solver: Specifications

## Overview

A companion tool that, given the current dice state (and optionally the active Pirate card), computes the optimal strategy for the player's turn and presents per-action statistics in a clear, actionable UI.

---

## Scope

### In scope

- Full optimal turn solver using exact dynamic programming
- Support for all Pirate card effects
- Per-action statistics: probability of losing, expected score, min/max reachable score (excl. losing outcomes)
- Web app UI usable as a phone/tablet companion while playing

### Out of scope (for now)

- Multi-turn / full-game strategy (the solver is per-turn only)
- Tracking cumulative scores across players
- Skull Island triggered on initial roll of 4+ skulls (complex separate mode, added later)

---

## Functional Requirements

### FR-1: Game State Representation

The solver must model the following state variables for a player's turn:

- **Accumulated skulls** (`n_skulls`): integer in {0, 1, 2}. Reaching 3 ends the turn with 0 points.
- **Non-skull dice showing** (`held_dice`): multiset of die faces currently visible (from any roll). The player can freely choose which of these to keep and which to re-roll.
- **Active Pirate card** (optional): affects scoring and special rules for the turn.

Die faces: skull, sword, coin, diamond, monkey, parrot.

> **Assumption (to verify against physical dice):** each face appears exactly once per die, giving a uniform 1/6 probability per face. The actual face distribution of the physical dice must be confirmed and is a parameter of the model.

### FR-2: Scoring

The score at the end of a turn (when the player voluntarily stops) is:

1. **Combination score**: for each symbol group, a combo of N identical dice scores:
   - 3 → 100 pts, 4 → 200 pts, 5 → 500 pts, 6 → 1000 pts, 7 → 2000 pts, 8 → 4000 pts
   - Skulls are never part of a combo.
2. **Coin/diamond bonus**: +100 pts per coin or diamond die (individual, in addition to combo score).
3. **Full treasure chest bonus**: +500 pts if all 8 dice are scored (i.e., `n_skulls == 0` and all 8 dice show non-skull values). Skulls forfeit this bonus.
4. **Pirate card modifiers** (see FR-5).

Score is 0 if n_skulls ≥ 3.

### FR-3: Action Enumeration

Given a state, a valid **action** is a choice of which non-skull dice to keep and how many to re-roll. Constraints (per the rules):

- At least 1 die must be reserved total (skull dice count toward this). Formally: `n_skulls + n_kept ≥ 1`.
- Re-rolling requires at least 2 dice: `n_reroll ≥ 2` (or 0 to stop).
- Skulls cannot be re-rolled.
- Previously kept non-skull dice can be un-kept and re-rolled.

**STOP** is always a valid action (n_reroll = 0), unless forced to re-roll by a card.

Actions are equivalent if they keep the same multiset of non-skull dice (positional identity of dice is irrelevant). The solver enumerates unique keep-multisets only.

### FR-4: Optimal Strategy Solver (Exact DP)

The solver computes the optimal value function `V(n_skulls, held_dice)` via memoized recursion:

```
V(s, held) = max(
    score(s, held),                          # stop action
    max over valid actions a of E_roll[V(s', held')]   # continue
)
```

where rolling `n_reroll` dice produces a distribution over (new_skulls, new_non_skull_dice), giving:

```
next_s = s + new_skulls
next_held = kept_held + new_non_skull_dice
```

If `next_s ≥ 3`: value = 0 (turn lost, no points).
Otherwise: recurse with `V(next_s, next_held)`.

Because the state space is small (~1035 states), this is solved exactly without approximation.

### FR-5: Pirate Card Support

Each card modifies the solver as follows:

| Card | Effect on solver |
|---|---|
| **Skull** (1 or 2 skulls) | Initial state starts with n_skulls = 1 or 2 |
| **Gold Coin** | Initial held_dice includes one extra coin; treated as a 9th die for scoring (can contribute to combos, gives 100 pts) |
| **Diamond** | Same as Gold Coin but with diamond |
| **Pirate** | Final score × 2; Skull Island damage × 2 |
| **Animals** | Monkeys and parrots are treated as the same symbol in combos |
| **Guardian** | Allows re-rolling one skull die once during the turn |
| **Treasure Island** | Dice placed on this card are "frozen" — they score at end of turn regardless of later skulls (up to 2 skulls); solver must track which dice are island-frozen vs in play |
| **Pirate Ship** (N sabres required) | If final sabre count < N: score = 0 and -penalty pts applied; if ≥ N: bonus pts added. Skull Island mechanic disabled. |

### FR-6: Per-Action Statistics

For each valid action at the current state, the solver reports:

- **P(lose)**: probability of accumulating 3 skulls before the turn ends (under optimal play from the next state onward).
- **E[score]**: expected final score under optimal play (weighted by all outcomes including losses at 0).
- **E[score | no lose]**: expected final score conditioned on not losing.
- **Min score** (excl. losing): minimum non-zero final score reachable from this action (across all non-losing outcome paths, under optimal play).
- **Max score** (excl. losing): maximum non-zero final score reachable from this action.
- **Score delta vs stopping**: E[score] minus the score obtained by stopping right now.
- **Recommended action**: the action maximising E[score].

### FR-7: Skull Island Mode

When the very first roll (all 8 dice) produces 4 or more skulls, the player enters Skull Island. This is a distinct mode:

- The player keeps accumulating skulls until a roll produces zero new skulls.
- No scoring; instead each skull accumulated costs all opponents 100 pts.
- The solver should detect this condition and switch to Skull Island mode.

*Skull Island support is deferred to a later iteration.*

---

## Non-Functional Requirements

### NFR-1: Accuracy
- DP solver must be exact (no approximation); Monte Carlo simulation may be offered as a secondary validation tool.
- All probabilities computed analytically from the die face distribution.

### NFR-2: Performance
- State space is ~1035 states; the full turn DP must solve in under 100 ms on commodity hardware.
- Web app must return results within 1 second of user input.

### NFR-3: Web App UI
- Single-page application, usable as a phone companion while playing.
- Mobile-first responsive design (primary use case: phone on the table).
- Dice input: tap/click each die to cycle through its 6 faces. Clear visual distinction between skull dice (locked) and free dice.
- Card input: select active Pirate card from a list.
- Output: ranked table of all valid actions with their statistics. Clearly highlight the recommended action.
- Offline-capable (static assets, solver runs client-side in the browser via WebAssembly or JavaScript).

### NFR-4: Correctness Validation
- Unit tests covering the scoring function, action enumeration, and DP solver.
- Test cases derived from the worked example in the rules and known edge cases.

---

## Phased Delivery

| Phase | Scope |
|---|---|
| **1 — Core solver (no cards)** | Scoring, action enumeration, exact DP solver, CLI report. No Pirate cards, no Skull Island. |
| **2 — Skull Island** | Detect and handle the 4+ skulls first-roll case. |
| **3 — Pirate cards** | Add all card effects to the solver. |
| **4 — Web app** | Browser UI wrapping the solver (Python→Wasm or rewrite in JS/TS). |
| **5 — Polish** | Animations, history, score tracking across turns (non-strategic, just tracking). |
