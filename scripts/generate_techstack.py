#!/usr/bin/env python3
"""Render assets/techstack.svg — the tech stack as Dracula pills.

Static data: edit STACK below to change what shows up. Colours are each
project's official brand colour, kept as the only splash of non-Dracula ink.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import svg  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "techstack.svg")

STACK = [
    ("LANGUAGES", [
        ("Go", "#00ADD8"), ("Rust", "#dea584"), ("TypeScript", "#3178c6"),
        ("Node.js", "#5FA04E"), ("C++", "#00599C"), ("Bash", "#4EAA25"),
    ]),
    ("CLOUD & INFRASTRUCTURE", [
        ("AWS", "#FF9900"), ("Google Cloud", "#4285F4"),
        ("DigitalOcean", "#0080FF"), ("Cloudflare", "#F38020"),
    ]),
    ("CONTAINERS & ORCHESTRATION", [
        ("Kubernetes", "#326ce5"), ("Docker", "#2496ED"),
        ("Podman", "#892CA0"), ("Helm", "#0F1689"),
    ]),
    ("IAC & AUTOMATION", [
        ("OpenTofu", "#FFDA18"), ("Terraform", "#844FBA"), ("Terragrunt", "#5C4EE5"),
        ("Ansible", "#EE0000"), ("GitHub Actions", "#2088FF"),
    ]),
    ("SYSTEMS & TOOLS", [
        ("Red Hat", "#EE0000"), ("Fedora", "#51A2DA"), ("Ubuntu", "#E95420"),
        ("FreeBSD", "#AB2B28"), ("GhostBSD", "#3B82F6"), ("macOS", "#f8f8f2"),
        ("Git", "#F05033"),
    ]),
]

ROW_GAP, PILL_GAP, GROUP_GAP = 40, 10, 30


def build():
    body, y = [], 88
    body.append(svg.prompt("cat ~/.config/stack.toml", y))
    y += 34

    for label, items in STACK:
        body.append(svg.section(label, y))
        y += 18
        x = svg.PAD
        for name, color in items:
            markup, width = svg.pill(x, y, name, color)
            if x + width > svg.PAD + svg.INNER:  # wrap before overflowing the card
                x = svg.PAD
                y += ROW_GAP
                markup, width = svg.pill(x, y, name, color)
            body.append("    " + markup)
            x += width + PILL_GAP
        y += ROW_GAP + GROUP_GAP

    y += 4
    body.append(svg.note("brand colours are the only non-Dracula ink on this card", y))
    height = y + 30

    return svg.card(
        height,
        "youhide@homelab: ~/stack",
        "Tech stack: " + ", ".join(n for _, items in STACK for n, _ in items),
        "\n".join(body),
    ), height


def main():
    markup, height = build()
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(markup)
    count = sum(len(items) for _, items in STACK)
    print(f"wrote {OUT}\n  {count} technologies in {len(STACK)} groups, card height {height}px")


if __name__ == "__main__":
    main()
