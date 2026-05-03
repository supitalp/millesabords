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


if __name__ == "__main__":
    main()
