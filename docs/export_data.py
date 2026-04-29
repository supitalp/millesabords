#!/usr/bin/env python3
"""
Export precomputed DP solutions to JSON files for the web app.

Run from the project root:
    python docs/export_data.py

Outputs one JSON file per card config into docs/data/.
"""
import json
import sys
from pathlib import Path

# Ensure the project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from solver.model import CARD_CONFIGS, DEFAULT_CONFIG
from solver.dp import get_solution


def export_config(name: str, config, out_dir: Path) -> None:
    print(f"  Solving '{name}'...", end=" ", flush=True)
    sol = get_solution(config)
    print(f"{len(sol.states)} states", end=" ", flush=True)

    # States: each as [n_skulls, held[0..5], skull_reroll_used]
    states = []
    for s in sol.states:
        states.append([s.n_skulls] + list(s.held) + [bool(s.skull_reroll_used)])

    data = {
        "config": {
            "total_dice": config.total_dice,
            "initial_n_skulls": config.initial_n_skulls,
            "initial_held": list(config.initial_held),
            "merge_animals": config.merge_animals,
            "score_multiplier": config.score_multiplier,
            "required_swords": config.required_swords,
            "sword_bonus": config.sword_bonus,
            "sword_penalty": config.sword_penalty,
            "skull_reroll_available": config.skull_reroll_available,
            "treasure_island": config.treasure_island,
        },
        "states": states,
        "V_normal": [round(float(v), 6) for v in sol.V_normal],
        "max_score": [int(v) for v in sol.max_score],
        "stop_values": [int(v) for v in sol.stop_values],
    }

    out_path = out_dir / f"{name}.json"
    with open(out_path, "w") as f:
        json.dump(data, f, separators=(",", ":"))

    size_kb = out_path.stat().st_size / 1024
    print(f"→ {out_path.name} ({size_kb:.1f} KB)")


def main():
    out_dir = Path(__file__).parent / "data"
    out_dir.mkdir(exist_ok=True)

    all_configs = {"default": DEFAULT_CONFIG, **CARD_CONFIGS}

    print(f"Exporting {len(all_configs)} card configs to {out_dir}/")
    for name, config in all_configs.items():
        export_config(name, config, out_dir)
    print("Done.")


if __name__ == "__main__":
    main()
