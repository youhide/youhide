#!/usr/bin/env python3
"""Render assets/detected.svg — frameworks CodersRank found in the code.

Complements assets/techstack.svg: that one is the curated list of what Youri
chooses to advertise, this one is what static analysis of the public repos
actually turned up, and it refreshes itself.
"""

import json
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import codersrank  # noqa: E402
import svg  # noqa: E402

LOGIN = os.environ.get("STATS_LOGIN", "youhide")
URL = f"https://api.codersrank.io/v2/users/{LOGIN}/technologies?get_by=username"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "detected.svg")

TOP_N = 12
BAR_X, BAR_W = 330, 620
ROW = 34


def die(msg):
    print(f"generate_detected: {msg}", file=sys.stderr)
    sys.exit(1)


def has_scores(payload):
    return any(
        isinstance(entry, dict) and isinstance(entry.get("score"), (int, float))
        for entry in payload.values()
    )


def fetch():
    data = codersrank.get(LOGIN, "/technologies", has_scores, "technologies")
    if data is None:
        die("could not get usable technologies from CodersRank — keeping the previous card")
    rows = [
        (name, entry["score"])
        for name, entry in data.items()
        if isinstance(entry, dict) and isinstance(entry.get("score"), (int, float))
    ]
    rows.sort(key=lambda row: -row[1])
    return rows


def build(rows):
    shown = rows[:TOP_N]
    peak = shown[0][1]

    body, y = [], 88
    body.append(svg.prompt("codersrank --technologies", y))
    y += 40
    body.append(svg.section(f"detected in code · {len(rows)} technologies found", y))
    y += 28

    for i, (name, score) in enumerate(shown):
        ry = y + i * ROW
        # square-root scale: ReactJS outscores the tail by ~1000x, and a linear
        # bar would render everything below it as an invisible sliver
        width = max(3, BAR_W * math.sqrt(score / peak))
        accent = svg.PURPLE if i == 0 else svg.CYAN if score >= peak * 0.1 else svg.COMMENT
        body.append(
            f'    <text x="{svg.PAD}" y="{ry + 5}" font-size="15" fill="{svg.FG}">'
            f'{svg.esc(name)}</text>'
            f'<rect x="{BAR_X}" y="{ry - 9}" width="{width:.1f}" height="14" rx="4" fill="{accent}"/>'
            f'<text x="{BAR_X + width + 12:.0f}" y="{ry + 4}" font-size="13" '
            f'fill="{svg.COMMENT}">{score:,.0f}</text>'
        )

    y += len(shown) * ROW + 16
    body.append(svg.note("bar uses a square-root scale · score from codersrank.io", y))
    height = y + 30

    aria = "Technologies detected in code by CodersRank: " + ", ".join(
        f"{name} score {score:,.0f}" for name, score in shown
    )
    return svg.card(height, f"{LOGIN}@homelab: ~/detected", aria, "\n".join(body)), height


def main():
    rows = fetch()
    markup, height = build(rows)
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(markup)
    print(f"wrote {OUT}\n  {len(rows)} technologies, showing {min(TOP_N, len(rows))}, height {height}px")


if __name__ == "__main__":
    main()
