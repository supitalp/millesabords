#!/usr/bin/env python3
"""Generate card illustrations using OpenAI gpt-image-2.

Usage:
    # Test with a single card (by filename stem):
    uv run fortune_cards/generate_images.py la_traversee

    # Generate all cards (skips already-generated ones):
    uv run fortune_cards/generate_images.py
"""

import base64
import os
import re
import sys
from pathlib import Path

from openai import OpenAI

CARDS_DIR = Path(__file__).parent / "cards"
IMAGES_DIR = Path(__file__).parent.parent / "docs" / "fortune_cards" / "images"
STYLE_REF = Path.home() / "Downloads" / "20260517_152954.jpg"


def extract_prompt(md_path: Path) -> str:
    text = md_path.read_text()
    match = re.search(r"## Description visuelle \(prompt IA\)\n(.+)", text, re.DOTALL)
    if not match:
        raise ValueError(f"No visual prompt section found in {md_path}")
    # Take only the first paragraph (stop at next ## or end of file)
    prompt = re.split(r"\n##", match.group(1).strip())[0].strip()
    return prompt


def generate_image(card_path: Path, client: OpenAI) -> None:
    card_name = card_path.stem
    output_path = IMAGES_DIR / f"{card_name}.png"

    if output_path.exists():
        print(f"  ⏭  Already exists, skipping: {output_path.name}")
        return

    prompt = extract_prompt(card_path)
    print(f"  Prompt ({len(prompt)} chars): {prompt[:100]}...")

    with open(STYLE_REF, "rb") as ref_img:
        result = client.images.edit(
            model="gpt-image-2",
            image=ref_img,
            prompt=prompt,
            size="1024x1536",
            quality="auto",
            n=1,
        )

    image_data = base64.b64decode(result.data[0].b64_json)
    output_path.write_bytes(image_data)
    print(f"  ✓  Saved → {output_path}")


def main() -> None:
    api_key = os.environ.get("OPENAI_TOKEN")
    if not api_key:
        print("Error: OPENAI_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    if not STYLE_REF.exists():
        print(f"Error: style reference image not found at {STYLE_REF}", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    IMAGES_DIR.mkdir(exist_ok=True)

    if len(sys.argv) > 1:
        # Single card mode (pass the filename stem, e.g. "la_traversee")
        card_name = sys.argv[1]
        card_path = CARDS_DIR / f"{card_name}.md"
        if not card_path.exists():
            print(f"Error: card not found: {card_path}", file=sys.stderr)
            sys.exit(1)
        cards = [card_path]
    else:
        cards = sorted(CARDS_DIR.glob("*.md"))

    print(f"Generating {len(cards)} image(s)...\n")
    for card_path in cards:
        print(f"→ {card_path.stem}")
        try:
            generate_image(card_path, client)
        except Exception as e:
            print(f"  ✗  Error: {e}", file=sys.stderr)
    print("\nDone.")


if __name__ == "__main__":
    main()
