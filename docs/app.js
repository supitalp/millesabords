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

// Default initial dice: skull skull monkey monkey sword sword coin diamond
const DEFAULT_DICE = [0, 0, 4, 4, 1, 1, 2, 3];

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
  const heldNonSkull = [...state.held];
  heldNonSkull[FACE.SKULL] = 0;

  for (const kept of subMultisets(heldNonSkull)) {
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

function keepStr(state, s) {
  if (s.n_reroll === 0) return fmtCounts(state.held);
  return s.kept.some(v => v > 0) ? fmtCounts(s.kept) : '—';
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
    const dice = ref([...DEFAULT_DICE]);
    const selectedCard = ref('default');
    const loading = ref(false);
    const error = ref(null);
    const results = ref(null);  // null = not computed yet

    // Config for the currently selected card (from loaded data)
    const currentConfig = ref(null);

    function cycleDie(i) {
      dice.value[i] = (dice.value[i] + 1) % NUM_FACES;
      results.value = null; // clear results when dice change
    }

    function onCardChange() {
      results.value = null;
    }

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

    async function showResults() {
      loading.value = true;
      error.value = null;
      results.value = null;

      try {
        const sol = await loadSolution(selectedCard.value);
        const config = sol.config;

        const state = diceToState(dice.value, config);

        // Check for instant bust
        if (state.n_skulls >= 3) {
          results.value = { busted: true, n_skulls: state.n_skulls, config };
          return;
        }

        const stopScore = scoreFunc(state.n_skulls, state.held, config);

        // Check for instant win
        if (stopScore === WIN_SCORE) {
          results.value = { win: true, config };
          return;
        }

        // Compute stats for all valid actions
        const actions = validActions(state, config);
        let allStats = actions.map(kept => computeStats(state, kept, config, sol));

        // Guardian: add skull-reroll options
        if (config.skull_reroll_available && !state.skull_reroll_used && state.n_skulls >= 1) {
          const guardianOptions = guardianKeptOptions(state);
          allStats = allStats.concat(
            guardianOptions.map(kept => computeStats(state, kept, config, sol, true))
          );
        }

        allStats.sort((a, b) => b.ev - a.ev);

        const anyWinPossible = allStats.some(s => s.p_win > 0);

        results.value = {
          state,
          config,
          stats: allStats,
          anyWinPossible,
          stopScore,
        };
      } catch (e) {
        error.value = e.message;
      } finally {
        loading.value = false;
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
      dice, selectedCard, loading, error, results,
      FACE_EMOJI, FACE_NAMES, CARD_OPTIONS,
      cycleDie, onCardChange, showResults,
      keepStr, rerollStr, rowMarker, rowClass,
      pct, evFmt, deltaFmt, maxStr,
      fixedCardDice, WIN_SCORE, FACE,
    };
  },
});

app.mount('#app');
