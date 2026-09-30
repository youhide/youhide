#!/usr/bin/env python3
"""Stamp each generated asset's URL in README.md with a content hash.

GitHub's image proxy serves cards with `cache-control: max-age=86400`,
ignoring the shorter max-age raw.githubusercontent sets. A regenerated card
can therefore keep showing stale numbers long after the workflow ran. Giving
the URL a ?v=<hash> that changes only when the file changes makes camo treat
it as a new image, so an updated card appears immediately.
"""

import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")

# matches .../main/<path>.svg with an optional existing ?v=... stamp
ASSET_RE = re.compile(
    r"(https://raw\.githubusercontent\.com/youhide/youhide/main/)([\w./-]+\.svg)(\?v=[0-9a-f]+)?"
)


def die(msg):
    print(f"bust_cache: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    text = open(README, encoding="utf-8").read()
    stamped = {}

    def replace(match):
        base, path = match.group(1), match.group(2)
        full = os.path.join(ROOT, path)
        if not os.path.isfile(full):
            die(f"README references {path}, which does not exist")
        if path not in stamped:
            with open(full, "rb") as handle:
                stamped[path] = hashlib.sha256(handle.read()).hexdigest()[:8]
        return f"{base}{path}?v={stamped[path]}"

    updated = ASSET_RE.sub(replace, text)
    if not stamped:
        die("no asset URLs found in README.md — the pattern may have drifted")

    if updated == text:
        print(f"README.md already stamped — {len(stamped)} assets unchanged")
        return

    with open(README, "w", encoding="utf-8") as handle:
        handle.write(updated)
    print(f"stamped {len(stamped)} asset URLs in README.md")


if __name__ == "__main__":
    main()
