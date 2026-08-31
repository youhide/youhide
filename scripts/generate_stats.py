#!/usr/bin/env python3
"""Generate assets/stats.svg from public GitHub data.

Reads GITHUB_TOKEN from the environment (falls back to `gh auth token` locally)
and renders a single self-contained SVG in the same Dracula terminal style as
assets/header.svg. No third-party services are involved at render time.
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone

API = "https://api.github.com/graphql"
LOGIN = os.environ.get("STATS_LOGIN", "youhide")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "stats.svg")

# Dracula palette — identical to assets/header.svg
BG, BAR, LINE, FG = "#282a36", "#21222c", "#44475a", "#f8f8f2"
COMMENT, PURPLE, PINK, CYAN = "#6272a4", "#bd93f9", "#ff79c6", "#8be9fd"
GREEN, ORANGE, YELLOW, RED = "#50fa7b", "#ffb86c", "#f1fa8c", "#ff5555"
MONO = "ui-monospace,SFMono-Regular,SF Mono,Menlo,Consolas,DejaVu Sans Mono,monospace"

W, H = 1200, 550
PAD = 48


def die(msg):
    print(f"generate_stats: {msg}", file=sys.stderr)
    sys.exit(1)


def token():
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except Exception:
        die("no GITHUB_TOKEN in the environment and `gh auth token` is unavailable")


def graphql(query, variables, tok):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={
            "Authorization": f"bearer {tok}",
            "Content-Type": "application/json",
            "User-Agent": f"{LOGIN}-profile-stats",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as exc:
        die(f"GitHub API returned HTTP {exc.code}: {exc.read()[:300].decode('utf-8', 'replace')}")
    except urllib.error.URLError as exc:
        die(f"could not reach the GitHub API: {exc.reason}")
    if payload.get("errors"):
        die(f"GraphQL errors: {json.dumps(payload['errors'])[:400]}")
    return payload["data"]


PROFILE_Q = """
query($login:String!){
  user(login:$login){
    createdAt
    repositories(first:100, ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC){
      totalCount
      nodes{ stargazerCount languages(first:10){ edges{ size node{ name color } } } }
    }
  }
}
"""

CALENDAR_Q = """
query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    contributionsCollection(from:$from,to:$to){
      restrictedContributionsCount
      contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount } } }
    }
  }
}
"""


def fetch(tok):
    data = graphql(PROFILE_Q, {"login": LOGIN}, tok)
    user = data.get("user")
    if not user:
        die(f"user '{LOGIN}' not found or not visible to this token")
    created = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))

    repos = user["repositories"]
    langs, stars = Counter(), 0
    colors = {}
    for node in repos["nodes"]:
        stars += node["stargazerCount"]
        edges = node["languages"]["edges"]
        repo_bytes = sum(edge["size"] for edge in edges)
        if not repo_bytes:
            continue
        # Weight each repo equally instead of by size: otherwise a single large
        # legacy import (runuo, ~38% of all public bytes) swamps the whole mix.
        for edge in edges:
            langs[edge["node"]["name"]] += edge["size"] / repo_bytes
            colors[edge["node"]["name"]] = edge["node"]["color"] or COMMENT

    days, restricted = {}, 0
    today = datetime.now(timezone.utc).date()
    for year in range(created.year, today.year + 1):
        start = max(created.date(), date(year, 1, 1))
        end = min(today, date(year, 12, 31))
        if start > end:
            continue
        col = graphql(
            CALENDAR_Q,
            {
                "login": LOGIN,
                "from": f"{start.isoformat()}T00:00:00Z",
                "to": f"{end.isoformat()}T23:59:59Z",
            },
            tok,
        )["user"]["contributionsCollection"]
        cal = col.get("contributionCalendar")
        if cal is None:
            die(
                "contributionCalendar came back empty — this token cannot read the "
                "contribution calendar. Use a PAT with read:user instead of GITHUB_TOKEN."
            )
        restricted += col.get("restrictedContributionsCount") or 0
        for week in cal["weeks"]:
            for day in week["contributionDays"]:
                days[day["date"]] = day["contributionCount"]

    if not days:
        die("no contribution days returned — refusing to render a card full of zeros")

    return {
        "created": created,
        "repos": repos["totalCount"],
        "stars": stars,
        "langs": langs,
        "colors": colors,
        "days": days,
        "restricted": restricted,
        "today": today,
    }


def streaks(days, today):
    """Return (total, current, longest). Today counts as neutral while empty."""
    ordered = sorted(days.items())
    total = sum(c for _, c in ordered)

    longest = run = 0
    prev = None
    for iso, count in ordered:
        current_day = date.fromisoformat(iso)
        if count > 0:
            run = run + 1 if prev and (current_day - prev).days == 1 else 1
            longest = max(longest, run)
            prev = current_day
        else:
            run, prev = 0, None

    current = 0
    cursor = today
    if days.get(today.isoformat(), 0) == 0:
        cursor -= timedelta(days=1)  # today isn't over yet
    while days.get(cursor.isoformat(), 0) > 0:
        current += 1
        cursor -= timedelta(days=1)
    return total, current, longest


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def human(n):
    return f"{n:,}"


def weekly_series(days, today, weeks=52):
    """Sum contributions per week for the last `weeks` weeks, oldest first."""
    series, labels = [], []
    for i in range(weeks - 1, -1, -1):
        end = today - timedelta(days=7 * i)
        start = end - timedelta(days=6)
        total = 0
        cursor = start
        while cursor <= end:
            total += days.get(cursor.isoformat(), 0)
            cursor += timedelta(days=1)
        series.append(total)
        labels.append(start)
    return series, labels


def chart(series, labels, x, y, w, h):
    peak = max(series) or 1
    step = w / (len(series) - 1)
    pts = [(x + i * step, y + h - (v / peak) * h) for i, v in enumerate(series)]

    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = f"{x:.1f},{y + h:.1f} " + line + f" {x + w:.1f},{y + h:.1f}"

    out = [
        f'<line x1="{x}" y1="{y + h}" x2="{x + w}" y2="{y + h}" stroke="{LINE}" stroke-width="1"/>',
        f'<line x1="{x}" y1="{y}" x2="{x + w}" y2="{y}" stroke="{LINE}" stroke-width="1" stroke-dasharray="3 5" opacity="0.5"/>',
        f'<text x="{x + w}" y="{y - 8}" text-anchor="end" font-size="12" fill="{COMMENT}">peak {peak}/week</text>',
        f'<polygon points="{area}" fill="url(#area)"/>',
        f'<polyline points="{line}" fill="none" stroke="{PURPLE}" stroke-width="2.5" stroke-linejoin="round"/>',
    ]

    seen = set()
    for i, day in enumerate(labels):
        tag = day.strftime("%b")
        if day.month in seen or i == 0 or i > len(labels) - 4:
            continue
        seen.add(day.month)
        out.append(
            f'<text x="{x + i * step:.1f}" y="{y + h + 20}" text-anchor="middle" '
            f'font-size="12" fill="{COMMENT}">{tag}</text>'
        )
    return "\n    ".join(out)


def tiles(stats, total, current, longest):
    labels = [
        (human(total), "public contributions"),
        (human(current), "current streak"),
        (human(longest), "longest streak"),
        (human(stats["repos"]), "public repos"),
        (human(stats["stars"]), "stars earned"),
    ]
    accents = [PURPLE, GREEN, ORANGE, CYAN, YELLOW]
    inner = W - 2 * PAD
    gap = 12
    tw = (inner - gap * (len(labels) - 1)) / len(labels)
    out = []
    for i, ((value, label), accent) in enumerate(zip(labels, accents)):
        tx = PAD + i * (tw + gap)
        mid = tx + tw / 2
        out.append(
            f'<g><rect x="{tx:.1f}" y="110" width="{tw:.1f}" height="86" rx="8" fill="{BAR}" '
            f'stroke="{LINE}" stroke-width="1.5"/>'
            f'<text x="{mid:.1f}" y="152" text-anchor="middle" font-size="32" font-weight="700" '
            f'fill="{accent}">{value}</text>'
            f'<text x="{mid:.1f}" y="176" text-anchor="middle" font-size="12" '
            f'fill="{COMMENT}">{label}</text></g>'
        )
    return "\n    ".join(out)


def languages(langs, colors, x, y, w):
    top = langs.most_common(7)
    total = sum(langs.values()) or 1
    other = total - sum(size for _, size in top)
    rows = [(name, size, colors.get(name, COMMENT)) for name, size in top]
    if other > 0:
        rows.append(("Other", other, LINE))

    bar, cursor = [], x
    for i, (name, size, color) in enumerate(rows):
        seg = w * size / total
        # keep the rounded ends of the bar clean by clipping the whole strip
        bar.append(
            f'<rect x="{cursor:.1f}" y="{y}" width="{seg:.1f}" height="26" fill="{color}"/>'
        )
        cursor += seg

    legend, lx = [], x
    for name, size, color in rows:
        pct = 100 * size / total
        label = f"{esc(name)} {pct:.1f}%"
        legend.append(
            f'<rect x="{lx:.1f}" y="{y + 46}" width="11" height="11" rx="2" fill="{color}"/>'
            f'<text x="{lx + 18:.1f}" y="{y + 56}" font-size="13" fill="{FG}">{label}</text>'
        )
        lx += 20 + len(label) * 7.9 + 14

    return (
        f'<g clip-path="url(#langbar)">{"".join(bar)}</g>\n    ' + "\n    ".join(legend)
    )


def render(stats):
    total, current, longest = streaks(stats["days"], stats["today"])
    series, labels = weekly_series(stats["days"], stats["today"])
    years = stats["today"].year - stats["created"].year
    stamp = stats["today"].isoformat()

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="GitHub stats for {esc(LOGIN)}: {human(total)} public contributions, {current} day current streak, {longest} day longest streak, {stats['repos']} public repos, {stats['stars']} stars">
  <defs>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{PURPLE}"/>
      <stop offset="50%" stop-color="{PINK}"/>
      <stop offset="100%" stop-color="{CYAN}"/>
    </linearGradient>
    <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{PURPLE}" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="{PURPLE}" stop-opacity="0.05"/>
    </linearGradient>
    <pattern id="dots" width="26" height="26" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1.2" fill="{LINE}" opacity="0.5"/>
    </pattern>
    <clipPath id="card"><rect width="{W}" height="{H}" rx="18"/></clipPath>
    <clipPath id="langbar"><rect x="{PAD}" y="448" width="{W - 2 * PAD}" height="26" rx="6"/></clipPath>
  </defs>

  <g clip-path="url(#card)" font-family="{MONO}">
    <rect width="{W}" height="{H}" fill="{BG}"/>
    <rect width="{W}" height="{H}" fill="url(#dots)"/>

    <rect width="{W}" height="46" fill="{BAR}"/>
    <circle cx="34" cy="23" r="7" fill="{RED}"/>
    <circle cx="58" cy="23" r="7" fill="{YELLOW}"/>
    <circle cx="82" cy="23" r="7" fill="{GREEN}"/>
    <text x="{W // 2}" y="28" text-anchor="middle" font-size="15" fill="{COMMENT}">{esc(LOGIN)}@homelab: ~/stats</text>

    <text x="{PAD}" y="88" font-size="22"><tspan fill="{GREEN}">$</tspan><tspan fill="{FG}" dx="12">gh stats --public</tspan></text>

    {tiles(stats, total, current, longest)}

    <text x="{PAD}" y="238" font-size="13" fill="{COMMENT}">// contributions · last 12 months</text>
    {chart(series, labels, PAD, 252, W - 2 * PAD, 130)}

    <text x="{PAD}" y="434" font-size="13" fill="{COMMENT}">// top languages · averaged across {stats['repos']} public repos</text>
    {languages(stats['langs'], stats['colors'], PAD, 448, W - 2 * PAD)}

    <text x="{PAD}" y="534" font-size="13" fill="{COMMENT}"># generated {stamp} · {years} years on GitHub · public data only</text>

    <rect x="0" y="{H - 6}" width="{W}" height="6" fill="url(#accent)"/>
  </g>
</svg>
"""


def main():
    tok = token()
    stats = fetch(tok)
    svg = render(stats)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(svg)

    total, current, longest = streaks(stats["days"], stats["today"])
    print(f"wrote {OUT}")
    print(
        f"  contributions={human(total)} current_streak={current} longest_streak={longest} "
        f"repos={stats['repos']} stars={stats['stars']}"
    )
    if stats["restricted"]:
        print(
            f"  note: this token also saw {stats['restricted']} restricted (private) "
            "contributions, which are NOT counted above"
        )


if __name__ == "__main__":
    main()
