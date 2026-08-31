#!/usr/bin/env python3
"""Refresh the star/follower counts embedded in README.md.

The counts live between markers so the surrounding table stays hand-written:

    <!--stars:youhide/OpenShard-->8<!--/stars-->
    <!--followers:DevOps-Brasil-->12<!--/followers-->

Only public data is needed, so the default Actions GITHUB_TOKEN is enough.
"""

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.github.com/graphql"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")

STAR_RE = re.compile(r"(<!--stars:([^>]+?)-->)(.*?)(<!--/stars-->)", re.S)
FOLLOWER_RE = re.compile(r"(<!--followers:([^>]+?)-->)(.*?)(<!--/followers-->)", re.S)


def die(msg):
    print(f"update_readme: {msg}", file=sys.stderr)
    sys.exit(1)


def token():
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except Exception:
        die("no GITHUB_TOKEN in the environment and `gh auth token` is unavailable")


def rest(path, tok):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"bearer {tok}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "youhide-profile-stats",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        die(f"GitHub REST returned HTTP {exc.code} for {path}")
    except urllib.error.URLError as exc:
        die(f"could not reach the GitHub API: {exc.reason}")


def graphql(query, tok):
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"bearer {tok}",
            "Content-Type": "application/json",
            "User-Agent": "youhide-profile-stats",
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


def main():
    text = open(README, encoding="utf-8").read()

    repos = [m.group(2) for m in STAR_RE.finditer(text)]
    orgs = [m.group(2) for m in FOLLOWER_RE.finditer(text)]
    if not repos:
        die("no <!--stars:...--> markers found in README.md")

    fields = []
    for i, slug in enumerate(repos):
        try:
            owner, name = slug.split("/", 1)
        except ValueError:
            die(f"marker '{slug}' is not in owner/repo form")
        fields.append(f'r{i}: repository(owner:"{owner}", name:"{name}"){{ stargazerCount }}')
    tok = token()
    data = graphql("query{" + " ".join(fields) + "}", tok)

    stars, members = {}, {}
    for i, slug in enumerate(repos):
        node = data.get(f"r{i}")
        if not node:
            die(f"repository '{slug}' returned no data — refusing to blank out its count")
        stars[slug] = node["stargazerCount"]
    for login in orgs:
        count = rest(f"/orgs/{login}", tok).get("followers")
        if count is None:
            die(f"organization '{login}' returned no follower count")
        members[login] = count

    def star_sub(match):
        return f"{match.group(1)}⭐ {stars[match.group(2)]}{match.group(4)}"

    def follower_sub(match):
        return f"{match.group(1)}👥 {members[match.group(2)]}{match.group(4)}"

    updated = FOLLOWER_RE.sub(follower_sub, STAR_RE.sub(star_sub, text))

    if updated == text:
        print("README.md already up to date")
        return
    with open(README, "w", encoding="utf-8") as handle:
        handle.write(updated)
    print(f"updated README.md — {len(stars)} repos, {len(members)} orgs")
    for login, count in members.items():
        print(f"  {login}: {count} followers")
    for slug, count in stars.items():
        print(f"  {slug}: {count}")


if __name__ == "__main__":
    main()
