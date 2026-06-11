#!/usr/bin/env python3
"""Resolve a `[company-or-slug]` target to an analysis slug.

Used by every pipeline skill except /research. Shared here so the
resolution algorithm (slugify, .last_target fallback, .meta lookup) lives
in exactly one place — see CLAUDE.md's "State" section for the convention
this implements.

Usage: python3 scripts/resolve_target.py "$target"

On success, prints `company:`, `slug:`, `type:` lines (read from
analyses/{slug}/.meta) and updates analyses/.last_target to the resolved
slug. On failure, prints a single line starting with `ERROR:` and exits
with status 0 (the caller is expected to check for that prefix, not the
exit code, and report it verbatim).
"""
import re
import os
import sys

target = sys.argv[1] if len(sys.argv) > 1 else ""
target = target.strip().strip('"').strip("'")


def slugify(s):
    s = s.lower().replace('+', '_plus').replace('&', '_and_')
    return re.sub(r'[^a-z0-9]+', '_', s).strip('_')


if target:
    slug = slugify(target)
elif os.path.exists('analyses/.last_target'):
    slug = open('analyses/.last_target').read().strip()
else:
    slug = None

if slug is None:
    print('ERROR: No target given and no analyses/.last_target found. '
          'Run /research "Company" TYPE first, or pass a company name or slug.')
elif not os.path.exists(f'analyses/{slug}/.meta'):
    print(f'ERROR: No analysis found for "{target or slug}" '
          f'(expected analyses/{slug}/.meta). Run /research first, or check the company name/slug.')
else:
    meta = {}
    for line in open(f'analyses/{slug}/.meta'):
        line = line.strip()
        if not line or '=' not in line:
            continue
        k, v = line.split('=', 1)
        meta[k] = v.strip('"')
    open('analyses/.last_target', 'w').write(slug + '\n')
    print(f'company: {meta.get("company", "")}')
    print(f'slug:    {slug}')
    print(f'type:    {meta.get("type", "")}')
