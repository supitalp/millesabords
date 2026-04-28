"""
Pre-solve and cache all known card configs to disk.

Run once (or after any change to scoring/DP logic):
    python prebuild.py

Subsequent runs of main.py will load cached results instantly.
"""
import time
from solver.model import DEFAULT_CONFIG, CARD_CONFIGS
from solver.dp import get_solution, _config_key, _DISK_CACHE_DIR

ALL_CONFIGS = {"default": DEFAULT_CONFIG, **CARD_CONFIGS}

print(f"Cache directory: {_DISK_CACHE_DIR}")
print()

total_start = time.time()
for name, config in ALL_CONFIGS.items():
    path = _DISK_CACHE_DIR / f"{_config_key(config)}.npz"
    if path.exists():
        print(f"  {name:<20} already cached, skipping")
        continue
    t0 = time.time()
    get_solution(config)
    elapsed = time.time() - t0
    size_kb = path.stat().st_size / 1024
    print(f"  {name:<20} solved in {elapsed:.1f}s → {size_kb:.1f} KB")

total = time.time() - total_start
total_kb = sum(p.stat().st_size for p in _DISK_CACHE_DIR.glob("*.npz")) / 1024
print()
print(f"Done in {total:.1f}s. Total cache size: {total_kb:.1f} KB")
