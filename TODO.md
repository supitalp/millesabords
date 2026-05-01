# TODO — Mille Sabords Website (Play Mode)

All items below concern the **play mode** of the web interface.

---

## UX / Interaction

A1. [x] **Prevent rerolling a single die or all dice** — guard against degenerate reroll selections (1 die or full set of 8)
A2. [x] **Freeze the bonus card in play mode** — the card selector should be locked to avoid mid-turn changes
A3. [x] **Rename "Reorder" button** → "Group Dice" (clearer label)
A4. [x] **Convert "Show Strategy" to a toggle** — when toggled on, the recommended dice to reroll are highlighted (with some kind of colored glow around the dice?); a new "Details" button opens a modal with the full strategy table (closeable). When the recommended strategy is "stop", we find a way to make this clear (not just not highlighting any dice).
A5. [x] **When the "+500 pt" bonus is enabled** (when all dice contribute a point), show a visual indicator (like a "safe" emoji or similar)
A6. [x] **When the card is pirate_ship**, show a visual indicator when the contract (number of swords) is fulfilled or not
A6. [ ] **Add a "Share" button** — lets users share the current game state (dice + card) via a URL or clipboard link
A7. [x] **Better dice roll animations** -- in particular when starting a new turn, we should start showing "blank" dice + gradually show them in a short animation (~1-2s). Same for when we re-roll dice + same when choosing the random "bonus card".

---

## Feedback / Gauges

B1. [x] **Danger gauge** — when the user selects a set of dice to reroll, display the probability of an immediate bust (≥3 skulls after the roll)
B2. [ ] **Opportunity gauge** — when the user selects a set of dice to reroll, show the best possible score achievable with a lucky outcome on that reroll

---

## Game Logic

C1. [x] **Auto-remove Guardian card effect** when a skull is rerolled — once the Guardian's one-time skull reroll has been used, update the state accordingly
C2. [x] **Tiebreak by safety** — when two strategies have equal EV, prefer the one with the lower probability of immediate bust
C3. [x] **Correct random sampling for bonus cards** — the card drawn at the start of a turn should follow the real game distribution (non-uniform), not a uniform random pick
C4. [ ] **Support "pirate island" mode** (when >= 4 skulls at the start)
C5. [x] **Add support for the "safe" card**

---

## Multiplayer & Social

D1. [x] **Multi-player mode** — support multiple players taking turns, tracking scores across rounds
            - could the "share" button also share the results? e.g. the scores + dice states of all players after the round?
            - could we save pre-existing players as cookie? (e.g. Henri, Paul)
            - possible workflow: add a new "finish turn" button that would open a small model allowing to assign the current score to a given player (either entering the name manually, and/or selecting from a drop-down list of existing players saved in cookies) -> after pressing OK the score for that player is saved in the "score board" page
            - add a "view scores" page showing a table with players + their ordered list of scores below)
            - users are responsible for taking turns...

---

## Distribution & Packaging

E1. [ ] **"Install as app" on mobile** — add PWA manifest + service worker so the site can be installed to a phone home screen with one tap
E2. [ ] **Versioning / release strategy** — decide on a versioning scheme (semver? date-based?) and set up a release workflow

---

## Documentation

F1. [ ] **README** — write a top-level README covering project overview, local dev setup, and how to deploy to GitHub Pages
F2. [ ] **DP algorithm write-up** — document the dynamic-programming solver (intended as a blog post or `docs/` page)
F3. Document our modification of not allowing direct WIN, but instead saying that 9 identical dice is 8000 points (this is functionally equivalent) + document the similar choice for the "treasure island" card where we automatically save the value of kept dice before rerolling.

## Research

G1. Can we express the expected values at game start as fractions (closed-form)? Not just as approximations?

---

## Appendix — Bonus Card Deck Composition

The physical deck contains **35 cards** in total. Probabilities below are used for correct random sampling (see Game Logic above).

| Card | Count | Probability |
|---|---|---|
| Coin | 4 | 11.4 % |
| Diamond | 4 | 11.4 % |
| Animals | 4 | 11.4 % |
| Guardian | 4 | 11.4 % |
| Pirate (×2 points) | 4 | 11.4 % |
| Safe | 4 | 11.4 % |
| Skull ×1 | 3 | 8.6 % |
| Pirate Ship (≥2 swords) | 2 | 5.7 % |
| Pirate Ship (≥3 swords) | 2 | 5.7 % |
| Pirate Ship (≥4 swords) | 2 | 5.7 % |
| Skull ×2 | 2 | 5.7 % |
| **Total** | **35** | **100 %** |

> Until the "Safe" card is implemented, draws should sample from the remaining **31 cards** (excluding the 4 Safe cards), adjusting probabilities accordingly.
