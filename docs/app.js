import { createApp, ref, computed, reactive } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.prod.js';

// ─── Constants ────────────────────────────────────────────────────────────────

const FACE = { SKULL: 0, SWORD: 1, COIN: 2, DIAMOND: 3, MONKEY: 4, PARROT: 5 };
const NUM_FACES = 6;
const WIN_SCORE = 1_000_000;

const FACE_EMOJI = ['💀', '⚔️', '🪙', '💎', '🐒', '🦜'];
const FACE_NAMES = ['Skull', 'Sword', 'Coin', 'Diamond', 'Monkey', 'Parrot'];

const COMBO_SCORE = { 3: 100, 4: 200, 5: 500, 6: 1000, 7: 2000, 8: 4000 };

const CARD_OPTIONS = [
  { value: 'default',      label: 'No card',                         icon: '🎲' },
  { value: 'skull-1',      label: 'Skull card (1 skull locked)',      icon: '💀' },
  { value: 'skull-2',      label: 'Skull card (2 skulls locked)',     icon: '💀💀' },
  { value: 'coin',         label: 'Treasure: Coin (+1 coin die)',     icon: '🪙' },
  { value: 'diamond',      label: 'Treasure: Diamond (+1 diamond die)', icon: '💎' },
  { value: 'animals',      label: 'Animals (monkeys = parrots)',      icon: '🐒🦜' },
  { value: 'pirate',       label: 'Pirate (×2 score)',                icon: '🏴‍☠️' },
  { value: 'guardian',     label: 'Guardian (reroll 1 skull once)',   icon: '🛡️' },
  { value: 'pirate-ship-2', label: 'Pirate Ship (≥2 ⚔️, +300/−300)', icon: '⚓' },
  { value: 'pirate-ship-3', label: 'Pirate Ship (≥3 ⚔️, +500/−500)', icon: '⚓' },
  { value: 'pirate-ship-4', label: 'Pirate Ship (≥4 ⚔️, +1000/−1000)', icon: '⚓' },
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

const app = createApp({
  setup() {
    const dice = ref(randomDice());
    const selectedCard = ref(randomCard());
    const loading = ref(false);
    const error = ref(null);
    const strategyData = ref(null); // null = not yet computed; cleared when dice/card change
    const strategyOn   = ref(false);  // A4: toggle — controls die highlights + banner
    const modalOpen    = ref(false);  // A4: details modal

    const mode = ref('play'); // 'play' | 'select'
    const selectedDice = ref(Array(8).fill(false));
    const anySelected = computed(() => selectedDice.value.some(Boolean));
    const selectedCount = computed(() => selectedDice.value.filter(Boolean).length);

    // A2: card selector is locked whenever we are in play mode.
    const cardLocked = computed(() => mode.value === 'play');

    // C1: true once the Guardian's one-time skull reroll has been consumed.
    const guardianUsed = ref(false);

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
      if (mode.value !== 'play' || !anySelected.value || !!rollInvalidReason.value) return null;
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
      if (mode.value === 'play') {
        if (!isDieSelectable(i)) return;
        selectedDice.value[i] = !selectedDice.value[i];
      } else {
        dice.value[i] = (dice.value[i] + 1) % NUM_FACES;
        _clearStrategy();
      }
    }

    function rollSelected() {
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

      const newDice = [...dice.value];
      for (let i = 0; i < newDice.length; i++) {
        if (selectedDice.value[i]) newDice[i] = Math.floor(Math.random() * NUM_FACES);
      }
      dice.value = newDice;
      selectedDice.value = Array(8).fill(false);
      _clearStrategy();
    }

    // Sort priority per face: skull, coin, diamond, sword, monkey, parrot
    const _REORDER_PRIORITY = [0, 3, 1, 2, 4, 5]; // index = FACE value

    function reorderDice() {
      const pairs = dice.value.map((face, i) => ({ face, selected: selectedDice.value[i] }));
      pairs.sort((a, b) => _REORDER_PRIORITY[a.face] - _REORDER_PRIORITY[b.face]);
      dice.value = pairs.map(p => p.face);
      selectedDice.value = pairs.map(p => p.selected);
    }

    function onCardChange() {
      _clearStrategy();
    }

    function randomize() {
      dice.value = randomDice();
      selectedCard.value = randomCard();
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
      return { score };
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

        allStats.sort((a, b) => b.ev - a.ev);

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
      FACE_EMOJI, FACE_NAMES, CARD_OPTIONS,
      mode, selectedDice, anySelected, selectedCount, rollInvalidReason, bustProbability,
      cardLocked, guardianUsed,
      setMode, interactDie, rollSelected, isDieSelectable, reorderDice,
      onCardChange, toggleStrategy, randomize,
      keepStr, rerollStr, rowMarker, rowClass,
      pct, evFmt, deltaFmt, maxStr,
      fixedCardDice, currentScore, WIN_SCORE, FACE,
    };
  },
});

app.mount('#app');
