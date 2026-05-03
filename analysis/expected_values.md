# Expected value by card

Expected score for a full turn under optimal play, for every bonus card. These are exact values from the DP fixed points (Bellman equations), confirmed by Monte Carlo simulation.

| Card | Expected value | Mechanic |
|------|---------------:|---------|
| 🏴‍☠️ Pirate | **1 158 pts** | Final score × 2 |
| 🛡️ Guardian | **906 pts** | May reroll one skull once per turn |
| 🪙 Coin | **784 pts** | Extra die, pre-set to Coin |
| 💎 Diamond | **784 pts** | Extra die, pre-set to Diamond |
| 🦜 Animals | **735 pts** | Monkeys and Parrots form one combined combo |
| 🏝️ Treasure Island | **680 pts** | Held dice score even on bust |
| 🎲 No card *(baseline)* | **579 pts** | — |
| ⚔️⚔️ Pirate Ship (2 swords) | **443 pts** | Meet quota: +300 pts; fail: −300 pts |
| 💀 Skull ×1 | **346 pts** | Starts with 1 extra locked skull |
| ⚔️⚔️⚔️ Pirate Ship (3 swords) | **249 pts** | Meet quota: +500 pts; fail: −500 pts |
| 💀💀 Skull ×2 | **113 pts** | Starts with 2 extra locked skulls |
| ⚔️⚔️⚔️⚔️ Pirate Ship (4 swords) | **−156 pts** | Meet quota: +1 000 pts; fail: −1 000 pts |

Pirate Ship (4 swords) is the only card with a **negative** expected value under optimal play — the quota is hard enough to reach that the −1 000 penalty dominates on average.
