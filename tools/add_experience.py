#!/usr/bin/env python3
"""Add hand-written experience items to the knowledge base from a JSON file.

    python3 tools/add_experience.py paiger.json [--api http://localhost:8000] [--yes]

The file is a list of items in the knowledge-base shape:
    [{"type": "experience", "title": "Full-Stack Developer", "company": "Acme",
      "date_range": "Jan 2021 - Present", "context": "Billing",
      "accomplishment": "Built ...", "technologies": ["Node.js"], "skills": [],
      "impact": null}]

Existing items from the same employer that say nearly the same thing as a new
one are listed and removed, so a resume never gets two bullets for one piece of
work. Items that are not covered by the new ones are kept. Nothing changes until
you confirm. Stdlib only.
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

OVERLAP = 0.35  # share of the shorter item's words that must also be in the other
_STOP = set("a an and the of for in on to with across from by as at into via using plus its their "
            "including more than".split())


def call(api, method, path, obj=None):
    body = json.dumps(obj).encode() if obj is not None else None
    req = urllib.request.Request(api + path, data=body, method=method,
                                 headers={"Content-Type": "application/json"} if body else {})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read() or b"null")


def words(text):
    return {w for w in re.findall(r"[a-z0-9+#.]+", (text or "").lower()) if w not in _STOP and len(w) > 2}


def overlap(a, b):
    wa, wb = words(a), words(b)
    return len(wa & wb) / max(1, min(len(wa), len(wb)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=Path)
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()

    new = json.loads(a.file.expanduser().read_text())
    existing = call(a.api, "GET", "/kb/chunks")
    companies = {(n.get("company") or "").lower() for n in new}
    replaced = [
        e for e in existing
        if (e.get("company") or "").lower() in companies
        and any(overlap(e["accomplishment"], n["accomplishment"]) >= OVERLAP for n in new)
    ]
    kept = [e for e in existing if (e.get("company") or "").lower() in companies and e not in replaced]

    print(f"Adding {len(new)} item(s):")
    for n in new:
        print(f"  + {n['accomplishment']}")
    if replaced:
        print(f"\nRemoving {len(replaced)} existing item(s) the new ones cover:")
        for e in replaced:
            print(f"  - [{e['id']}] {e['accomplishment']}")
    if kept:
        print(f"\nKeeping {len(kept)} existing item(s) from the same employer:")
        for e in kept:
            print(f"  = [{e['id']}] {e['accomplishment']}")
    if not a.yes and input("\nApply? [y/N] ").lower() != "y":
        sys.exit("Nothing changed.")
    saved = call(a.api, "POST", "/kb/chunks/bulk", new)
    for e in replaced:
        call(a.api, "DELETE", f"/kb/chunks/{e['id']}")
    print(f"Added {len(saved)}, removed {len(replaced)}.")


if __name__ == "__main__":
    main()
