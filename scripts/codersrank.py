"""Shared CodersRank client.

The public API intermittently answers with an empty body — in one sample, 3 of
4 consecutive calls to /languages returned zero languages while the 4th
returned 29. A single attempt therefore can't tell "this user has no data"
apart from "the API hiccuped", so every read retries until it sees a payload
that passes the caller's own sanity check.
"""

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "https://api.codersrank.io/v2/users"
ATTEMPTS = 4
BACKOFF = 3  # seconds, multiplied by the attempt number


def get(login, path, is_valid, what):
    """Fetch BASE/<login><path>, retrying until `is_valid(payload)` holds.

    Returns the payload, or None when every attempt failed — callers decide
    whether that is fatal, so a flaky endpoint leaves the previous card intact
    instead of publishing an empty one.
    """
    url = f"{BASE}/{login}{path}?get_by=username"
    req = urllib.request.Request(url, headers={"User-Agent": f"{login}-profile-stats"})

    for attempt in range(1, ATTEMPTS + 1):
        reason = None
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.load(resp)
            if is_valid(payload):
                if attempt > 1:
                    print(f"  {what}: recovered on attempt {attempt}", file=sys.stderr)
                return payload
            reason = "empty or unusable payload"
        except urllib.error.HTTPError as exc:
            reason = f"HTTP {exc.code}"
        except urllib.error.URLError as exc:
            reason = f"unreachable ({exc.reason})"
        except json.JSONDecodeError:
            reason = "malformed JSON"

        print(f"  {what}: attempt {attempt}/{ATTEMPTS} failed — {reason}", file=sys.stderr)
        if attempt < ATTEMPTS:
            time.sleep(BACKOFF * attempt)

    return None
