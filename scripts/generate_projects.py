#!/usr/bin/env python3
"""Render one clickable card per project and per org.

Each card is its own SVG so the README can wrap it in its own <a>: an SVG
served through <img> has no clickable regions, so one file per row is what
buys back the per-project link.
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import svg  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.github.com/graphql"

# slug, display name, stack, one-line description
PROJECTS = [
    ("youhide/OpenShard", "OpenShard", "Rust",
     "Modern open-source MMORPG server engine, compatible with classic Ultima Online clients"),
    ("youhide/oxinit", "oxinit", "Rust",
     "A service manager and PID 1 for Linux — TOML units, no panic, no async runtime (pre-alpha)"),
    ("youhide/hideDot", "hideDot", "Go",
     "Blazing fast dotfiles manager — symlinks, git repo cloning and shell hooks from one YAML"),
    ("youhide/homebrew-youhide", "homebrew-youhide", "Ruby · Homebrew",
     "Homebrew tap for my dark tools — brew tap youhide/youhide"),
    ("youhide/hideTop", "hideTop", "Go",
     "Terminal system monitor: CPU, memory, Apple Silicon GPU metrics and energy impact"),
    ("youhide/hideGit", "hideGit", "Rust",
     "Cross-platform desktop Git client with pull request alerts built in (pre-alpha)"),
    ("youhide/hideForming", "hideForming", "HCL",
     "The whole homelab as Infrastructure as Code"),
    ("youhide/theShortener", "theShortener", "C++ · Node",
     "SHA-256 + Base62 string shortener as a native Node.js addon"),
    ("youhide/hideGrowLegacy", "hideGrowLegacy", "C",
     "ESP32 environmental monitoring with HomeKit — pH, temperature and CO₂"),
    ("youhide/vagas.tec.br", "vagas.tec.br", "TypeScript",
     "Mural de vagas em tecnologia focado no mercado brasileiro"),
]

ORGS = [
    {
        "file": "postrite",
        "name": "PostRite",
        "handle": "@Post-Rite",
        "logo": "postrite.png",
        "logo_box": (48, 34, 210, 52),
        "tagline": "Engineering order inside the chaos of time-based publishing.",
        "body": "Social publishing in one workspace — 12+ networks, campaign calendar, "
                "approval workflows with audit trail, per-platform variants, and an MCP server "
                "so AI assistants can schedule posts by conversation.",
        "metric": None,
    },
    {
        "file": "devops-brasil",
        "name": "DevOps Brasil",
        "handle": "@DevOps-Brasil",
        "logo": "devops-brasil.jpg",
        "logo_box": (48, 26, 68, 68),
        "tagline": "Comunidade brasileira de DevOps, SRE, Cloud, Platform Engineering e Infra.",
        "body": "O board de Vagas é o carro-chefe da org.",
        "metric": ("DevOps-Brasil/Vagas", "stars on Vagas"),
    },
]

NAME_COL = 285        # x where the description column starts
STAR_COL = svg.W - 48  # right edge for the star count


def die(msg):
    print(f"generate_projects: {msg}", file=sys.stderr)
    sys.exit(1)


def token():
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except Exception:
        die("no GITHUB_TOKEN in the environment and `gh auth token` is unavailable")


def fetch_stars(slugs):
    fields = []
    for i, slug in enumerate(slugs):
        owner, name = slug.split("/", 1)
        fields.append(f'r{i}: repository(owner:"{owner}", name:"{name}"){{ stargazerCount }}')
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": "query{" + " ".join(fields) + "}"}).encode(),
        headers={
            "Authorization": f"bearer {token()}",
            "Content-Type": "application/json",
            "User-Agent": "youhide-profile-stats",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as exc:
        die(f"GitHub API returned HTTP {exc.code}: {exc.read()[:200].decode('utf-8', 'replace')}")
    except urllib.error.URLError as exc:
        die(f"could not reach the GitHub API: {exc.reason}")
    if payload.get("errors"):
        die(f"GraphQL errors: {json.dumps(payload['errors'])[:300]}")

    stars = {}
    for i, slug in enumerate(slugs):
        node = payload["data"].get(f"r{i}")
        if not node:
            die(f"repository '{slug}' returned no data — refusing to render a card without its count")
        stars[slug] = node["stargazerCount"]
    return stars


def project_card(slug, name, stack, description, stars):
    desc_width = STAR_COL - 130 - NAME_COL
    lines = svg.wrap(description, 15, desc_width)
    height = 86 if len(lines) < 2 else 86 + (len(lines) - 1) * 22

    mid = height / 2
    body = [
        f'    <text x="{svg.PAD}" y="{mid - 2:.0f}" font-size="19" font-weight="700" '
        f'fill="{svg.PURPLE}">{svg.esc(name)}</text>',
        f'    <text x="{svg.PAD}" y="{mid + 20:.0f}" font-size="13" '
        f'fill="{svg.COMMENT}">{svg.esc(stack)}</text>',
    ]
    first = mid + 5 - (len(lines) - 1) * 11
    for i, line in enumerate(lines):
        body.append(
            f'    <text x="{NAME_COL}" y="{first + i * 22:.0f}" font-size="15" '
            f'fill="{svg.FG}">{svg.esc(line)}</text>'
        )
    body.append(
        f'    <text x="{STAR_COL}" y="{mid + 5:.0f}" text-anchor="end" font-size="16" '
        f'fill="{svg.YELLOW}">★ {stars}</text>'
    )

    aria = f"{name} ({stack}) — {description}. {stars} stars on GitHub."
    return svg.row_card(height, "\n".join(body), aria)


def org_card(org, stars):
    lines = svg.wrap(org["body"], 15, STAR_COL - NAME_COL - 150)
    height = 150
    lx, ly, lw, lh = org["logo_box"]

    clip_defs, clip_id = "", None
    if org["file"] == "devops-brasil":  # round avatar
        clip_id = "avatar"
        clip_defs = (
            f'\n    <clipPath id="avatar">'
            f'<circle cx="{lx + lw / 2}" cy="{ly + lh / 2}" r="{lw / 2}"/></clipPath>'
        )

    body = [
        "    " + svg.embed_image(
            os.path.join(ROOT, "assets", "logos", org["logo"]), lx, ly, lw, lh, clip_id
        ),
        f'    <text x="{svg.PAD}" y="{ly + lh + 26}" font-size="13" '
        f'fill="{svg.COMMENT}">{svg.esc(org["handle"])}</text>',
        f'    <text x="{NAME_COL}" y="46" font-size="15" font-style="italic" '
        f'fill="{svg.CYAN}">{svg.esc(org["tagline"])}</text>',
    ]
    for i, line in enumerate(lines):
        body.append(
            f'    <text x="{NAME_COL}" y="{78 + i * 22}" font-size="15" '
            f'fill="{svg.FG}">{svg.esc(line)}</text>'
        )
    if org["metric"]:
        slug, label = org["metric"]
        body.append(
            f'    <text x="{STAR_COL}" y="{height - 30}" text-anchor="end" font-size="16" '
            f'fill="{svg.YELLOW}">★ {stars[slug]} <tspan fill="{svg.COMMENT}" font-size="13">'
            f'{svg.esc(label)}</tspan></text>'
        )

    aria = f'{org["name"]} ({org["handle"]}) — {org["tagline"]} {org["body"]}'
    return svg.row_card(height, "\n".join(body), aria, clip_defs)


def write(path, markup):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as handle:
        handle.write(markup)
    return os.path.getsize(full)


def main():
    slugs = [p[0] for p in PROJECTS] + [o["metric"][0] for o in ORGS if o["metric"]]
    stars = fetch_stars(slugs)

    for slug, name, stack, description in PROJECTS:
        path = f"assets/projects/{slug.split('/')[1].lower()}.svg"
        write(path, project_card(slug, name, stack, description, stars[slug]))

    for org in ORGS:
        write(f"assets/building/{org['file']}.svg", org_card(org, stars))

    write("assets/labels/projects.svg", svg.label_strip("youhide@homelab: ~/projects"))
    write("assets/labels/building.svg", svg.label_strip("youhide@homelab: ~/where-i-build"))

    print(f"wrote {len(PROJECTS)} project cards, {len(ORGS)} org cards, 2 labels")
    for slug in slugs:
        print(f"  {slug}: {stars[slug]} stars")


if __name__ == "__main__":
    main()
