#!/usr/bin/env python3
"""Render assets/codersrank.svg from the public CodersRank API.

No token required. If the API is unreachable the script exits non-zero and
leaves the previous SVG untouched, so a bad fetch can never publish an empty
card — the workflow's conditional commit does the rest.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import svg  # noqa: E402

LOGIN = os.environ.get("STATS_LOGIN", "youhide")
BASE = "https://api.codersrank.io/v2/users"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "codersrank.svg")

TOP_N = 8
WORLD_N = 5  # how many languages to spotlight by worldwide rank


PILL_H = 30
# svg.pill() takes the row's TOP edge, so advancing by only PILL_H leaves the
# next baseline sitting on the pills' bottom border — which is how the
# achievements label ended up drawn across the row above it.
PILL_ROW_GAP = 26


def pill_row(body, items, y):
    """Draw one row of pills and return the y the next block should start at."""
    x = svg.PAD
    for label, accent in items:
        markup, width = svg.pill(x, y, label, accent)
        body.append("    " + markup)
        x += width + 10
    return y + PILL_H + PILL_ROW_GAP


def die(msg):
    print(f"generate_codersrank: {msg}", file=sys.stderr)
    sys.exit(1)


def fetch(path):
    url = f"{BASE}/{LOGIN}{path}?get_by=username"
    req = urllib.request.Request(url, headers={"User-Agent": f"{LOGIN}-profile-stats"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        die(f"CodersRank returned HTTP {exc.code} for {path} — keeping the previous card")
    except urllib.error.URLError as exc:
        die(f"could not reach CodersRank ({exc.reason}) — keeping the previous card")
    except json.JSONDecodeError:
        die(f"CodersRank sent malformed JSON for {path} — keeping the previous card")


def build():
    profile = fetch("")
    languages = fetch("/languages")
    badges = fetch("/badges").get("badges") or []

    # both are optional: if CodersRank stops returning them the row disappears
    streak = next(
        (b for b in badges if b.get("badgeFamily") == "Streak" and (b.get("values") or {}).get("days")),
        None,
    )
    city = next(
        (b for b in badges if b.get("location_type") == "city" and b.get("rank")),
        None,
    )

    position = profile.get("position")
    total_users = profile.get("total_users")
    if not position or not total_users:
        die("profile response had no position/total_users — refusing to render an empty card")

    ranked = [
        (name, data["country_rank"], data.get("world_wide_rank"))
        for name, data in languages.items()
        if isinstance(data, dict) and data.get("country_rank")
    ]
    if not ranked:
        die("no language carried a country_rank — refusing to render an empty card")
    ranked.sort(key=lambda row: row[1])
    ranked = ranked[:TOP_N]

    worldwide = [
        (name, data["country_rank"], data["world_wide_rank"])
        for name, data in languages.items()
        if isinstance(data, dict) and data.get("world_wide_rank")
    ]
    if not worldwide:
        die("no language carried a world_wide_rank — refusing to render an empty card")
    worldwide.sort(key=lambda row: row[2])
    worldwide = worldwide[:WORLD_N]

    body, y = [], 88
    body.append(svg.prompt("codersrank --rank", y))
    y += 46

    # headline: world position
    body.append(
        f'    <text x="{svg.PAD}" y="{y + 26}" font-size="42" font-weight="700" '
        f'fill="{svg.PURPLE}">#{position:,}</text>'
    )
    body.append(
        f'    <text x="{svg.PAD + svg.text_width(f"#{position:,}", 42) + 16:.0f}" y="{y + 26}" '
        f'font-size="15" fill="{svg.COMMENT}">worldwide, out of {total_users:,} developers</text>'
    )
    y += 62

    body.append(svg.section("language rank", y))

    # two columns so the card uses its width instead of running tall
    col_w = svg.INNER // 2
    rows_per_col = (len(ranked) + 1) // 2

    # column headers, otherwise the two bare numbers are ambiguous
    for col in range(2):
        hx = svg.PAD + col * col_w
        body.append(
            f'    <text x="{hx + 250}" y="{y + 22}" font-size="11" text-anchor="end" '
            f'fill="{svg.COMMENT}">BRAZIL</text>'
            f'<text x="{hx + 400}" y="{y + 22}" font-size="11" text-anchor="end" '
            f'fill="{svg.COMMENT}">WORLD</text>'
        )
    y += 20
    for i, (name, country, world) in enumerate(ranked):
        col, row = divmod(i, rows_per_col)
        x = svg.PAD + col * col_w
        ry = y + 26 + row * 30
        accent = svg.GREEN if country <= 10 else svg.CYAN if country <= 50 else svg.FG
        body.append(
            f'    <text x="{x}" y="{ry}" font-size="15" fill="{svg.FG}">{svg.esc(name)}</text>'
            f'<text x="{x + 250}" y="{ry}" font-size="15" text-anchor="end" fill="{accent}">'
            f'#{country:,}</text>'
            f'<text x="{x + 400}" y="{ry}" font-size="15" text-anchor="end" fill="{svg.COMMENT}">'
            f'#{world:,}</text>'
        )
    y += 26 + rows_per_col * 30 + 18

    body.append(svg.section("best worldwide", y))
    y += 16
    # green for a top-10 placing, cyan for top-100, yellow beyond
    y = pill_row(
        body,
        [
            (
                f"{name} #{world:,}",
                svg.GREEN if world <= 10 else svg.CYAN if world <= 100 else svg.YELLOW,
            )
            for name, _, world in worldwide
        ],
        y,
    )

    achievements = []
    if streak:
        achievements.append((f"{streak['values']['days']}-day commit streak", svg.GREEN))
    if city:
        achievements.append(
            (f"#{city['rank']} {city.get('language', '?')} · {city.get('location_name', '?')}", svg.PINK)
        )
    if achievements:
        body.append(svg.section("achievements", y))
        y += 16
        y = pill_row(body, achievements, y)

    stamp = datetime.now(timezone.utc).date().isoformat()
    y += 8
    body.append(svg.note(f"generated {stamp} · source codersrank.io", y))
    height = y + 30

    return svg.card(
        height,
        f"{LOGIN}@homelab: ~/codersrank",
        f"CodersRank: #{position:,} worldwide out of {total_users:,} developers; "
        + ", ".join(f"{n} #{c} in Brazil" for n, c, _ in ranked)
        + ". Best worldwide: "
        + ", ".join(f"{n} #{w}" for n, _, w in worldwide),
        "\n".join(body),
    ), height, position, len(ranked)


def main():
    markup, height, position, count = build()
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(markup)
    print(f"wrote {OUT}\n  world rank #{position:,}, {count} languages, card height {height}px")


if __name__ == "__main__":
    main()
