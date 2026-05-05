# Expected value by card

Expected score for a full turn under optimal play, for every bonus card. These are exact values from the DP fixed points (Bellman equations), confirmed by Monte Carlo simulation.

| Card | Expected value | Mechanic |
|------|---------------:|---------|
| 🏴‍☠️ Pirate | **1 158 pts** | Final score × 2 |
| 🛡️ Guardian | **905 pts** | May reroll one skull once per turn |
| ⛈️ After the Storm | **805 pts** | One reroll only; coins & diamonds score ×2; skull island disabled |
| 🪙 Coin | **784 pts** | Extra die, pre-set to Coin |
| 💎 Diamond | **784 pts** | Extra die, pre-set to Diamond |
| 🦜 Animals | **735 pts** | Monkeys and Parrots form one combined combo |
| 🏝️ Treasure Island | **680 pts** | Held dice score even on bust |
| 🎲 No card *(baseline)* | **579 pts** | — |
| 🕊️ Peace | **521 pts** | No swords allowed; any sword: −1 000 pts/sword (BGA variant) |
| ⚔️⚔️ Pirate Ship (2 swords) | **443 pts** | Meet quota: +300 pts; fail: −300 pts |
| 🧟 Zombie Attack | **436 pts** | ≥5 swords: 1 200 pts; else 0 pts (binary outcome; no player choices) |
| 💀 Skull ×1 | **346 pts** | Starts with 1 extra locked skull |
| ⚔️⚔️⚔️ Pirate Ship (3 swords) | **249 pts** | Meet quota: +500 pts; fail: −500 pts |
| 💀💀 Skull ×2 | **113 pts** | Starts with 2 extra locked skulls |
| ⚔️⚔️⚔️⚔️ Pirate Ship (4 swords) | **−156 pts** | Meet quota: +1 000 pts; fail: −1 000 pts |

Pirate Ship (4 swords) is the only card with a **negative** expected value under optimal play — the quota is hard enough to reach that the −1 000 penalty dominates on average.

## Score distributions

▶ [Interactive version](https://supitalp.github.io/millesabords/score_distributions.html) — hover for exact probabilities, click any bubble for example dice combinations.

Each row is one card, sorted from worst to best EV. Bubble area is proportional to the probability of landing in that 100-pt bin under the optimal strategy; the triangle marker shows the expected value. Cards near the top have narrow, left-skewed distributions (high bust rates); cards near the bottom spread wider to the right as high-combo turns become more likely.
