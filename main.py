#!/usr/bin/env python3
"""
Usage: python main.py [<die1> ... <dieN>] [--card <card>]

Pass dice to analyse a specific roll, or omit dice to see the expected score
for a fresh turn under optimal play.

Each die value is one of: skull, sword, coin, diamond, monkey, parrot
Optional --card selects the active Pirate card (default: none).

Available cards:
  tete-de-mort-1   Tête de Mort with 1 pre-locked skull
  tete-de-mort-2   Tête de Mort with 2 pre-locked skulls
  piece-d-or       Pièce d'or (1 extra coin die, 9 total)
  diamant          Diamant (1 extra diamond die, 9 total)
  animaux          Animaux (monkeys and parrots count as the same symbol)

Examples:
  python main.py skull sword coin coin diamond monkey parrot sword
  python main.py skull sword coin coin diamond monkey parrot sword --card tete-de-mort-1
  python main.py --card piece-d-or
"""
import sys
from solver.model import Face, CARD_CONFIGS, DEFAULT_CONFIG
from solver.report import report, report_turn_start

FACE_MAP = {f.name.lower(): f for f in Face}


def main():
    args = sys.argv[1:]

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

    print(report(dice, config))


if __name__ == "__main__":
    main()
