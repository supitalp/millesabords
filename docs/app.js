import { createApp, ref, computed, reactive } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.prod.js';

// ─── Constants ────────────────────────────────────────────────────────────────

const FACE = { SKULL: 0, SWORD: 1, COIN: 2, DIAMOND: 3, MONKEY: 4, PARROT: 5 };
const NUM_FACES = 6;
const WIN_SCORE = 1_000_000;
const FACE_BLANK = -1; // sentinel: die not yet rolled

const FACE_EMOJI = ['💀', '⚔️', '🪙', '💎', '🐒', '🦜'];
const FACE_NAMES = ['Skull', 'Sword', 'Coin', 'Diamond', 'Monkey', 'Parrot'];

const COMBO_SCORE = { 3: 100, 4: 200, 5: 500, 6: 1000, 7: 2000, 8: 4000 };

const CARD_OPTIONS = [
  { value: 'default',       name: 'No Card',       icon: '🎲',          desc: 'No bonus card',                        label: 'No card'                              },
  { value: 'skull-1',       name: 'Skull ×1',      icon: '💀',          desc: '1 skull locked at start',              label: 'Skull ×1 (1 skull locked)'            },
  { value: 'skull-2',       name: 'Skull ×2',      icon: '💀💀',        desc: '2 skulls locked at start',             label: 'Skull ×2 (2 skulls locked)'           },
  { value: 'coin',          name: 'Coin',           icon: '🪙',          desc: '+1 coin die at start',                 label: 'Coin (+1 coin die)'                   },
  { value: 'diamond',       name: 'Diamond',        icon: '💎',          desc: '+1 diamond die at start',              label: 'Diamond (+1 diamond die)'             },
  { value: 'animals',       name: 'Animals',        icon: '🐒🦜',        desc: 'Monkeys and parrots count together',   label: 'Animals (monkeys = parrots)'          },
  { value: 'pirate',        name: 'Pirate',         icon: '🏴‍☠️',          desc: 'Score × 2',                            label: 'Pirate (×2 score)'                    },
  { value: 'guardian',      name: 'Guardian',       icon: '🛡️',          desc: 'Reroll 1 skull once per turn',         label: 'Guardian (reroll 1 skull once)'       },
  { value: 'pirate-ship-2', name: 'Pirate Ship',    icon: '⚔️⚔️',        desc: '≥2 swords: +300 pts, else −300 pts',   label: 'Pirate Ship (+300 / −300)'   },
  { value: 'pirate-ship-3', name: 'Pirate Ship',    icon: '⚔️⚔️⚔️',      desc: '≥3 swords: +500 pts, else −500 pts',   label: 'Pirate Ship (+500 / −500)'   },
  { value: 'pirate-ship-4', name: 'Pirate Ship',    icon: '⚔️⚔️⚔️⚔️',    desc: '≥4 swords: +1000 pts, else −1000 pts',  label: 'Pirate Ship (+1000 / −1000)' },
];

const _EMPTY_HELD = [0, 0, 0, 0, 0, 0];
function _held(face, count = 1) {
  const h = [0, 0, 0, 0, 0, 0];
  h[face] = count;
  return h;
}

const CARD_CONFIGS = {
  'default':        { total_dice: 8,  initial_n_skulls: 0, initial_held: _EMPTY_HELD,                merge_animals: false, score_multiplier: 1, required_swords: 0, sword_bonus: 0,    sword_penalty: 0,    skull_reroll_available: false },
  'skull-1':        { total_dice: 9,  initial_n_skulls: 1, initial_held: _EMPTY_HELD,                merge_animals: false, score_multiplier: 1, required_swords: 0, sword_bonus: 0,    sword_penalty: 0,    skull_reroll_available: false },
  'skull-2':        { total_dice: 10, initial_n_skulls: 2, initial_held: _EMPTY_HELD,                merge_animals: false, score_multiplier: 1, required_swords: 0, sword_bonus: 0,    sword_penalty: 0,    skull_reroll_available: false },
  'coin':           { total_dice: 9,  initial_n_skulls: 0, initial_held: _held(FACE.COIN),           merge_animals: false, score_multiplier: 1, required_swords: 0, sword_bonus: 0,    sword_penalty: 0,    skull_reroll_available: false },
  'diamond':        { total_dice: 9,  initial_n_skulls: 0, initial_held: _held(FACE.DIAMOND),        merge_animals: false, score_multiplier: 1, required_swords: 0, sword_bonus: 0,    sword_penalty: 0,    skull_reroll_available: false },
  'animals':        { total_dice: 8,  initial_n_skulls: 0, initial_held: _EMPTY_HELD,                merge_animals: true,  score_multiplier: 1, required_swords: 0, sword_bonus: 0,    sword_penalty: 0,    skull_reroll_available: false },
  'pirate':         { total_dice: 8,  initial_n_skulls: 0, initial_held: _EMPTY_HELD,                merge_animals: false, score_multiplier: 2, required_swords: 0, sword_bonus: 0,    sword_penalty: 0,    skull_reroll_available: false },
  'guardian':       { total_dice: 8,  initial_n_skulls: 0, initial_held: _EMPTY_HELD,                merge_animals: false, score_multiplier: 1, required_swords: 0, sword_bonus: 0,    sword_penalty: 0,    skull_reroll_available: true  },
  'pirate-ship-2':  { total_dice: 8,  initial_n_skulls: 0, initial_held: _EMPTY_HELD,                merge_animals: false, score_multiplier: 1, required_swords: 2, sword_bonus: 300,  sword_penalty: 300,  skull_reroll_available: false },
  'pirate-ship-3':  { total_dice: 8,  initial_n_skulls: 0, initial_held: _EMPTY_HELD,                merge_animals: false, score_multiplier: 1, required_swords: 3, sword_bonus: 500,  sword_penalty: 500,  skull_reroll_available: false },
  'pirate-ship-4':  { total_dice: 8,  initial_n_skulls: 0, initial_held: _EMPTY_HELD,                merge_animals: false, score_multiplier: 1, required_swords: 4, sword_bonus: 1000, sword_penalty: 1000, skull_reroll_available: false },
};

function randomDice() {
  return Array.from({ length: 8 }, () => Math.floor(Math.random() * NUM_FACES));
}

// Deck composition (Safe card excluded — not yet implemented).
// Source: game rulebook; see TODO.md appendix for full table.
const CARD_DECK = [
  { value: 'coin',          weight: 4 },
  { value: 'diamond',       weight: 4 },
  { value: 'animals',       weight: 4 },
  { value: 'guardian',      weight: 4 },
  { value: 'pirate',        weight: 4 },
  { value: 'skull-1',       weight: 3 },
  { value: 'pirate-ship-2', weight: 2 },
  { value: 'pirate-ship-3', weight: 2 },
  { value: 'pirate-ship-4', weight: 2 },
  { value: 'skull-2',       weight: 2 },
]; // total weight = 31

function randomCard() {
  const total = CARD_DECK.reduce((s, c) => s + c.weight, 0);
  let r = Math.random() * total;
  for (const { value, weight } of CARD_DECK) {
    r -= weight;
    if (r <= 0) return value;
  }
  return CARD_DECK[CARD_DECK.length - 1].value; // float-rounding safety net
}

// ─── Solver logic (ported from Python) ────────────────────────────────────────

// Cache: n → [{outcome: [c0..c5], prob}]
const _rollCache = new Map();

function factorial(n) {
  let r = 1;
  for (let i = 2; i <= n; i++) r *= i;
  return r;
}

function multinomialProb(counts) {
  const n = counts.reduce((a, b) => a + b, 0);
  let denom = factorial(n);
  for (const c of counts) denom /= factorial(c);  // actually: numerator / denominator
  // Correct: multinomial = n! / (c0! * c1! * ... * c5!) / 6^n
  return (factorial(n) / counts.reduce((acc, c) => acc * factorial(c), 1)) / Math.pow(NUM_FACES, n);
}

// Generate all combinations with replacement: choose n items from [0..k-1]
function* combWithReplacement(k, n) {
  if (n === 0) { yield []; return; }
  const combo = new Array(n).fill(0);
  while (true) {
    yield combo.slice();
    let i = n - 1;
    while (i >= 0 && combo[i] === k - 1) i--;
    if (i < 0) return;
    const val = combo[i] + 1;
    for (let j = i; j < n; j++) combo[j] = val;
  }
}

function rollOutcomes(n) {
  if (_rollCache.has(n)) return _rollCache.get(n);
  if (n === 0) {
    const result = [{ outcome: [0, 0, 0, 0, 0, 0], prob: 1.0 }];
    _rollCache.set(n, result);
    return result;
  }
  const results = [];
  for (const combo of combWithReplacement(NUM_FACES, n)) {
    const counts = [0, 0, 0, 0, 0, 0];
    for (const face of combo) counts[face]++;
    results.push({ outcome: counts, prob: multinomialProb(counts) });
  }
  _rollCache.set(n, results);
  return results;
}

function scoreFunc(n_skulls, held, config) {
  if (n_skulls >= 3) {
    return config.sword_penalty ? -config.sword_penalty : 0;
  }
  // Pirate's Magic: 9 identical dice
  if (n_skulls === 0) {
    for (let f = 1; f < NUM_FACES; f++) {
      if (held[f] === 9) return WIN_SCORE;
    }
  }

  let total = 0;
  if (config.merge_animals) {
    const animalCount = held[FACE.MONKEY] + held[FACE.PARROT];
    for (let face = 1; face < NUM_FACES; face++) {
      if (face === FACE.MONKEY || face === FACE.PARROT) continue;
      const count = held[face];
      total += COMBO_SCORE[count] || 0;
      if (face === FACE.COIN || face === FACE.DIAMOND) total += 100 * count;
    }
    total += COMBO_SCORE[animalCount] || 0;
  } else {
    for (let face = 1; face < NUM_FACES; face++) {
      const count = held[face];
      total += COMBO_SCORE[count] || 0;
      if (face === FACE.COIN || face === FACE.DIAMOND) total += 100 * count;
    }
  }

  // Full treasure chest bonus
  const totalHeld = held.reduce((a, b) => a + b, 0);
  if (n_skulls === 0 && totalHeld === config.total_dice) {
    let allContribute;
    if (config.merge_animals) {
      const animalCount = held[FACE.MONKEY] + held[FACE.PARROT];
      allContribute = (held[FACE.SWORD] === 0 || held[FACE.SWORD] >= 3) &&
                      (animalCount === 0 || animalCount >= 3);
    } else {
      allContribute = [FACE.SWORD, FACE.COIN, FACE.DIAMOND, FACE.MONKEY, FACE.PARROT].every(f => {
        return held[f] === 0 || held[f] >= 3 || f === FACE.COIN || f === FACE.DIAMOND;
      });
    }
    if (allContribute) total += 500;
  }

  // Pirate Ship: sword requirement
  if (config.required_swords > 0 && held[FACE.SWORD] < config.required_swords) {
    return -config.sword_penalty;
  }

  total += config.sword_bonus;
  return total * config.score_multiplier;
}

// All sub-multisets of a count vector
function subMultisets(held) {
  // Cartesian product of range(0..held[i]) for each i
  let results = [[]];
  for (let i = 0; i < held.length; i++) {
    const next = [];
    for (const prefix of results) {
      for (let v = 0; v <= held[i]; v++) {
        next.push([...prefix, v]);
      }
    }
    results = next;
  }
  return results;
}

function validActions(state, config) {
  const actions = [];
  // Variable dice: held minus the card's locked initial_held dice (skulls always 0).
  const heldVariable = state.held.map((v, f) =>
    f === FACE.SKULL ? 0 : Math.max(0, v - config.initial_held[f])
  );

  for (const keptVariable of subMultisets(heldVariable)) {
    // Card's initial dice are always included on top of the chosen variable kept.
    const kept = keptVariable.map((kv, f) => kv + config.initial_held[f]);
    const n_kept = kept.reduce((a, b) => a + b, 0);
    const n_reroll = config.total_dice - state.n_skulls - n_kept;
    if (n_reroll < 0 || n_reroll === 1) continue;
    if (n_reroll > 0 && n_kept === 0) continue;
    actions.push(kept);
  }
  return actions;
}

function guardianKeptOptions(state) {
  const totalHeld = state.held.reduce((a, b) => a + b, 0);
  return subMultisets(state.held).filter(k => k.reduce((a, b) => a + b, 0) <= totalHeld - 1);
}

function addOutcome(kept, outcome) {
  const result = [...kept];
  for (let face = 1; face < NUM_FACES; face++) {
    result[face] += outcome[face];
  }
  return result;
}

function stateKey(n_skulls, held, skull_reroll_used) {
  return `${n_skulls}:${held.join(',')}:${skull_reroll_used ? 1 : 0}`;
}

function diceToState(dice, config) {
  const counts = [...config.initial_held];
  for (const f of dice) counts[f]++;
  const n_skulls = config.initial_n_skulls + counts[FACE.SKULL];
  counts[FACE.SKULL] = 0;
  return { n_skulls, held: counts, skull_reroll_used: false };
}

function computeStats(state, kept, config, sol, use_guardian = false) {
  let n_reroll, n_skulls_base;
  if (use_guardian) {
    n_reroll = (state.held.reduce((a, b) => a + b, 0) - kept.reduce((a, b) => a + b, 0)) + 1;
    n_skulls_base = state.n_skulls - 1;
  } else {
    n_reroll = config.total_dice - state.n_skulls - kept.reduce((a, b) => a + b, 0);
    n_skulls_base = state.n_skulls;
  }

  const stop_score = scoreFunc(state.n_skulls, state.held, config);

  if (n_reroll === 0) {
    return {
      kept, n_reroll: 0, use_guardian: false, stop_score,
      p_lose: 0, p_win: stop_score === WIN_SCORE ? 1 : 0,
      ev: stop_score, ev_no_lose: stop_score,
      min_score: stop_score, max_score: stop_score,
      delta_vs_stop: 0,
    };
  }

  const bust_score = config.sword_penalty ? -config.sword_penalty : 0;
  let p_lose = 0, p_win = 0, ev = 0, p_survive = 0, ev_survive = 0;
  let min_score = null, max_score = null;

  for (const { outcome, prob } of rollOutcomes(n_reroll)) {
    const new_skulls = n_skulls_base + outcome[FACE.SKULL];
    if (new_skulls >= 3) {
      // Guardian rescue on first reroll
      if (config.skull_reroll_available && !state.skull_reroll_used && !use_guardian && new_skulls === 3) {
        const base_held = addOutcome(kept, outcome);
        for (const { outcome: rOutcome, prob: rProb } of rollOutcomes(1)) {
          if (rOutcome[FACE.SKULL] > 0) {
            p_lose += prob * rProb;
            ev += prob * rProb * bust_score;
          } else {
            const rescue_held = addOutcome(base_held, rOutcome);
            const key = stateKey(2, rescue_held, true);
            const idx = sol.stateToIdx.get(key);
            if (idx === undefined) continue;
            const val = sol.V_normal[idx];
            ev += prob * rProb * val;
            p_survive += prob * rProb;
            ev_survive += prob * rProb * val;
            const nextMax = sol.max_score[idx];
            if (max_score === null || nextMax > max_score) max_score = nextMax;
            const nextStop = scoreFunc(2, rescue_held, config);
            if (nextStop === WIN_SCORE) p_win += prob * rProb;
            else if (min_score === null || nextStop < min_score) min_score = nextStop;
          }
        }
      } else {
        p_lose += prob;
        ev += prob * bust_score;
      }
    } else {
      const new_held = addOutcome(kept, outcome);
      const new_reroll_used = use_guardian ? true : state.skull_reroll_used;
      const key = stateKey(new_skulls, new_held, new_reroll_used);
      const idx = sol.stateToIdx.get(key);
      if (idx === undefined) continue;

      const val = sol.V_normal[idx];
      ev += prob * val;
      p_survive += prob;
      ev_survive += prob * val;

      const nextMax = sol.max_score[idx];
      if (max_score === null || nextMax > max_score) max_score = nextMax;

      const nextStop = scoreFunc(new_skulls, new_held, config);
      if (nextStop === WIN_SCORE) p_win += prob;
      else if (min_score === null || nextStop < min_score) min_score = nextStop;
    }
  }

  const ev_no_lose = p_survive > 0 ? ev_survive / p_survive : 0;

  return {
    kept, n_reroll, use_guardian, stop_score,
    p_lose, p_win, ev, ev_no_lose,
    min_score: min_score ?? 0,
    max_score: max_score ?? 0,
    delta_vs_stop: ev - stop_score,
  };
}

// ─── Data loading ──────────────────────────────────────────────────────────────

const _dataCache = new Map();

async function loadSolution(cardName) {
  if (_dataCache.has(cardName)) return _dataCache.get(cardName);
  const resp = await fetch(`data/${cardName}.json`);
  if (!resp.ok) throw new Error(`Failed to load data/${cardName}.json`);
  const data = await resp.json();

  // Build stateToIdx map: key → index
  const stateToIdx = new Map();
  for (let i = 0; i < data.states.length; i++) {
    const s = data.states[i];
    // s = [n_skulls, held[0..5], skull_reroll_used]
    const n_skulls = s[0];
    const held = s.slice(1, 7);
    const reroll_used = s[7];
    stateToIdx.set(stateKey(n_skulls, held, reroll_used), i);
  }

  const sol = {
    config: data.config,
    stateToIdx,
    V_normal: data.V_normal,
    max_score: data.max_score,
    stop_values: data.stop_values,
  };
  _dataCache.set(cardName, sol);
  return sol;
}

// ─── Probability helpers ───────────────────────────────────────────────────────

// P(exactly k skulls in n dice), skull prob = 1/6
function pExactSkulls(n, k) {
  if (k < 0 || k > n) return 0;
  let coeff = 1;
  for (let i = 0; i < k; i++) coeff = coeff * (n - i) / (i + 1);
  return coeff * Math.pow(1/6, k) * Math.pow(5/6, n - k);
}

// P(at least `min` skulls in n dice)
function pAtLeastSkulls(n, min) {
  if (min <= 0) return 1;
  if (min > n) return 0;
  let p = 0;
  for (let k = min; k <= n; k++) p += pExactSkulls(n, k);
  return p;
}

// ─── Formatting helpers ────────────────────────────────────────────────────────

function fmtCounts(held, includeSkull = false) {
  const parts = [];
  const start = includeSkull ? 0 : 1;
  for (let f = start; f < NUM_FACES; f++) {
    const c = held[f];
    if (c > 0) parts.push(FACE_EMOJI[f].repeat(c));
  }
  return parts.join(' ') || '—';
}

function keepStr(state, s, config) {
  const initial = config ? config.initial_held : _EMPTY_HELD;
  const base = s.n_reroll === 0 ? state.held : s.kept;
  const shown = base.map((v, f) => Math.max(0, v - initial[f]));
  return shown.some(v => v > 0) ? fmtCounts(shown) : '—';
}

function rerollStr(state, s) {
  if (s.n_reroll === 0) return '—';
  const rerolled = state.held.map((v, f) => v - s.kept[f]);
  if (s.use_guardian) rerolled[FACE.SKULL] += 1;
  return fmtCounts(rerolled, true);
}

// ─── Vue App ───────────────────────────────────────────────────────────────────

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

const app = createApp({
  setup() {
    // ── Game state ────────────────────────────────────────────────────────────
    const dice         = ref(Array(8).fill(0));          // true committed game state
    const selectedCard = ref('default');
    const mode         = ref('play');                    // 'play' | 'select'
    const selectedDice = ref(Array(8).fill(false));
    const guardianUsed = ref(false);                     // C1

    // ── Turn / animation state ────────────────────────────────────────────────
    // 'idle'          → fresh page load: blank card back + blank dice
    // 'card_revealed' → card flipped, waiting for user to click "Roll Dice!"
    // 'rolling'       → dice animating (all buttons disabled)
    // 'active'        → dice settled, normal play
    const turnPhase   = ref('idle');
    const displayDice = ref(Array(8).fill(FACE_BLANK)); // visually shown faces
    const isAnimating  = ref(false);
    const displayCard  = ref(null); // null = card back; string = card value being shown

    // ── Strategy state ────────────────────────────────────────────────────────
    const loading      = ref(false);
    const error        = ref(null);
    const strategyData = ref(null); // null = not yet computed; cleared when dice/card change
    const strategyOn   = ref(false);  // A4: toggle — controls die highlights + banner
    const modalOpen    = ref(false);  // A4: details modal

    const anySelected = computed(() => selectedDice.value.some(Boolean));
    const selectedCount = computed(() => selectedDice.value.filter(Boolean).length);

    // Current card option object (for the card tile display)
    // Card shown on the tile right now (cycles during animation, null = back of card)
    const displayCardOption = computed(() =>
      displayCard.value === null
        ? null
        : (CARD_OPTIONS.find(o => o.value === displayCard.value) ?? CARD_OPTIONS[0])
    );

    // A2: card selector locked in play mode once a turn has started
    const cardLocked = computed(() => mode.value === 'play' && turnPhase.value !== 'idle');

    // Returns a human-readable reason string when the current selection is an
    // invalid reroll (solver forbids n_reroll=1 and n_kept_variable=0).
    // Returns null when the selection is fine (or when nothing is selected yet).
    //
    // Note: the fixed card die (coin/diamond) is intentionally NOT counted as
    // a "kept die" here — the user must keep at least one of their own 8 dice.
    const rollInvalidReason = computed(() => {
      if (!anySelected.value) return null;
      // Exactly one die selected → n_reroll=1, always forbidden.
      if (selectedCount.value === 1) {
        return "Can't reroll a single die — select at least 2";
      }
      // "Keeping nothing" check: count only variable dice (the 8 in dice.value).
      // The fixed card die is always kept automatically and does not count.
      const n_nonSkull_selected = selectedDice.value
        .filter((sel, i) => sel && dice.value[i] !== FACE.SKULL).length;
      const n_nonSkull_total = dice.value.filter(f => f !== FACE.SKULL).length;
      if (n_nonSkull_total > 0 && n_nonSkull_selected === n_nonSkull_total) {
        return "Can't reroll every die — keep at least one";
      }
      return null;
    });

    // B1: probability of immediately busting on the next roll given the current
    // selection. null when no dice are selected, the state is already busted,
    // or the selection is invalid.
    const bustProbability = computed(() => {
      if (mode.value !== 'play' || turnPhase.value !== 'active' || !anySelected.value || !!rollInvalidReason.value) return null;
      const config = CARD_CONFIGS[selectedCard.value] ?? CARD_CONFIGS['default'];
      const state = diceToState(dice.value, config);
      if (state.n_skulls >= 3) return null;
      // Guardian reroll: the selected skull is removed before rolling, so
      // we start with one fewer skull in the base count.
      const skullSelected = selectedDice.value.some((sel, i) => sel && dice.value[i] === FACE.SKULL);
      const n_skulls_base = state.n_skulls - (skullSelected ? 1 : 0);
      const skulls_needed = 3 - n_skulls_base;
      return pAtLeastSkulls(selectedCount.value, skulls_needed);
    });

    // A4: true when strategy is loaded and the best action is "stop".
    const bestStrategyIsStop = computed(() => {
      if (!strategyOn.value || !strategyData.value?.stats) return false;
      return strategyData.value.stats[0].n_reroll === 0;
    });

    // A4: Set of die indices (into dice.value) that the best strategy wants rerolled.
    // Empty when strategy is off, busted/win, or the recommendation is "stop".
    const bestStrategyRerollIndices = computed(() => {
      if (!strategyOn.value || !strategyData.value?.stats) return new Set();
      const best = strategyData.value.stats[0];
      if (best.n_reroll === 0) return new Set();

      const state = strategyData.value.state;
      // Per-face count of dice to reroll (variable dice only; held[SKULL] is always 0).
      const remaining = state.held.map((h, f) => h - best.kept[f]);
      let skullsToReroll = best.use_guardian ? 1 : 0;

      const rerollSet = new Set();
      for (let i = 0; i < dice.value.length; i++) {
        const f = dice.value[i];
        if (f === FACE.SKULL && skullsToReroll > 0) {
          rerollSet.add(i); skullsToReroll--;
        } else if (f !== FACE.SKULL && remaining[f] > 0) {
          rerollSet.add(i); remaining[f]--;
        }
      }
      return rerollSet;
    });

    function _clearStrategy() {
      strategyData.value = null;
      strategyOn.value = false;
      modalOpen.value = false;
    }

    function setMode(m) {
      mode.value = m;
      selectedDice.value = Array(8).fill(false);
      guardianUsed.value = false;
      _clearStrategy();
      if (m === 'select') {
        // Sync visual display with committed values when entering edit mode
        displayDice.value = [...dice.value];
        displayCard.value = selectedCard.value;
      }
    }

    // Returns true if die i can be toggled for re-roll in play mode.
    // Skulls are locked unless the guardian card is active (then at most one skull,
    // and only if the Guardian's reroll hasn't been used yet).
    function isDieSelectable(i) {
      if (mode.value !== 'play') return true;
      if (currentScore.value.busted) return false;
      if (dice.value[i] !== FACE.SKULL) return true;
      if (selectedCard.value !== 'guardian') return false;
      // C1: Guardian reroll already consumed → treat skulls as locked again.
      if (guardianUsed.value) return false;
      // Guardian: this skull is selectable only if it is already selected,
      // or no other skull die is currently selected.
      if (selectedDice.value[i]) return true;
      return !dice.value.some((f, j) => f === FACE.SKULL && selectedDice.value[j]);
    }

    function interactDie(i) {
      // Silently ignore clicks during animation or while dice haven't been rolled yet
      if (isAnimating.value || displayDice.value[i] === FACE_BLANK) return;
      if (mode.value === 'play') {
        if (!isDieSelectable(i)) return;
        selectedDice.value[i] = !selectedDice.value[i];
      } else {
        dice.value[i] = (dice.value[i] + 1) % NUM_FACES;
        displayDice.value[i] = dice.value[i]; // keep display in sync
        _clearStrategy();
      }
    }

    // ── Animation engine ──────────────────────────────────────────────────────

    // Slot-machine animation for a single die.
    // Rapidly cycles through random faces (fast → decelerate → settle).
    // startDelay: ms to wait before starting; perDieMs: total cycle duration.
    async function _animateSingleDie(idx, finalFace, startDelay, perDieMs) {
      if (startDelay > 0) await sleep(startDelay);

      // Build schedule: fast ticks → progressively slower ticks
      const MIN_IV  = 55;   // fastest tick interval (ms)
      const MAX_IV  = 190;  // slowest tick before settling (ms)
      const schedule = [];
      let elapsed = 0;
      const fastEnd = perDieMs * 0.62;

      // Fast phase
      while (elapsed < fastEnd) {
        schedule.push(MIN_IV);
        elapsed += MIN_IV;
      }
      // Deceleration phase
      let iv = MIN_IV;
      while (elapsed < perDieMs - MAX_IV) {
        iv = Math.min(Math.round(iv * 1.5), MAX_IV);
        schedule.push(iv);
        elapsed += iv;
      }

      // Run cycles (all show random faces)
      for (const interval of schedule) {
        displayDice.value[idx] = Math.floor(Math.random() * NUM_FACES);
        await sleep(interval);
      }

      // Settle on final face
      displayDice.value[idx] = finalFace;
    }

    // Animate a set of dice.
    // diceToRoll: [{idx, finalFace}, ...]
    // perDieMs:   how long each die's slot-machine runs
    // staggerMs:  delay between successive dice starts (0 = all simultaneous)
    // When staggerMs > 0 the order is randomised for a pleasing cascade effect.
    async function _animateDiceRoll(diceToRoll, perDieMs, staggerMs = 0) {
      const order = [...diceToRoll];
      if (staggerMs > 0) {
        // Shuffle for random settle order
        for (let i = order.length - 1; i > 0; i--) {
          const j = Math.floor(Math.random() * (i + 1));
          [order[i], order[j]] = [order[j], order[i]];
        }
      }
      await Promise.all(
        order.map(({ idx, finalFace }, i) =>
          _animateSingleDie(idx, finalFace, i * staggerMs, perDieMs)
        )
      );
    }

    // ── Turn flow ─────────────────────────────────────────────────────────────

    // Slot-machine reveal for the bonus card: rapidly cycles through card icons
    // then settles on the actual drawn card (same deceleration pattern as dice).
    async function _animateCardReveal() {
      const cyclePool = CARD_OPTIONS.filter(o => o.value !== 'default');
      displayCard.value = null; // show card back briefly
      await sleep(160);

      const MIN_IV = 65, MAX_IV = 220, TOTAL_MS = 1050;
      const schedule = [];
      let elapsed = 0;
      while (elapsed < TOTAL_MS * 0.65) { schedule.push(MIN_IV); elapsed += MIN_IV; }
      let iv = MIN_IV;
      while (elapsed < TOTAL_MS - MAX_IV) {
        iv = Math.min(Math.round(iv * 1.5), MAX_IV);
        schedule.push(iv); elapsed += iv;
      }

      for (const interval of schedule) {
        displayCard.value = cyclePool[Math.floor(Math.random() * cyclePool.length)].value;
        await sleep(interval);
      }
      displayCard.value = selectedCard.value; // settle on drawn card
    }

    // Step 1 of a new turn: draw and reveal the bonus card, then wait for the
    // user to click "Roll Dice!".
    async function startNewTurn() {
      if (isAnimating.value) return;
      isAnimating.value = true;
      turnPhase.value = 'card_revealed';
      mode.value = 'play';
      guardianUsed.value = false;
      selectedDice.value = Array(8).fill(false);
      _clearStrategy();

      displayDice.value = Array(8).fill(FACE_BLANK);
      selectedCard.value = randomCard();

      await _animateCardReveal();

      isAnimating.value = false;
      // turnPhase remains 'card_revealed' — "Roll Dice!" button now appears
    }

    // Step 2: roll all 8 dice with slot-machine animation, staggered (~2 s total).
    async function rollInitialDice() {
      if (isAnimating.value) return;
      isAnimating.value = true;
      turnPhase.value = 'rolling';

      const finalDice = randomDice();
      dice.value = finalDice;

      // perDie = 900 ms, stagger = 150 ms → last die starts at 7×150=1050ms, ends at 1950ms ≈ 2s
      await _animateDiceRoll(
        finalDice.map((finalFace, idx) => ({ idx, finalFace })),
        900, 150
      );

      displayDice.value = [...finalDice]; // safety flush
      turnPhase.value = 'active';
      isAnimating.value = false;
    }

    async function rollSelected() {
      // C1: detect guardian skull reroll before overwriting dice.
      const skullWasSelected = selectedDice.value.some(
        (sel, i) => sel && dice.value[i] === FACE.SKULL
      );
      if (selectedCard.value === 'guardian' && skullWasSelected) {
        guardianUsed.value = true;
        // The Guardian card is now spent — switch to "no card" so the solver
        // computes the correct strategy for the remainder of the turn.
        selectedCard.value = 'default';
      }

      // Compute final values and commit to game state immediately
      const newDice = [...dice.value];
      const diceToRoll = [];
      for (let i = 0; i < newDice.length; i++) {
        if (selectedDice.value[i]) {
          const finalFace = Math.floor(Math.random() * NUM_FACES);
          newDice[i] = finalFace;
          diceToRoll.push({ idx: i, finalFace });
        }
      }
      dice.value = newDice;
      selectedDice.value = Array(8).fill(false);
      _clearStrategy();

      isAnimating.value = true;
      // All selected dice animate simultaneously (staggerMs = 0), ~900 ms each
      await _animateDiceRoll(diceToRoll, 900, 0);
      displayDice.value = [...dice.value]; // safety flush
      isAnimating.value = false;
    }

    // Sort priority per face: skull, coin, diamond, sword, monkey, parrot
    const _REORDER_PRIORITY = [0, 3, 1, 2, 4, 5]; // index = FACE value

    function reorderDice() {
      const pairs = dice.value.map((face, i) => ({ face, selected: selectedDice.value[i] }));
      pairs.sort((a, b) => _REORDER_PRIORITY[a.face] - _REORDER_PRIORITY[b.face]);
      dice.value = pairs.map(p => p.face);
      displayDice.value = [...dice.value]; // keep display in sync
      selectedDice.value = pairs.map(p => p.selected);
    }

    function onCardChange() {
      _clearStrategy();
      displayCard.value = selectedCard.value; // keep tile in sync in edit mode
    }

    // Edit-mode instant randomise (no animation)
    function randomize() {
      dice.value = randomDice();
      displayDice.value = [...dice.value];
      selectedCard.value = randomCard();
      displayCard.value = selectedCard.value;
      selectedDice.value = Array(8).fill(false);
      guardianUsed.value = false;
      _clearStrategy();
    }

    const currentScore = computed(() => {
      const config = CARD_CONFIGS[selectedCard.value] ?? CARD_CONFIGS['default'];
      const state = diceToState(dice.value, config);
      if (state.n_skulls >= 3) return { busted: true };
      const score = scoreFunc(state.n_skulls, state.held, config);
      if (score === WIN_SCORE) return { win: true };

      // A5: detect whether the +500 full-chest bonus is active right now.
      // Mirror the exact condition used in scoreFunc; guard with score > 0
      // so we never show the badge on pirate-ship penalty states.
      // The Pirate card doubles the bonus (500 × multiplier).
      let fullChest = false;
      const fullChestBonus = 500 * config.score_multiplier;
      if (score > 0 && state.n_skulls === 0) {
        const totalHeld = state.held.reduce((a, b) => a + b, 0);
        if (totalHeld === config.total_dice) {
          if (config.merge_animals) {
            const animals = state.held[FACE.MONKEY] + state.held[FACE.PARROT];
            fullChest = (state.held[FACE.SWORD] === 0 || state.held[FACE.SWORD] >= 3) &&
                        (animals === 0 || animals >= 3);
          } else {
            fullChest = [FACE.SWORD, FACE.COIN, FACE.DIAMOND, FACE.MONKEY, FACE.PARROT]
              .every(f => state.held[f] === 0 || state.held[f] >= 3
                       || f === FACE.COIN || f === FACE.DIAMOND);
          }
        }
      }

      // A6: pirate-ship contract status (null when card is not a pirate-ship card).
      const pirateShip = config.required_swords > 0 ? {
        met:      state.held[FACE.SWORD] >= config.required_swords,
        swords:   state.held[FACE.SWORD],
        required: config.required_swords,
        bonus:    config.sword_bonus,
      } : null;

      return { score, fullChest, fullChestBonus, pirateShip };
    });

    // Fixed card dice to display alongside the 8 interactive dice
    const fixedCardDice = computed(() => {
      const card = selectedCard.value;
      const fixed = [];
      if (card === 'skull-1') fixed.push(...Array(1).fill(FACE.SKULL));
      if (card === 'skull-2') fixed.push(...Array(2).fill(FACE.SKULL));
      if (card === 'coin') fixed.push(FACE.COIN);
      if (card === 'diamond') fixed.push(FACE.DIAMOND);
      return fixed;
    });

    // Internal: fetch + compute, populate strategyData. Does NOT touch strategyOn.
    async function _loadStrategy() {
      loading.value = true;
      error.value = null;
      strategyData.value = null;

      try {
        const sol = await loadSolution(selectedCard.value);
        const config = sol.config;
        const state = diceToState(dice.value, config);

        if (state.n_skulls >= 3) {
          strategyData.value = { busted: true, n_skulls: state.n_skulls, config };
          return;
        }

        const stopScore = scoreFunc(state.n_skulls, state.held, config);

        if (stopScore === WIN_SCORE) {
          strategyData.value = { win: true, config };
          return;
        }

        const actions = validActions(state, config);
        let allStats = actions.map(kept => computeStats(state, kept, config, sol));

        if (config.skull_reroll_available && !state.skull_reroll_used && state.n_skulls >= 1) {
          const guardianOptions = guardianKeptOptions(state);
          allStats = allStats.concat(
            guardianOptions.map(kept => computeStats(state, kept, config, sol, true))
          );
        }

        allStats.sort((a, b) => {
          const evDiff = b.ev - a.ev;
          return Math.abs(evDiff) < 1e-9 ? a.p_lose - b.p_lose : evDiff;
        });

        strategyData.value = {
          state,
          config,
          stats: allStats,
          anyWinPossible: allStats.some(s => s.p_win > 0),
          stopScore,
        };
      } catch (e) {
        error.value = e.message;
      } finally {
        loading.value = false;
      }
    }

    // A4: toggle strategy on/off. Lazy-loads data on first activation.
    async function toggleStrategy() {
      if (strategyOn.value) {
        strategyOn.value = false;
        modalOpen.value = false;
        return;
      }
      if (!strategyData.value) {
        await _loadStrategy();
      }
      if (strategyData.value && !error.value) {
        strategyOn.value = true;
      }
    }

    function rowMarker(i, s) {
      const isStop = s.n_reroll === 0;
      const isBest = i === 0;
      if (isStop && isBest) return '🛑⭐';
      if (isStop) return '🛑';
      if (isBest) return '⭐';
      return String(i + 1);
    }

    function rowClass(i, s) {
      const isStop = s.n_reroll === 0;
      const isBest = i === 0;
      if (isBest) return 'row-best';
      if (isStop) return 'row-stop';
      return '';
    }

    function pct(v) { return (v * 100).toFixed(1) + '%'; }
    function evFmt(v) { return v.toFixed(1); }
    function deltaFmt(v) { return (v >= 0 ? '+' : '') + v.toFixed(1); }

    function maxStr(s) {
      return s.max_score >= WIN_SCORE ? 'WIN' : String(s.max_score);
    }

    return {
      dice, selectedCard, loading, error,
      strategyData, strategyOn, modalOpen,
      bestStrategyIsStop, bestStrategyRerollIndices,
      FACE_EMOJI, FACE_NAMES, CARD_OPTIONS, FACE_BLANK,
      mode, selectedDice, anySelected, selectedCount, rollInvalidReason, bustProbability,
      cardLocked, guardianUsed,
      // A7: animation state
      turnPhase, displayDice, isAnimating, displayCard, displayCardOption,
      setMode, interactDie, rollSelected, isDieSelectable, reorderDice,
      onCardChange, toggleStrategy, randomize,
      startNewTurn, rollInitialDice,
      keepStr, rerollStr, rowMarker, rowClass,
      pct, evFmt, deltaFmt, maxStr,
      fixedCardDice, currentScore, WIN_SCORE, FACE,
    };
  },
});

app.mount('#app');
