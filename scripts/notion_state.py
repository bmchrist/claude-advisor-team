#!/usr/bin/env python3
"""Read and write analyses/{slug}/.notion safely under concurrency.

The three advisors run in parallel and each records its sub-page id in the
same `.notion` file. A plain read-modify-write can drop one of them, so all
writes go through this script, which holds an exclusive `fcntl` lock on
`analyses/{slug}/.notion.lock` for the whole read-modify-write and replaces
the file atomically.

Usage:
  python3 scripts/notion_state.py set <slug> <key> <value> [<key> <value> ...]
      Set one or more keys (e.g. main_page_id and main_page_url together).
      Creates .notion if missing. Existing keys keep their position; new
      keys are appended. Prints `set: <key>` per key.
  python3 scripts/notion_state.py get <slug> <key>
      Prints the value, or nothing (exit 1) if the key is absent.

File format is unchanged: one `key="value"` line per key. A line starting
`ERROR:` means the caller should report it and stop.
"""
import fcntl
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_RE = re.compile(r"^[A-Za-z0-9_]+$")
LINE_RE = re.compile(r'^\s*([A-Za-z0-9_]+)\s*=\s*"?(.*?)"?\s*$')


def fail(msg):
    print(f"ERROR: {msg}")
    sys.exit(2)


def paths(slug):
    d = os.path.join(ROOT, "analyses", slug)
    if not re.match(r"^[a-z0-9_]+$", slug) or not os.path.isdir(d):
        fail(f"no analysis directory analyses/{slug}")
    return d, os.path.join(d, ".notion"), os.path.join(d, ".notion.lock")


def parse(path):
    items = []
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            m = LINE_RE.match(line)
            if m:
                items.append([m.group(1), m.group(2)])
    return items


def cmd_set(slug, pairs):
    if not pairs or len(pairs) % 2:
        fail("set needs <key> <value> pairs")
    updates = list(zip(pairs[::2], pairs[1::2]))
    for k, v in updates:
        if not KEY_RE.match(k):
            fail(f"invalid key {k!r}")
        if '"' in v or "\n" in v:
            fail(f"value for {k} contains a quote or newline")
    d, path, lock = paths(slug)
    with open(lock, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        items = parse(path)
        for k, v in updates:
            for item in items:
                if item[0] == k:
                    item[1] = v
                    break
            else:
                items.append([k, v])
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".notion.")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.writelines(f'{k}="{v}"\n' for k, v in items)
        os.replace(tmp, path)
    for k, _ in updates:
        print(f"set: {k}")


def cmd_get(slug, key):
    _, path, lock = paths(slug)
    with open(lock, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_SH)
        items = dict(parse(path))
    if key in items:
        print(items[key])
    else:
        sys.exit(1)


def main():
    a = sys.argv[1:]
    if len(a) >= 3 and a[0] == "set":
        cmd_set(a[1], a[2:])
    elif len(a) == 3 and a[0] == "get":
        cmd_get(a[1], a[2])
    else:
        fail("usage: notion_state.py set <slug> <key> <value> [...] | get <slug> <key>")


if __name__ == "__main__":
    main()
