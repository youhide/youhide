#!/usr/bin/env python3
"""Render assets/about.svg — the About Me YAML as a syntax-coloured card.

Also carries the homelab philosophy: with the markdown headings gone those two
lines would otherwise float unlabelled, and a whole card for one quote weighs
more than the quote does.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import svg  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "about.svg")

# (key, scalar value) or (key, [list items])
ABOUT = [
    ("also", "Keeper of Ancient Scripts"),
    ("location", "Londrina, Brazil"),
    (None, None),
    ("by_day", ["Clusters at scale", "GitOps workflows", "Infrastructure as Code"]),
    (None, None),
    ("by_night", [
        "Tools in Go and Rust that fix my own problems",
        "Homelab experiments",
        "Retro gaming & tech",
        "Automation that actually works",
    ]),
]

PHILOSOPHY = [
    "I experiment, prototype, and tune systems in my homelab",
    "before deploying them at scale.",
    "19 years of building boxes, breaking clusters, fixing the chaos,",
    "and repeating the loop.",
]

LINE = 26


def build():
    body, y = [], 88
    body.append(svg.prompt("cat ~/about.yaml", y))
    y += 42

    for key, value in ABOUT:
        if key is None:
            y += LINE // 2
            continue
        if isinstance(value, list):
            body.append(
                f'    <text x="{svg.PAD}" y="{y}" font-size="16">'
                f'<tspan fill="{svg.PINK}">{svg.esc(key)}</tspan>'
                f'<tspan fill="{svg.FG}">:</tspan></text>'
            )
            y += LINE
            for item in value:
                body.append(
                    f'    <text x="{svg.PAD + 24}" y="{y}" font-size="16">'
                    f'<tspan fill="{svg.COMMENT}">-</tspan>'
                    f'<tspan fill="{svg.YELLOW}" dx="10">{svg.esc(item)}</tspan></text>'
                )
                y += LINE
        else:
            body.append(
                f'    <text x="{svg.PAD}" y="{y}" font-size="16">'
                f'<tspan fill="{svg.PINK}">{svg.esc(key)}</tspan>'
                f'<tspan fill="{svg.FG}">:</tspan>'
                f'<tspan fill="{svg.YELLOW}" dx="10">{svg.esc(value)}</tspan></text>'
            )
            y += LINE

    y += 20
    body.append(
        f'    <line x1="{svg.PAD}" y1="{y}" x2="{svg.W - svg.PAD}" y2="{y}" '
        f'stroke="{svg.LINE}" stroke-width="1" stroke-dasharray="3 5" opacity="0.6"/>'
    )
    y += 30
    for line in PHILOSOPHY:
        body.append(
            f'    <text x="{svg.PAD}" y="{y}" font-size="14" fill="{svg.COMMENT}"># {svg.esc(line)}</text>'
        )
        y += 22

    height = y + 20
    aria = (
        "About Youri: Keeper of Ancient Scripts, based in Londrina, Brazil. "
        "By day: clusters at scale, GitOps workflows, Infrastructure as Code. "
        "By night: tools in Go and Rust, homelab experiments, retro gaming, automation. "
        + " ".join(PHILOSOPHY)
    )
    return svg.card(height, "youhide@homelab: ~/about", aria, "\n".join(body)), height


def main():
    markup, height = build()
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(markup)
    print(f"wrote {OUT}\n  card height {height}px")


if __name__ == "__main__":
    main()
