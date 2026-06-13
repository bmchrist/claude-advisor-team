#!/usr/bin/env python3
"""Resolve a `[company-or-slug]` target to an analysis slug, or bootstrap a
new analysis.

Used by every pipeline skill. Shared here so the resolution algorithm
(slugify, sanitization, .last_target fallback, .meta lookup/validation, and
near-miss slug detection) lives in exactly one place — see CLAUDE.md's
"State" and "Slug convention" sections for the conventions this implements.

Usage:
  python3 scripts/resolve_target.py "$target"
      Resolve an existing analysis (the original mode, used by every skill
      except /research and /ingest-materials). Prints `company:` / `slug:`
      / `type:` and updates analyses/.last_target. On failure, prints a
      single line starting `ERROR:`.

  python3 scripts/resolve_target.py --slug-only "Company"
      Print just `slug:` for "Company" (used by /ingest-materials, which
      runs before .meta exists and so can't use the default mode above).
      Also checks for a near-miss sibling analysis and prints a `WARNING:`
      line if found. Does not touch .last_target or create anything.

  python3 scripts/resolve_target.py --new "Company" "TYPE"
      Bootstrap a new analysis (used by /research): sanitize "Company",
      validate "TYPE" against DEAL|TECHNOLOGY|POLICY, create
      analyses/{slug}/ and write its .meta, and print `company:` / `slug:`
      / `type:` / `date:`. Also checks for a near-miss sibling. Does NOT
      update analyses/.last_target — /research's Setup does that itself
      once this returns successfully, since the repoint should happen at
      the point /research commits to this analysis as the new target, not
      as a side effect of this script.

In all modes, a line starting `ERROR:` means the caller should stop and
report it to Ben verbatim. A line starting `WARNING:` is informational —
surface it in the final summary but don't block.
"""
import datetime
import re
import os
import sys

VALID_TYPES = {'DEAL', 'TECHNOLOGY', 'POLICY'}


def slugify(s):
    s = s.lower().replace('+', '_plus').replace('&', '_and_')
    return re.sub(r'[^a-z0-9]+', '_', s).strip('_')


def sanitize_company(s):
    """Strip surrounding straight/curly quotes and whitespace. Reject `"`,
    `$`, and `\\` outright — these can't be safely round-tripped through a
    quoted .meta value or a shell heredoc (B1, D3)."""
    s = s.strip().strip('"\'').strip('“”‘’').strip()
    for bad in ('"', '$', '\\'):
        if bad in s:
            print(f'ERROR: company name contains {bad!r}, which cannot be '
                  f'safely written to .meta or interpolated into a shell '
                  f'heredoc. Re-run with that character removed or '
                  f'replaced.')
            sys.exit(0)
    return s


def near_miss_warning(slug):
    """If another analyses/<sibling> exists whose slug is a prefix of (or
    prefixed by) `slug`, and that sibling has 00_deal_materials/ but no
    .meta (i.e. /ingest-materials output not yet adopted by /research),
    return a WARNING line. Otherwise None."""
    if not os.path.isdir('analyses'):
        return None
    for sibling in sorted(os.listdir('analyses')):
        if sibling == slug or sibling.startswith('.'):
            continue
        sibling_dir = os.path.join('analyses', sibling)
        if not os.path.isdir(sibling_dir):
            continue
        if not (sibling.startswith(slug) or slug.startswith(sibling)):
            continue
        has_materials = os.path.isdir(os.path.join(sibling_dir, '00_deal_materials'))
        has_meta = os.path.exists(os.path.join(sibling_dir, '.meta'))
        if has_materials and not has_meta:
            return (f'WARNING: possible slug mismatch with existing '
                    f'analyses/{sibling}/00_deal_materials/ — confirm this '
                    f'is a different company')
    return None


args = sys.argv[1:]
mode = args[0] if args and args[0].startswith('--') else None

if mode == '--slug-only':
    company = sanitize_company(args[1]) if len(args) > 1 else ''
    if not company:
        print('ERROR: --slug-only requires a non-empty company name')
    else:
        slug = slugify(company)
        print(f'slug: {slug}')
        warning = near_miss_warning(slug)
        if warning:
            print(warning)

elif mode == '--new':
    company = sanitize_company(args[1]) if len(args) > 1 else ''
    type_in = args[2].strip().strip('"\'') if len(args) > 2 else ''
    type_ = type_in.upper()
    if not company:
        print('ERROR: --new requires a non-empty company name')
    elif type_ not in VALID_TYPES:
        print(f'ERROR: invalid type \'{type_in}\' — expected '
              f'DEAL|TECHNOLOGY|POLICY')
    else:
        slug = slugify(company)
        warning = near_miss_warning(slug)
        os.makedirs(f'analyses/{slug}', exist_ok=True)
        with open(f'analyses/{slug}/.meta', 'w') as f:
            f.write(f'company="{company}"\nslug="{slug}"\ntype="{type_}"\n')
        print(f'company: {company}')
        print(f'slug:    {slug}')
        print(f'type:    {type_}')
        print(f'date:    {datetime.date.today().isoformat()}')
        if warning:
            print(warning)

else:
    target = args[0] if args else ""
    target = target.strip().strip('"').strip("'")

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
            meta[k] = v.strip('"“”\'')

        type_ = meta.get('type', '').upper()
        if type_ not in VALID_TYPES:
            print(f'ERROR: invalid type \'{meta.get("type", "")}\' in '
                  f'analyses/{slug}/.meta — expected DEAL|TECHNOLOGY|POLICY')
        else:
            open('analyses/.last_target', 'w').write(slug + '\n')
            print(f'company: {meta.get("company", "")}')
            print(f'slug:    {slug}')
            print(f'type:    {type_}')
