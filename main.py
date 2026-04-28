#!/usr/bin/env python3
"""
Usage: python main.py [<die1> ... <dieN>] [--card <card>] [--verbose]

Pass dice to analyse a specific roll, or omit dice to see the expected score
for a fresh turn under optimal play.

Each die value is one of: skull, sword, coin, diamond, monkey, parrot
Optional --card selects the active Pirate card (default: none).
Optional --verbose shows additional columns (EV|safe, Min, Max, P(win)).

Available cards:
  skull-1        Skull card with 1 pre-locked skull
  skull-2        Skull card with 2 pre-locked skulls
  coin           Coin card (1 extra coin die, 9 total)
  diamond        Diamond card (1 extra diamond die, 9 total)
  animals        Animals card (monkeys and parrots count as the same symbol)
  pirate         Pirate card (doubles all points)
  guardian       Guardian card (may reroll one skull die once per turn)
  pirate-ship-2  Pirate Ship card (need ≥2 swords, +300/−300)
  pirate-ship-3  Pirate Ship card (need ≥3 swords, +500/−500)
  pirate-ship-4  Pirate Ship card (need ≥4 swords, +1000/−1000)

Examples:
  python main.py skull sword coin coin diamond monkey parrot sword
  python main.py skull sword coin coin diamond monkey parrot sword --card skull-1
  python main.py --card coin
  python main.py coin coin coin sword sword sword monkey parrot --card guardian --verbose
"""
import sys
from solver.model import Face, CARD_CONFIGS, DEFAULT_CONFIG
from solver.report import report, report_turn_start

FACE_MAP = {f.name.lower(): f for f in Face}


def main():
    args = sys.argv[1:]

    # Parse optional --verbose flag
    verbose = "--verbose" in args
    if verbose:
        args = [a for a in args if a != "--verbose"]

    # Parse optional --card flag
    config = DEFAULT_CONFIG
    if "--card" in args:
        idx = args.index("--card")
        if idx + 1 >= len(args):
            print("Error: --card requires a card name.")
            print(__doc__)
            sys.exit(1)
        card_name = args[idx + 1]
        if card_name not in CARD_CONFIGS:
            valid = ", ".join(CARD_CONFIGS.keys())
            print(f"Error: unknown card '{card_name}'. Valid cards: {valid}")
            sys.exit(1)
        config = CARD_CONFIGS[card_name]
        args = args[:idx] + args[idx + 2:]

    if len(args) == 0:
        print(report_turn_start(config))
        return

    n_dice = config.total_dice - config.initial_n_skulls - sum(config.initial_held)
    if len(args) != n_dice:
        print(f"Error: expected {n_dice} dice for this card, got {len(args)}.")
        print(__doc__)
        sys.exit(1)

    dice = []
    for arg in args:
        key = arg.lower()
        if key not in FACE_MAP:
            valid = ", ".join(FACE_MAP.keys())
            print(f"Error: unknown face '{arg}'. Valid values: {valid}")
            sys.exit(1)
        dice.append(FACE_MAP[key])

    print(report(dice, config, verbose=verbose))


if __name__ == "__main__":
    main()
