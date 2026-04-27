#!/usr/bin/env python3
"""
Usage: python main.py <die1> <die2> ... <die8>

Each die value is one of: skull, sword, coin, diamond, monkey, parrot
Example: python main.py skull sword coin coin diamond monkey parrot sword
"""
import sys
from solver.model import Face
from solver.report import report

FACE_MAP = {f.name.lower(): f for f in Face}


def main():
    if len(sys.argv) != 9:
        print(f"Error: expected 8 dice, got {len(sys.argv) - 1}.")
        print(__doc__)
        sys.exit(1)

    dice = []
    for arg in sys.argv[1:]:
        key = arg.lower()
        if key not in FACE_MAP:
            valid = ", ".join(FACE_MAP.keys())
            print(f"Error: unknown face '{arg}'. Valid values: {valid}")
            sys.exit(1)
        dice.append(FACE_MAP[key])

    print(report(dice))


if __name__ == "__main__":
    main()
