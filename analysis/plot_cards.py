#!/usr/bin/env python3
"""
plot_cards.py — Simulate all special cards (+ no card) under the optimal DP policy
and plot their score distributions as individual KDE plots, all sharing the same
X (score) and Y (density) axes for easy comparison.

Simulation results are saved to results/<card>.npy and reused across runs.

Usage:
    uv run python analysis/plot_cards.py [--n N] [--seed SEED] [--force] [--plot-only]
                                         [--out-dir DIR]

Options:
    --n N           Number of turns to simulate per card (default: 200000).
    --seed SEED     Random seed for reproducibility.
    --force         Re-run simulations even if .npy files already exist.
    --plot-only     Skip simulation entirely; load existing .npy files and plot.
    --out-dir DIR   Directory for output images (default: results/plots/).
"""
import argparse
import random
from pathlib import Path

import numpy as np

from solver.model import CARD_CONFIGS, DEFAULT_CONFIG
from solver.dp import get_solution
from analysis.simulate import simulate

RESULTS_DIR = Path("results")

ALL_CARDS: list[tuple[str, str]] = [
    # Ordered worst → best by expected value (EV), so heatmap rows read top=worst, bottom=best.
    ("ship ×4",        "pirate-ship-4"),   # EV  −156 pts
    ("skull ×2",       "skull-2"),          # EV   113 pts
    ("ship ×3",        "pirate-ship-3"),   # EV   249 pts
    ("skull ×1",       "skull-1"),          # EV   346 pts
    ("ship ×2",        "pirate-ship-2"),   # EV   443 pts
    ("no card",        ""),                 # EV   579 pts
    ("treasure island","treasure-island"), # EV   680 pts
    ("animals",        "animals"),          # EV   735 pts
    ("diamond",        "diamond"),          # EV   784 pts
    ("coin",           "coin"),             # EV   784 pts
    ("guardian",       "guardian"),         # EV   906 pts
    ("pirate ×2",      "pirate"),           # EV  1158 pts
]


def npy_path(card_key: str) -> Path:
    return RESULTS_DIR / ((card_key or "no_card").replace("-", "_") + ".npy")


def run_simulation(label: str, card_key: str, n: int, seed: int | None) -> np.ndarray:
    config = CARD_CONFIGS[card_key] if card_key else DEFAULT_CONFIG
    print(f"  [{label}] Loading DP solution...", end=" ", flush=True)
    get_solution(config)
    print("done.")

    rng = random.Random(seed)
    scores: list[float] = []
    print(f"  [{label}] Simulating {n:,} turns...", end=" ", flush=True)
    for _ in range(n):
        scores.append(simulate(config, rng, card_name=label, verbose=False))
    arr = np.array(scores, dtype=np.float32)
    print("done.")

    out = npy_path(card_key)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.save(out, arr)
    print(f"  [{label}] Saved → {out}")
    return arr


def load_or_simulate(label: str, card_key: str, n: int, seed: int | None,
                     force: bool, plot_only: bool) -> np.ndarray | None:
    path = npy_path(card_key)
    if not force and path.exists():
        arr = np.load(path)
        print(f"  [{label}] Loaded {len(arr):,} scores from {path}")
        return arr
    if plot_only:
        print(f"  [{label}] WARNING: {path} not found — skipping.")
        return None
    return run_simulation(label, card_key, n, seed)


def _npy_stem(card_key: str) -> str:
    return (card_key or "no_card").replace("-", "_")


COLORMAPS = ["viridis", "plasma", "magma", "inferno", "YlOrRd", "Blues"]


def _score_freq_table(
    datasets: list[tuple[str, str, np.ndarray]],
    percentile: float = 98,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Return (vals, matrix) where:
      vals   — sorted array of all realized score values (integers, multiples of 100)
               clipped at the 99th-percentile on the right to drop extreme outliers.
      matrix — shape (n_cards, n_vals), each row sums to ≤ 1 (frequencies; scores
               beyond the 99th-pct cutoff are excluded from each row independently).
    """
    all_scores = np.concatenate([arr for _, _, arr in datasets])
    x_min = int(np.floor(all_scores.min() / 100) * 100)
    x_max = int(np.floor(np.percentile(all_scores, percentile) / 100) * 100)

    # Uniform grid: every multiple of 100 between min and max, regardless of
    # whether that exact score is achievable (gaps will just show frequency 0).
    vals = np.arange(x_min, x_max + 100, 100, dtype=int)

    n = len(datasets[0][2])
    matrix = np.zeros((len(datasets), len(vals)), dtype=np.float32)
    for i, (_, _, arr) in enumerate(datasets):
        unique, counts = np.unique(arr.astype(int), return_counts=True)
        freq = dict(zip(unique.tolist(), counts.tolist()))
        for j, v in enumerate(vals):
            matrix[i, j] = freq.get(int(v), 0) / n

    return vals, matrix


def pmf_all(datasets: list[tuple[str, str, np.ndarray]], out_dir: Path) -> None:
    """
    One PMF bar chart per card (one bar per realizable score value), all sharing
    the same X and Y axes so cards are directly comparable.
    """
    import matplotlib.pyplot as plt
    import seaborn as sns

    out_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", font_scale=1.1)
    palette = sns.color_palette("tab10", n_colors=len(datasets))

    vals, matrix = _score_freq_table(datasets)

    x_lim  = (int(vals[0]) - 150, int(vals[-1]) + 150)
    y_lim  = (0, float(matrix.max()) * 1.12)

    saved: list[Path] = []
    for idx, ((label, card_key, arr), color) in enumerate(zip(datasets, palette)):
        bust_rate = float((arr <= 0).mean())
        mu        = float(arr.mean())
        freqs     = matrix[idx]

        fig, ax = plt.subplots(figsize=(14, 5))
        ax.bar(vals, freqs, width=80, color=color, alpha=0.85, edgecolor="none")

        ax.set_xlim(*x_lim)
        ax.set_ylim(*y_lim)
        ax.set_xlabel("Score (pts)", fontsize=12)
        ax.set_ylabel("Frequency", fontsize=12)
        ax.set_title(
            f"{label}  —  μ = {mu:.0f} pts  |  bust = {bust_rate:.1%}",
            fontsize=13, pad=10,
        )

        fig.tight_layout()
        out = out_dir / f"{_npy_stem(card_key)}_pmf.png"
        fig.savefig(out, dpi=150)
        plt.close(fig)
        saved.append(out)
        print(f"  [{label}] PMF saved → {out}")

    print(f"\n  {len(saved)} PMF plots written to {out_dir}/")



def heatmap_all(
    datasets: list[tuple[str, str, np.ndarray]],
    out_dir: Path,
    percentile: float = 98,
    cmap: str = "viridis",
    ev_color: str = "white",
    log_scale: bool = False,
) -> None:
    """
    Single heatmap: rows = cards (worst EV at top, best at bottom), columns =
    score values (multiples of 100), colour = log-frequency.

    A white tick mark on each row shows that card's empirical mean (EV).
    """
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)

    vals, matrix = _score_freq_table(datasets, percentile=percentile)
    text_labels = [label for label, _, _ in datasets]
    n_cards = len(datasets)

    row_edges = np.arange(n_cards + 1, dtype=float)

    # Column edges: uniform 100-pt bins.
    edges = np.empty(len(vals) + 1)
    # Left-edge convention: bin for score v spans [v, v+100).
    # Ticks at vals are then exactly at left edges, so the EV marker
    # (drawn at the raw mean) aligns correctly within its bin.
    edges[:-1] = vals
    edges[-1]  = vals[-1] + 100

    plot_matrix = np.log1p(matrix * 1000) if log_scale else matrix

    fig, ax = plt.subplots(figsize=(16, 6))

    ax.pcolormesh(edges, row_edges, plot_matrix, cmap=cmap, shading="flat")

    # Worst card (index 0 in ALL_CARDS) at the top.
    ax.invert_yaxis()

    # ── EV markers: white vertical tick at the empirical mean for each row ────
    for i, (_, _, arr) in enumerate(datasets):
        mu = float(arr.mean())
        row_center = i + 0.5
        ax.plot(
            [mu, mu], [row_center - 0.38, row_center + 0.38],
            color=ev_color, linewidth=2.0, solid_capstyle="round",
        )

    # ── X ticks: every 100 pts ────────────────────────────────────────────────
    ax.set_xticks(vals)
    ax.set_xticklabels([str(int(v)) for v in vals], rotation=90, ha="center", fontsize=6)
    ax.set_xlim(edges[0], edges[-1])

    # ── Y ticks: text card labels ─────────────────────────────────────────────
    ax.set_yticks(np.arange(n_cards) + 0.5)
    ax.set_yticklabels(text_labels, fontsize=11)
    ax.set_ylim(n_cards, 0)

    ax.set_xlabel(f"Score (pts, up to {percentile:.1f}th percentile)", fontsize=11, labelpad=8)
    ax.set_ylabel("")
    scale_label = "log-frequency" if log_scale else "frequency"
    ax.set_title(
        f"Score distributions — all cards  |  optimal strategy  |  {scale_label}  |  {ev_color} bar = EV",
        fontsize=12, pad=12,
    )

    fig.tight_layout()
    out = out_dir / "heatmap_all_cards.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Heatmap saved → {out}")


def ridgeline_all(
    datasets: list[tuple[str, str, np.ndarray]],
    out_dir: Path,
    percentile: float = 98,
    overlap: float = 2.0,
) -> None:
    """
    Ridgeline (Joy Plot) — discrete step-fill PMF per card, stacked with overlap.
    Bust zone (score ≤ 0) rendered in a uniform dark red across all rows.
    EV marker uses a dark halo so it reads against both dark and bright ridges.
    """
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    import matplotlib.patheffects as pe

    out_dir.mkdir(parents=True, exist_ok=True)

    n_cards  = len(datasets)
    BG       = "#0d0d10"
    BUST_CLR = "#8b1a1a"   # uniform dark-red for score ≤ 0 across all cards

    # ── x grid ────────────────────────────────────────────────────────────────
    all_scores = np.concatenate([arr for _, _, arr in datasets])
    x_min = int(np.floor(np.percentile(all_scores, 0.5) / 100) * 100)
    x_max = int(np.floor(np.percentile(all_scores, percentile) / 100) * 100)
    bin_edges = np.arange(x_min - 50, x_max + 150, 100)
    centers   = (bin_edges[:-1] + bin_edges[1:]) / 2.0   # at multiples of 100

    # ── raw PMF per card, normalised by global 95th-percentile cap ───────────
    # Collect every non-zero bar height across all cards, take the 95th
    # percentile as the shared scale cap.  Extreme spikes (e.g. ship×4 bust)
    # are clipped to 1.0 so they don't dwarf the rest of each distribution.
    all_freqs: list[np.ndarray] = []
    for _, _, arr in datasets:
        counts, _ = np.histogram(arr, bins=bin_edges, density=False)
        all_freqs.append(counts.astype(float) / len(arr))

    nonzero = np.concatenate(all_freqs)
    nonzero = nonzero[nonzero > 0]
    cap     = float(np.percentile(nonzero, 95))   # shared normalisation factor
    # Round cap up to the nearest clean 1 % for a legible legend
    cap_display = np.ceil(cap * 100) / 100

    ridges: list[np.ndarray] = []
    evs:    list[float]      = []
    for freq, (_, _, arr) in zip(all_freqs, datasets):
        ridges.append(np.clip(freq / cap, 0.0, 1.0))
        evs.append(float(arr.mean()))

    # ── layout ────────────────────────────────────────────────────────────────
    row_step    = 1.0 / overlap
    total_yspan = (n_cards - 1) * row_step + 1.0

    fig_w, fig_h = 18, max(9, n_cards * 1.15)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # plasma gradient, worst (i=0) = dark purple, best (i=n-1) = bright yellow
    cmap   = plt.colormaps["plasma"]
    colors = [cmap(0.10 + 0.82 * i / max(n_cards - 1, 1)) for i in range(n_cards)]

    bust_mask = centers <= 0     # bins in the bust / penalty zone
    pos_mask  = centers > 0

    # Draw worst (i=0) first so best (i=n-1) renders on top
    for i, ((label, card_key, arr), ridge, color, mu) in enumerate(
        zip(datasets, ridges, colors, evs)
    ):
        y_base = (n_cards - 1 - i) * row_step   # row 0 (worst) = top = largest y

        # Bust zone (≤ 0): uniform dark red
        r_bust = np.where(bust_mask, ridge, 0.0)
        ax.fill_between(centers, y_base, y_base + r_bust,
                        step="mid", color=BUST_CLR, alpha=0.80,
                        linewidth=0, zorder=i)

        # Positive zone: card colour
        r_pos = np.where(pos_mask, ridge, 0.0)
        ax.fill_between(centers, y_base, y_base + r_pos,
                        step="mid", color=color, alpha=0.75,
                        linewidth=0, zorder=i)

        # Single step outline across the full ridge
        ax.step(centers, y_base + ridge, where="mid",
                color=color, linewidth=0.8, alpha=0.95, zorder=i + 0.5)

        # Baseline rule
        ax.plot([centers[0], centers[-1]], [y_base, y_base],
                color="white", linewidth=0.2, alpha=0.10, zorder=i)

        # EV marker: white tick with dark halo — readable on any ridge colour
        tick_h = ridge.max() * 0.82
        ax.plot([mu, mu], [y_base, y_base + tick_h],
                color="white", linewidth=2.2, solid_capstyle="round",
                zorder=i + 1,
                path_effects=[
                    pe.Stroke(linewidth=5, foreground="black", alpha=0.55),
                    pe.Normal(),
                ])

        # μ annotation just above the EV tick
        ax.text(mu, y_base + tick_h + 0.015, f"{mu:+.0f}",
                ha="center", va="bottom", fontsize=7, color="white", alpha=0.75,
                zorder=n_cards + 5,
                path_effects=[pe.Stroke(linewidth=2, foreground="black", alpha=0.5),
                               pe.Normal()])

    # ── card labels as y-axis tick labels (no overlap with ridges) ────────────
    ytick_pos = [(n_cards - 1 - i) * row_step for i in range(n_cards)]
    ax.set_yticks(ytick_pos)
    ax.set_yticklabels([lbl for lbl, _, _ in datasets],
                       fontsize=10.5, fontweight="bold")
    for tick, color in zip(ax.get_yticklabels(), colors):
        tick.set_color(color)
    ax.tick_params(axis="y", which="both", length=0, pad=10)

    # ── x axis ────────────────────────────────────────────────────────────────
    # Give extra left padding so the bust zone isn't cramped at the edge.
    x_left  = x_min - 350
    x_right = x_max + 380   # room for the probability scale bar on the right
    ax.set_xlim(x_left, x_right)
    ax.set_ylim(-0.06, total_yspan + 0.08)

    xtick_step = 500
    xticks = np.arange(
        int(np.ceil(x_min / xtick_step) * xtick_step),
        int(np.floor(x_max / xtick_step) * xtick_step) + xtick_step,
        xtick_step,
    )
    ax.set_xticks(xticks)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.tick_params(axis="x", colors="#888888", labelsize=9, length=4, pad=6)

    # No vertical grid lines — just the zero-line marker
    ax.axvline(0, color="#cc4444", linewidth=1.0, linestyle="--", alpha=0.45, zorder=0)

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color("#333338")

    ax.set_xlabel("Score (pts)", color="#888888", fontsize=11, labelpad=10)
    ax.set_title(
        "Mille Sabords — score distributions under optimal strategy\n"
        "cards ordered worst → best EV  ·  dark red = bust/penalty zone  ·"
        "  white tick = expected value  ·  200 k simulated turns",
        color="#cccccc", fontsize=11, pad=14, linespacing=1.6,
    )

    # ── probability scale bar (right margin) ─────────────────────────────────
    # Anchored at the bottom row (pirate ×2, i = n_cards-1, y_base = 0).
    # Shows heights for 5 %, 10 %, and the cap value.
    sb_x   = x_max + 140          # x position of the scale bar
    sb_bot = 0.0                   # aligns with the bottom row baseline
    sb_top = sb_bot + 1.0          # 1.0 = cap height in plot units

    # Vertical spine
    ax.plot([sb_x, sb_x], [sb_bot, sb_top],
            color="#555555", linewidth=1.5, solid_capstyle="butt",
            zorder=n_cards + 10)

    ref_probs = [p for p in [0.05, 0.10, 0.15, 0.20] if p <= cap_display + 0.001]
    ref_probs.append(cap_display)   # always show the cap
    ref_probs = sorted(set(ref_probs))

    for prob in ref_probs:
        h = min(prob / cap, 1.0)
        y = sb_bot + h
        ax.plot([sb_x - 5, sb_x + 5], [y, y],
                color="#888888", linewidth=1.0, zorder=n_cards + 10)
        label_str = f"{prob:.0%}" if prob != cap_display else f"{prob:.0%} ← cap"
        ax.text(sb_x + 10, y, label_str,
                ha="left", va="center", fontsize=7.5,
                color="#999999", zorder=n_cards + 10)

    ax.text(sb_x, sb_bot - 0.06, "prob / bin",
            ha="center", va="top", fontsize=7, color="#666666",
            zorder=n_cards + 10)

    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out = out_dir / "ridgeline_all_cards.png"
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  Ridgeline saved → {out}")


def _score_to_combos(
    card_key: str,
    target_scores: set[int],
    max_per_score: int = 3,
) -> dict[int, list[str]]:
    """
    Enumerate final dice configurations (n_skulls, held) that produce each
    target score for the given card.  Returns {score: [emoji_str, ...]}.

    Always holds all free dice so each example shows exactly (total - base_skulls) dice.
    Uses greedy diversity selection: each new pick maximises new face types / skull counts
    not yet seen in the already-selected examples.
    """
    from solver.model import CARD_CONFIGS, DEFAULT_CONFIG
    from solver.scoring import score as score_fn

    config      = CARD_CONFIGS[card_key] if card_key else DEFAULT_CONFIG
    total       = config.total_dice
    base_skulls = config.initial_n_skulls
    base_held   = list(config.initial_held)
    base_fixed  = base_skulls + sum(base_held)

    EMOJI = ['💀', '⚔️', '🪙', '💎', '🐒', '🦜']

    def _parts(n: int, k: int):
        if k == 1:
            yield (n,)
            return
        for i in range(n + 1):
            for rest in _parts(n - i, k - 1):
                yield (i,) + rest

    def _to_emoji(extra_skulls: int, held_faces: tuple) -> str:
        parts = (
            ['💀'] * extra_skulls
            + [EMOJI[j + 1] for j, cnt in enumerate(held_faces) for _ in range(cnt)]
        )
        return ' '.join(parts) if parts else '—'

    # Collect all valid (extra_skulls, held_faces) candidates per score
    MAX_COLLECT = 600
    candidates: dict[int, list[tuple[int, tuple]]] = {s: [] for s in target_scores}

    for extra_skulls in range(total - base_fixed + 1):
        n_skulls = base_skulls + extra_skulls
        free     = total - base_fixed - extra_skulls
        if free < 0:
            break
        for extra_combo in _parts(free, 5):
            held = (base_held[0],) + tuple(
                base_held[j + 1] + extra_combo[j] for j in range(5)
            )
            s = score_fn(n_skulls, held, config)
            bucket = candidates.get(s)
            if bucket is not None and len(bucket) < MAX_COLLECT:
                bucket.append((extra_skulls, held[1:]))

    def _pick_diverse(cands: list, n: int) -> list:
        """Greedy: each step picks the candidate that introduces the most new face types / skull count."""
        if not cands:
            return []
        seen_skulls: set[int] = set()
        seen_faces:  set[int] = set()
        selected: list = []
        remaining = list(cands)
        while remaining and len(selected) < n:
            def novelty(c: tuple) -> int:
                extra_sk, held_faces = c
                return (
                    (2 if extra_sk not in seen_skulls else 0)
                    + sum(1 for f, cnt in enumerate(held_faces) if cnt > 0 and f not in seen_faces)
                )
            best = max(remaining, key=novelty)
            selected.append(best)
            extra_sk, held_faces = best
            seen_skulls.add(extra_sk)
            seen_faces |= {f for f, cnt in enumerate(held_faces) if cnt > 0}
            remaining.remove(best)
        return selected

    return {
        s: [_to_emoji(es, hf) for es, hf in _pick_diverse(cands, max_per_score)]
        for s, cands in candidates.items()
    }


def bubble_plotly(
    datasets: list[tuple[str, str, np.ndarray]],
    out_dir: Path,
    min_prob: float = 5e-5,
) -> None:
    """
    Interactive Plotly bubble chart: one circle per (card, score) pair,
    area ∝ probability.  Exported as a standalone HTML file.
    X axis covers all observed scores (no percentile cutoff).
    """
    import plotly.graph_objects as go
    import matplotlib.pyplot as plt  # only for the plasma colormap

    out_dir.mkdir(parents=True, exist_ok=True)

    n_cards = len(datasets)

    # ── card metadata: emoji-only label + full hover description ────────────
    _META: dict[str, tuple[str, str, str]] = {
        # card_key → (emoji_label, full_name, description)
        "pirate-ship-4":   ("⚔️⚔️⚔️⚔️", "Pirate Ship ×4",    "≥4 swords: +1000 pts, else −1000 pts"),
        "skull-2":         ("💀💀",       "Skull ×2",           "2 skulls locked at start"),
        "pirate-ship-3":   ("⚔️⚔️⚔️",   "Pirate Ship ×3",    "≥3 swords: +500 pts, else −500 pts"),
        "skull-1":         ("💀",         "Skull ×1",           "1 skull locked at start"),
        "pirate-ship-2":   ("⚔️⚔️",      "Pirate Ship ×2",    "≥2 swords: +300 pts, else −300 pts"),
        "":                ("🎲",         "No Card",            "No bonus card"),
        "treasure-island": ("🏝️",         "Treasure Island",   "Kept dice still score even if you bust"),
        "animals":         ("🐒🦜",       "Animals",            "Monkeys and parrots count together"),
        "diamond":         ("💎",         "Diamond",            "+1 diamond die at start"),
        "coin":            ("🪙",         "Coin",               "+1 coin die at start"),
        "guardian":        ("🛡️",         "Guardian",           "Reroll 1 skull once per turn"),
        "pirate":          ("🏴‍☠️",         "Pirate",             "Score × 2"),
    }
    default_meta = lambda lbl: (lbl, lbl, "")
    card_meta    = [_META.get(ck, default_meta(lbl)) for lbl, ck, _ in datasets]
    emoji_labels = [m[0] for m in card_meta]
    full_names   = [m[1] for m in card_meta]
    descs        = [m[2] for m in card_meta]

    # ── x grid covering ALL observed scores ──────────────────────────────────
    all_scores = np.concatenate([arr for _, _, arr in datasets])
    x_min = int(np.floor(all_scores.min() / 100) * 100)
    x_max = int(np.ceil(all_scores.max()  / 100) * 100)
    bin_edges = np.arange(x_min - 50, x_max + 150, 100)
    centers   = (bin_edges[:-1] + bin_edges[1:]) / 2.0

    # ── plasma colours (matches the other plots) ──────────────────────────────
    _cmap = plt.colormaps["plasma"]
    def _hex(t: float) -> str:
        r, g, b, _ = _cmap(t)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    colors = [_hex(0.10 + 0.82 * i / max(n_cards - 1, 1)) for i in range(n_cards)]

    BG      = "#0d0d10"
    PLOT_BG = "#13131a"

    # ── global sizeref — same scale for all cards ─────────────────────────────
    max_prob = max(
        float((np.histogram(arr, bins=bin_edges, density=False)[0] / len(arr)).max())
        for _, _, arr in datasets
    )
    MAX_DIAM = 44
    sizeref  = 2.0 * max_prob / (MAX_DIAM ** 2)

    def _fmt_prob(p: float) -> str:
        """Adaptive precision: always shows ≥2 significant figures."""
        pct = p * 100
        if pct >= 1:
            return f"{pct:.1f}%"
        elif pct >= 0.1:
            return f"{pct:.2f}%"
        elif pct >= 0.01:
            return f"{pct:.3f}%"
        else:
            return f"{pct:.4f}%"

    # ── pre-compute dice combo examples for every visible (card, score) ─────
    import json as _json
    print("    computing dice combos...", end=" ", flush=True)
    card_combos: list[dict[int, list[str]]] = []
    for label, card_key, arr in datasets:
        counts, _ = np.histogram(arr, bins=bin_edges, density=False)
        freq = counts.astype(float) / len(arr)
        visible = set(centers[freq >= min_prob].astype(int).tolist())
        card_combos.append(_score_to_combos(card_key, visible))
    print("done.")

    # ── one scatter trace per card ────────────────────────────────────────────
    traces: list[go.BaseTraceType] = []

    for i, ((label, card_key, arr), elabel, color, combos_map) in enumerate(
        zip(datasets, emoji_labels, colors, card_combos)
    ):
        counts, _ = np.histogram(arr, bins=bin_edges, density=False)
        freq = counts.astype(float) / len(arr)

        mask   = freq >= min_prob
        x_vals = centers[mask]
        probs  = freq[mask]

        prob_strs  = [_fmt_prob(p) for p in probs]
        combo_strs = [_json.dumps(combos_map.get(int(x), [])) for x in x_vals]

        traces.append(go.Scatter(
            x=x_vals.tolist(),
            y=[elabel] * int(mask.sum()),
            mode="markers",
            name=elabel,
            legendgroup=elabel,
            marker=dict(
                size=probs.tolist(),
                sizemode="area",
                sizeref=sizeref,
                sizemin=3,
                color=color,
                opacity=0.88,
                line=dict(width=0),
            ),
            customdata=[[ps, cs] for ps, cs in zip(prob_strs, combo_strs)],
            hovertemplate=(
                f"<b>{elabel}</b><br>"
                "Score: <b>%{x:,} pts</b><br>"
                "Probability: <b>%{customdata[0]}</b>"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    # ── EV marker: small triangle-down in each card's own color ─────────────
    ev_rounded = [int(round(float(arr.mean()))) for _, _, arr in datasets]
    traces.append(go.Scatter(
        x=ev_rounded,
        y=emoji_labels,
        mode="markers",
        name="Expected value",
        marker=dict(
            symbol="triangle-down",
            size=10,
            color=colors,
            opacity=1.0,
            line=dict(width=1.5, color="rgba(255,255,255,0.6)"),
        ),
        customdata=[[ev] for ev in ev_rounded],
        hovertemplate="EV: <b>%{customdata[0]:+d} pts</b><extra></extra>",
        showlegend=False,
    ))

    # ── invisible label-hover points (one per card, at far left) ─────────────
    # Plotly axis ticks can't show tooltips, so we place a transparent marker
    # at the left edge of each row that carries the full card description.
    x_label_anchor = x_min - 100   # just left of the bust-zone shading
    for elabel, full_name, desc in zip(emoji_labels, full_names, descs):
        traces.append(go.Scatter(
            x=[x_label_anchor],
            y=[elabel],
            mode="markers",
            marker=dict(size=28, color="rgba(0,0,0,0)", line=dict(width=0)),
            hovertemplate=(
                f"<b>{full_name}</b><br>{desc}<extra></extra>"
            ),
            showlegend=False,
            hoverinfo="text",
        ))

    # ── bust-zone shading ─────────────────────────────────────────────────────
    shapes = [
        dict(
            type="rect",
            x0=x_min - 200, x1=0,
            y0=-0.5, y1=n_cards - 0.5,
            fillcolor="rgba(100,20,20,0.12)",
            line=dict(width=0),
            layer="below",
        ),
        dict(
            type="line",
            x0=0, x1=0, y0=-0.5, y1=n_cards - 0.5,
            line=dict(color="rgba(200,60,60,0.45)", width=1.5, dash="dash"),
        ),
    ]

    # ── layout ────────────────────────────────────────────────────────────────
    emoji_labels_bottom_to_top = list(reversed(emoji_labels))

    fig = go.Figure(data=traces)
    fig.update_layout(
        paper_bgcolor=BG,
        plot_bgcolor=PLOT_BG,
        title=dict(
            text=(
                "Mille Sabords! — score distributions under optimal strategy<br>"
                "<sup>bubble area ∝ probability per 100-pt bin  ·  click a bubble for example dice combinations</sup>"
            ),
            font=dict(color="#cccccc", size=15, family="sans-serif"),
            x=0.5, xanchor="center",
        ),
        xaxis=dict(
            title="Score (pts)",
            color="#888888",
            gridcolor="#222228",
            zeroline=False,
            tickformat=",",
            range=[x_min - 200, 4100],
        ),
        yaxis=dict(
            color="#888888",
            gridcolor="#1e1e28",
            categoryorder="array",
            categoryarray=emoji_labels_bottom_to_top,
            tickfont=dict(size=20, color="#cccccc"),
        ),
        shapes=shapes,
        showlegend=False,
        width=1440,
        height=680,
        margin=dict(l=100, r=60, t=100, b=70),
        hoverlabel=dict(
            bgcolor="#1e1e2e",
            bordercolor="#555566",
            font=dict(color="#ffffff", size=12),
        ),
    )

    POPUP_JS = """
(function () {
  var popup = document.createElement('div');
  popup.id = 'ms-combo-popup';
  Object.assign(popup.style, {
    display: 'none', position: 'fixed', zIndex: '9999',
    background: '#1a1a2e', border: '1px solid rgba(160,160,200,0.35)',
    borderRadius: '10px', padding: '14px 18px', color: '#fff',
    fontFamily: 'sans-serif', maxWidth: '360px', pointerEvents: 'auto',
    boxShadow: '0 8px 32px rgba(0,0,0,0.7)', lineHeight: '1.5',
  });
  document.body.appendChild(popup);

  var justOpened = false;

  document.addEventListener('click', function () {
    if (justOpened) { justOpened = false; return; }
    popup.style.display = 'none';
  });

  var plotDiv = document.getElementById('ms-plot');
  plotDiv.on('plotly_click', function (data) {
    var pt = data.points[0];
    // Only react to bubble traces (customdata has 2 elements: [prob_str, combos_json])
    if (!pt.customdata || pt.customdata.length < 2) return;
    var combosJson = pt.customdata[1];
    if (typeof combosJson !== 'string') return;
    var combos;
    try { combos = JSON.parse(combosJson); } catch (e) { return; }

    var score = Math.round(pt.x);
    var prob  = pt.customdata[0];

    var rows = combos.length === 0
      ? '<div style="color:#888;font-size:12px">no examples found</div>'
      : combos.map(function (c) {
          return '<div style="font-size:22px;margin:3px 0;letter-spacing:3px">' + c + '</div>';
        }).join('');

    popup.innerHTML =
      '<div style="font-size:11px;color:#aaa;margin-bottom:10px">' +
        pt.y + ' &nbsp;·&nbsp; <b>' + score.toLocaleString() + ' pts</b>' +
        ' &nbsp;·&nbsp; ' + prob +
      '</div>' +
      rows +
      '<div style="font-size:9px;color:#555;margin-top:10px;text-align:right">click elsewhere to close</div>';

    // Position near cursor, keeping within viewport
    var ex = data.event.clientX, ey = data.event.clientY;
    var pw = 380, ph = popup.scrollHeight || 200;
    var left = ex + 16, top = ey - 20;
    if (left + pw > window.innerWidth)  left = ex - pw - 8;
    if (top  + ph > window.innerHeight) top  = ey - ph - 8;
    popup.style.left = left + 'px';
    popup.style.top  = top  + 'px';
    popup.style.display = 'block';

    justOpened = true;
  });
})();
"""

    html_name = "score_distributions.html"
    png_name  = "score_distributions.png"

    out_html = out_dir / html_name
    fig.write_html(
        str(out_html),
        include_plotlyjs="cdn",
        div_id="ms-plot",
        post_script=POPUP_JS,
    )
    print(f"  Bubble chart saved → {out_html}")

    # Mirror to docs/ for GitHub Pages
    docs_dir = Path(__file__).parent.parent / "docs"
    if docs_dir.exists():
        docs_html = docs_dir / html_name
        fig.write_html(
            str(docs_html),
            include_plotlyjs="cdn",
            div_id="ms-plot",
            post_script=POPUP_JS,
        )
        print(f"  Bubble chart mirrored → {docs_html}")

    # Static PNG for README / GitHub embedding
    out_png = out_dir / png_name
    try:
        fig.write_image(str(out_png), scale=2)
        print(f"  PNG snapshot saved  → {out_png}")
    except Exception as e:
        print(f"  PNG export skipped ({e})")


def ridgeline_3d(
    datasets: list[tuple[str, str, np.ndarray]],
    out_dir: Path,
    percentile: float = 98,
    elev: float = 26,
    azim: float = -62,
    depth_gap: float = 1.4,
) -> None:
    """
    3-D perspective ridgeline — each card is a flat step-bar wall at its own
    depth along the Y axis.  Bust zone in dark red, positive zone in the
    plasma-gradient card colour.  Same global-percentile normalisation as
    ridgeline_all so bar heights are comparable across all cards.
    """
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D          # noqa: F401  registers projection
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import matplotlib.ticker as ticker

    out_dir.mkdir(parents=True, exist_ok=True)

    n_cards  = len(datasets)
    BG       = "#0d0d10"
    BUST_CLR = "#8b1a1a"

    # ── x grid ────────────────────────────────────────────────────────────────
    all_scores = np.concatenate([arr for _, _, arr in datasets])
    x_min = int(np.floor(np.percentile(all_scores, 0.5)  / 100) * 100)
    x_max = int(np.floor(np.percentile(all_scores, percentile) / 100) * 100)
    bin_edges = np.arange(x_min - 50, x_max + 150, 100)
    centers   = (bin_edges[:-1] + bin_edges[1:]) / 2.0

    # ── global 95th-percentile cap (shared scale) ─────────────────────────────
    all_freqs: list[np.ndarray] = []
    for _, _, arr in datasets:
        counts, _ = np.histogram(arr, bins=bin_edges, density=False)
        all_freqs.append(counts.astype(float) / len(arr))

    nonzero = np.concatenate(all_freqs)
    cap     = float(np.percentile(nonzero[nonzero > 0], 95))

    ridges = [np.clip(f / cap, 0.0, 1.0) for f in all_freqs]
    evs    = [float(arr.mean()) for _, _, arr in datasets]

    # ── figure ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(20, 11))
    ax  = fig.add_subplot(111, projection="3d")
    fig.patch.set_facecolor(BG)
    # 3-D axes background: remove pane fills, keep thin dark edges
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.fill = False
        pane.set_edgecolor("#1e1e24")
    ax.grid(False)

    cmap   = plt.colormaps["plasma"]
    colors = [cmap(0.10 + 0.82 * i / max(n_cards - 1, 1)) for i in range(n_cards)]

    bust_idx = int(np.searchsorted(centers, 0, side="right"))  # first positive-score bin

    def _wall_verts(xs: np.ndarray, hs: np.ndarray, y_d: float) -> list[tuple]:
        """Return polygon vertices for a step-function bar wall at depth y_d."""
        top_x: list[float] = []
        top_z: list[float] = []
        for c, h in zip(xs, hs):
            top_x += [c - 50, c + 50]
            top_z += [float(h), float(h)]
        px = [float(xs[0]) - 50] + top_x + [float(xs[-1]) + 50, float(xs[0]) - 50]
        pz = [0.0]               + top_z + [0.0,                 0.0]
        return [(x, y_d, z) for x, z in zip(px, pz)]

    # Draw back-to-front (worst card first) so closer rows occlude farther ones
    for i, ((label, card_key, arr), ridge, color, mu) in enumerate(
        zip(datasets, ridges, colors, evs)
    ):
        y_d = (n_cards - 1 - i) * depth_gap    # row 0 (worst) = farthest back

        # Bust zone wall (score ≤ 0)
        if bust_idx > 0:
            vb = _wall_verts(centers[:bust_idx], ridge[:bust_idx], y_d)
            pc = Poly3DCollection([vb])
            pc.set_facecolor(BUST_CLR)
            pc.set_edgecolor("none")
            pc.set_alpha(0.82)
            ax.add_collection3d(pc)

        # Positive-score wall
        if bust_idx < len(centers):
            vp = _wall_verts(centers[bust_idx:], ridge[bust_idx:], y_d)
            pc2 = Poly3DCollection([vp])
            pc2.set_facecolor(color)
            pc2.set_edgecolor("none")
            pc2.set_alpha(0.72)
            ax.add_collection3d(pc2)

        # Crisp step outline along the top of the full ridge
        top_x: list[float] = []
        top_z: list[float] = []
        for c, h in zip(centers, ridge):
            top_x += [c - 50, c + 50]
            top_z += [float(h), float(h)]
        ax.plot(top_x, [y_d] * len(top_x), top_z,
                color=color, linewidth=0.8, alpha=0.95)

        # EV marker: white vertical line
        ev_h = float(ridge[bust_idx:].max()) if bust_idx < len(ridge) else 0.0
        ax.plot([mu, mu], [y_d, y_d], [0.0, ev_h * 0.85],
                color="white", linewidth=1.8, solid_capstyle="round", alpha=0.85)

        # Card label at the left end of each wall
        ax.text(float(x_min) - 120, y_d, 0.02, label,
                color=color, fontsize=9, fontweight="bold",
                ha="right", va="bottom")

    # ── axis styling ──────────────────────────────────────────────────────────
    ax.view_init(elev=elev, azim=azim)

    # X axis — score
    xtick_step = 500
    xticks = np.arange(
        int(np.ceil(x_min  / xtick_step) * xtick_step),
        int(np.floor(x_max / xtick_step) * xtick_step) + xtick_step,
        xtick_step,
    )
    ax.set_xticks(xticks)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.tick_params(axis="x", colors="#666666", labelsize=7.5, pad=2)
    ax.set_xlabel("Score (pts)", color="#888888", labelpad=8, fontsize=10)

    # Y axis — depth: hide ticks, labels already drawn as ax.text
    ax.set_yticks([])
    ax.set_ylim(-depth_gap * 0.5, (n_cards - 1) * depth_gap + depth_gap * 0.5)

    # Z axis — probability
    z_ticks = [0.0, 0.25, 0.5, 0.75, 1.0]
    ax.set_zticks(z_ticks)
    ax.set_zticklabels([f"{t * cap:.0%}" for t in z_ticks],
                       fontsize=7.5, color="#666666")
    ax.set_zlabel("Probability / 100-pt bin", color="#888888", labelpad=8, fontsize=9)
    ax.set_zlim(0.0, 1.08)

    ax.set_xlim(float(x_min) - 300, float(x_max) + 100)

    ax.set_title(
        "Mille Sabords — score distributions under optimal strategy\n"
        "worst card (back) → best (front)  ·  dark red = bust/penalty  ·  white line = EV",
        color="#cccccc", fontsize=11, pad=16, linespacing=1.6,
    )

    fig.tight_layout()
    out = out_dir / "ridgeline_3d_all_cards.png"
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  3-D ridgeline saved → {out}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate all cards and plot their score distributions."
    )
    parser.add_argument("--n", type=int, default=200_000,
                        help="Turns to simulate per card (default: 200000).")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility.")
    parser.add_argument("--force", action="store_true",
                        help="Re-run simulations even if .npy files already exist.")
    parser.add_argument("--plot-only", action="store_true",
                        help="Skip simulation; load existing .npy files and plot.")
    parser.add_argument("--out-dir", default="results/plots",
                        help="Directory for output images (default: results/plots/).")
    parser.add_argument("--percentile", type=float, default=98,
                        help="Right-hand x-axis cutoff percentile for heatmap/PMF (default: 98).")
    parser.add_argument("--cmap", default="viridis", choices=COLORMAPS,
                        help=f"Heatmap colormap (default: viridis). Choices: {', '.join(COLORMAPS)}.")
    parser.add_argument("--ev-color", default="white",
                        help="Color of the EV marker line on the heatmap (default: white).")
    parser.add_argument("--log-scale", action="store_true",
                        help="Use log-frequency color scale on the heatmap (default: linear).")
    parser.add_argument("--overlap", type=float, default=2.8,
                        help="Ridgeline overlap factor (default: 2.8). Higher = more overlap.")
    args = parser.parse_args()

    print(f"\n{'━' * 60}")
    print(f"  Mille Sabords — score distributions ({args.n:,} turns/card)")
    print(f"{'━' * 60}\n")

    datasets: list[tuple[str, str, np.ndarray]] = []
    for label, card_key in ALL_CARDS:
        arr = load_or_simulate(label, card_key, args.n, args.seed, args.force, args.plot_only)
        if arr is not None:
            datasets.append((label, card_key, arr))

    if not datasets:
        print("  No data to plot.")
        return

    out_dir = Path(args.out_dir)
    print()
    pmf_all(datasets, out_dir)
    print()
    heatmap_all(datasets, out_dir, percentile=args.percentile, cmap=args.cmap,
                ev_color=args.ev_color, log_scale=args.log_scale)
    print()
    ridgeline_all(datasets, out_dir, percentile=args.percentile, overlap=args.overlap)
    print()
    ridgeline_3d(datasets, out_dir, percentile=args.percentile)
    print()
    bubble_plotly(datasets, out_dir)


if __name__ == "__main__":
    main()
