#!/usr/bin/env python3
"""One-time setup for headless use (no web UI): set your profile and load your
experience into the knowledge base from your existing resume.

    python3 tools/import_resume.py --resume ~/cv.pdf \
        --name "Your Name" --email you@example.com [--phone ...] [--location ...] \
        [--link github=https://github.com/you --link linkedin=https://...]
        [--api http://localhost:8000] [--yes]

Parsing runs the local model over the whole document, so on a Pi it takes a
while. Everything the model proposes is printed before it is saved; nothing is
saved unless you confirm (or pass --yes). Stdlib only, so it runs anywhere.
"""
import argparse
import json
import mimetypes
import sys
import time
import urllib.request
import uuid
from pathlib import Path


def call(api, method, path, body=None, headers=None, timeout=60):
    req = urllib.request.Request(api + path, data=body, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"null")


def post_json(api, method, path, obj):
    return call(api, method, path, json.dumps(obj).encode(), {"Content-Type": "application/json"})


def post_file(api, path, file):
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"{file.name}\"\r\n"
        f"Content-Type: {ctype}\r\n\r\n"
    ).encode() + file.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    return call(api, "POST", path, body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--resume", type=Path, help="PDF, DOCX or TXT")
    ap.add_argument("--name"); ap.add_argument("--email")
    ap.add_argument("--phone", default=""); ap.add_argument("--location", default="")
    ap.add_argument("--summary", default=""); ap.add_argument("--education", default="")
    ap.add_argument("--link", action="append", default=[], help="label=url, repeatable")
    ap.add_argument("--yes", action="store_true", help="save without asking")
    a = ap.parse_args()

    # The backend takes a while to start (it loads PyTorch), so a run straight
    # after a restart waits for it instead of failing with "connection refused".
    for attempt in range(60):
        try:
            call(a.api, "GET", "/health", timeout=5)
            break
        except OSError:
            if attempt == 0:
                print(f"Waiting for the backend at {a.api} ...", flush=True)
            time.sleep(3)
    else:
        sys.exit(f"The backend at {a.api} isn't answering. Check: journalctl -u unemployed-api -n 50")

    if a.name or a.email:
        current = call(a.api, "GET", "/profile")
        profile = {k: current.get(k) for k in
                   ("name", "email", "phone", "location", "links", "summary", "education", "college")}
        for k in ("name", "email", "phone", "location", "summary", "education"):
            if getattr(a, k):
                profile[k] = getattr(a, k)
        if a.link:
            profile["links"] = dict(pair.split("=", 1) for pair in a.link)
        post_json(a.api, "PUT", "/profile", profile)
        print(f"Profile saved: {profile['name']} <{profile['email']}>")

    if not a.resume:
        return
    job = post_file(a.api, "/kb/parse", a.resume.expanduser())
    print(f"Parsing {a.resume.name} (this is the slow part)...")
    while job["status"] == "running":
        time.sleep(10)
        job = call(a.api, "GET", f"/kb/parse/{job['id']}")
        print("  ", job.get("message") or job.get("progress") or "working...", flush=True)
    if job["status"] != "done":
        sys.exit(f"Parsing failed: {job}")

    for err in job.get("errors") or []:
        print(f"  ! {err}")
    chunks = job["chunks"]
    for i, c in enumerate(chunks, 1):
        print(f"\n[{i}] {c.get('title')} @ {c.get('company') or '-'} ({c.get('date_range') or '-'})")
        print(f"    {c['accomplishment']}")
        if c.get("technologies"):
            print(f"    tech: {', '.join(c['technologies'])}")
    if not chunks:
        sys.exit("Nothing was found in that document."
                 + (" The errors above say why." if job.get("errors") else
                    " If it is a scanned/image PDF there is no text to read; try a .docx or .txt."))
    if not a.yes and input(f"\nSave these {len(chunks)} items to the knowledge base? [y/N] ").lower() != "y":
        sys.exit("Not saved.")
    saved = post_json(a.api, "POST", "/kb/chunks/bulk", chunks)
    print(f"Saved {len(saved)} items.")


if __name__ == "__main__":
    main()
