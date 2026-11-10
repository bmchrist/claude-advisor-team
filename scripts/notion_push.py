#!/usr/bin/env python3
"""Push an analysis to Notion through the REST API, without the MCP.

Usage:
  python3 scripts/notion_push.py <slug> <stage> [<stage> ...]
  python3 scripts/notion_push.py <slug> all
  python3 scripts/notion_push.py --check
  (add --bootstrap to create a missing main page even when stage 1 isn't
   listed, as /notion-sync does; add --dry-run to print the requests instead of sending them; no token
   needed, nothing written to .notion)

  <stage> takes the same values as notion_body.py: research|1, science|2a,
  investment|2b, political|2c, bull|3, bear|4, executive|5, compare|6.
  Several stages run in the order given. `all` = bootstrap if needed, then
  every stage with a local file, executive last so it links every sub-page.

Payloads come from notion_body.py (same strip and escape rules as the MCP
path), and page ids are recorded through notion_state.py (locked writes).

Token: $NOTION_TOKEN, else the macOS Keychain item with service
`notion-pipeline`. With no token, or one Notion rejects, or one whose
integration can't see the database, it prints `MODE: mcp` (plus a
`WARNING:` line when a token exists but doesn't work) and exits 3: the
caller then uses the MCP procedures in .claude/skills/notion-sync/REFERENCE.md.

Output, one line per item:
  created: <stage> <page id>     updated: <stage>
  skipped: <stage> — <reason>    error: <stage> — <message>
then `OMITTED: ...` (executive properties left out as n/a), and finally
`Notion: <main page url>` if nothing failed, or `ERROR: <n> item(s) failed`
(exit 1). The token is never printed.
"""
import datetime
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

import notion_body as nb

API = "https://api.notion.com/v1"
NOTION_VERSION = "2026-03-11"
MARKDOWN_VERSION = "v2"
DATA_SOURCE_ID = "8a829f17-bcb4-49d0-8562-26a0e6342df1"
KEYCHAIN_SERVICE = "notion-pipeline"
TIMEOUT = 90
MAX_TRIES = 3

ROOT = nb.ROOT
STAGE_NAMES = {"1": "research", "2a": "science", "2b": "investment", "2c": "political",
               "3": "bull", "4": "bear", "5": "executive", "6": "compare"}
ALL_ORDER = ["1", "2a", "2b", "2c", "3", "4", "6", "5"]

BOOTSTRAP_BODY = """> **Grade: pending**
> Run /executive to populate the grade, scorecard, and narrative.

## Executive Narrative
_Pending — run /executive to populate this analysis._

## Stage Reports
Full write-ups for each pipeline stage are linked as sub-pages below."""

# Flat (MCP-style) property name -> REST property name and value shape.
SELECTS = ("Grade", "Status", "Technical Confidence", "Commercial Confidence")


class NotionError(Exception):
    def __init__(self, status, code, message):
        super().__init__(f"{status} {code}: {message}")
        self.status, self.code = status, code


class UseMCP(Exception):
    """The token is missing or can't reach the database: fall back to MCP."""


# --- token and HTTP ----------------------------------------------------------

def find_token():
    tok = os.environ.get("NOTION_TOKEN", "").strip()
    if tok:
        return tok, "NOTION_TOKEN"
    try:
        r = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None, None
    tok = r.stdout.strip() if r.returncode == 0 else ""
    return (tok, "Keychain") if tok else (None, None)


class Client:
    def __init__(self, token, dry_run=False):
        self.token, self.dry_run, self.fake = token, dry_run, 0

    def call(self, method, path, body=None):
        if self.dry_run:
            return self._dry(method, path, body)
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(1, MAX_TRIES + 1):
            req = urllib.request.Request(API + path, data=data, method=method, headers={
                "Authorization": f"Bearer {self.token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            })
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    return json.loads(resp.read() or b"{}")
            except urllib.error.HTTPError as e:
                try:
                    err = json.loads(e.read() or b"{}")
                except ValueError:
                    err = {}
                retryable = e.code == 429 or e.code >= 500
                if retryable and attempt < MAX_TRIES:
                    wait = e.headers.get("Retry-After") if e.code == 429 else None
                    time.sleep(float(wait) if wait else 4 ** (attempt - 1))
                    continue
                raise NotionError(e.code, err.get("code", "http_error"),
                                  err.get("message", e.reason)) from None
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                if attempt < MAX_TRIES:
                    time.sleep(4 ** (attempt - 1))
                    continue
                raise NotionError(0, "network_error", str(getattr(e, "reason", e))) from None

    def _dry(self, method, path, body):
        shown = json.loads(json.dumps(body)) if body else None
        for holder in (shown or {}, (shown or {}).get("replace_content") or {}):
            for k in ("markdown", "new_str"):
                if isinstance(holder.get(k), str):
                    v = holder[k]
                    holder[k] = f"<{len(v)} chars: {v[:60]!r}…>"
        print(f"DRY {method} {path} {json.dumps(shown, ensure_ascii=False) if shown else ''}".rstrip())
        self.fake += 1
        fid = f"dry-run-{self.fake:04d}"
        return {"id": fid, "url": f"https://www.notion.so/{fid}", "markdown": ""}


# --- state -------------------------------------------------------------------

def notion_state(slug):
    return nb.read_kv(os.path.join(ROOT, "analyses", slug, ".notion"))


def record(slug, pairs, dry_run):
    if dry_run:
        return
    args = [sys.executable, os.path.join(ROOT, "scripts", "notion_state.py"), "set", slug]
    for k, v in pairs:
        args += [k, v]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise NotionError(0, "state_write_failed", (r.stdout + r.stderr).strip())


# --- Notion operations -------------------------------------------------------

def rich(text):
    return [{"type": "text", "text": {"content": text[i:i + 2000]}} for i in range(0, len(text), 2000)] or []


def rest_properties(flat):
    """notion_body.properties(escape=False) output -> REST property values."""
    out = {}
    for k, v in flat.items():
        if k in SELECTS:
            out[k] = {"select": {"name": v}}
        elif k == "Grade driver":
            out[k] = {"rich_text": rich(v)}
        elif k == "date:Analysis Date:start":
            out["Analysis Date"] = {"date": {"start": v}}
    return out


def create_page(c, parent, properties, markdown):
    return c.call("POST", "/pages", {"parent": parent, "properties": properties,
                                     "markdown": markdown, "markdown_version": MARKDOWN_VERSION})


def replace_body(c, page_id, markdown):
    return c.call("PATCH", f"/pages/{page_id}/markdown", {
        "type": "replace_content", "replace_content": {"new_str": markdown},
        "markdown_version": MARKDOWN_VERSION})


def preflight(c):
    """Fail over to MCP if the token is rejected or can't see the database."""
    try:
        c.call("GET", f"/data_sources/{DATA_SOURCE_ID}")
    except NotionError as e:
        if e.status == 401:
            raise UseMCP("Notion rejected the API token (401 unauthorized)") from None
        if e.status in (403, 404):
            raise UseMCP("the API integration can't see the Investment Analysis Pipeline "
                         "database; add it under Connections on the Investments page") from None
        raise


def bootstrap(c, slug, out):
    meta = nb.read_kv(os.path.join(ROOT, "analyses", slug, ".meta"))
    company, atype = meta.get("company") or slug, meta.get("type")
    props = {"Name": {"title": rich(company)}, "Slug": {"rich_text": rich(slug)},
             "Analysis Date": {"date": {"start": datetime.date.today().isoformat()}}}
    if atype:
        props["Type"] = {"select": {"name": atype}}
    page = create_page(c, {"type": "data_source_id", "data_source_id": DATA_SOURCE_ID},
                       props, BOOTSTRAP_BODY)
    record(slug, [("main_page_id", page["id"]), ("main_page_url", page["url"])], c.dry_run)
    out.append(f"created: main page {page['id']}")
    return page["id"], page["url"]


def subpage_target(slug, stage, facts):
    """(.notion key, title, extra state pairs) for a sub-page stage."""
    if stage != "6":
        return facts[stage]["key"], facts[stage]["title"], []
    text = nb.read_stage_file(slug, "6", facts)
    fm = nb.parse_frontmatter(text)
    key, title = fm.get("notion_key"), fm.get("notion_title")
    if not key or not re.match(r"^compare_\w+_page_id$", key) or not title:
        raise nb.BodyError("06_run_comparison.md frontmatter needs notion_key and notion_title")
    return key, title, [(key[:-len("_id")] + "_title", title)]


def push_subpage(c, slug, stage, facts, main_id, out):
    payload = nb.build_payload(slug, stage, facts)
    key, title, extra = subpage_target(slug, stage, facts)
    existing = notion_state(slug).get(key)
    if existing:
        replace_body(c, existing, payload)
        if extra:
            record(slug, extra, c.dry_run)
        out.append(f"updated: {STAGE_NAMES[stage]}")
        return
    page = create_page(c, {"type": "page_id", "page_id": main_id},
                       {"title": {"title": rich(title)}}, payload)
    record(slug, [(key, page["id"])] + extra, c.dry_run)
    out.append(f"created: {STAGE_NAMES[stage]} {page['id']}")


def push_executive(c, slug, facts, main_id, out, notes):
    flat, omitted = nb.build_properties(slug, escape=False, facts=facts)
    if omitted:
        notes.append("OMITTED: " + ", ".join(omitted))
    c.call("PATCH", f"/pages/{main_id}", {"properties": rest_properties(flat)})
    replace_body(c, main_id, nb.build_payload(slug, "5", facts))
    if not c.dry_run:
        got = c.call("GET", f"/pages/{main_id}/markdown?markdown_version={MARKDOWN_VERSION}")
        text = (got.get("markdown") or "").replace("-", "")
        state = notion_state(slug)
        missing = [k for k, v in state.items()
                   if re.match(r"^(stage\w+|compare_\w+)_page_id$", k) and v.replace("-", "") not in text]
        if missing:
            raise NotionError(0, "subpage_link_missing",
                              "main page no longer links " + ", ".join(missing)
                              + " (recoverable from Notion's trash; /notion-sync can re-push)")
    out.append("updated: executive (main page)")


# --- driver ------------------------------------------------------------------

def run(slug, stages, dry_run, allow_bootstrap=False):
    facts = nb.load_stage_facts()
    if not os.path.isdir(os.path.join(ROOT, "analyses", slug)):
        print(f"ERROR: no analysis directory analyses/{slug}")
        return 1
    token, _ = find_token()
    if not token and not dry_run:
        print("MODE: mcp")
        return 3
    c = Client(token, dry_run)
    out, notes, errors = [], [], 0
    try:
        if not dry_run:
            preflight(c)
    except UseMCP as e:
        print("MODE: mcp")
        print(f"WARNING: {e}; run python3 scripts/notion_push.py --check")
        return 3
    except NotionError as e:
        print(f"ERROR: Notion preflight failed: {e}")
        return 1

    state = notion_state(slug)
    main_id, main_url = state.get("main_page_id"), state.get("main_page_url")
    is_all = stages == ["all"]
    order = ALL_ORDER if is_all else stages

    if not main_id:
        rc = nb.stage_path(slug, "1", facts)
        if (is_all or allow_bootstrap or "1" in order) and os.path.exists(rc):
            try:
                main_id, main_url = bootstrap(c, slug, out)
            except (NotionError, nb.BodyError) as e:
                print(f"error: main page — {e}")
                print("ERROR: 1 item(s) failed")
                return 1
        else:
            for line in out:
                print(line)
            for st in order:
                print(f"skipped: {STAGE_NAMES[st]} — no main_page_id yet (run /research or /notion-sync first)")
            return 0

    elif not dry_run:
        try:
            page = c.call("GET", f"/pages/{main_id}")
            gone = page.get("in_trash") or page.get("archived")
        except NotionError as e:
            if e.status != 404:
                print(f"ERROR: could not read main page {main_id}: {e}")
                return 1
            gone = True
        if gone:
            print(f"ERROR: main page {main_id} is unreachable (deleted or moved?). Remove "
                  f"main_page_id, main_page_url and every *_page_id from analyses/{slug}/.notion "
                  "(restore it from Notion's trash instead if you want the old page back), "
                  "then re-run /notion-sync.")
            return 1

    for st in order:
        name = STAGE_NAMES[st]
        if not os.path.exists(nb.stage_path(slug, st, facts)):
            out.append(f"skipped: {name} — no local file")
            continue
        try:
            if st == "5":
                push_executive(c, slug, facts, main_id, out, notes)
            else:
                push_subpage(c, slug, st, facts, main_id, out)
        except (NotionError, nb.BodyError) as e:
            out.append(f"error: {name} — {e}")
            errors += 1

    for line in out + notes:
        print(line)
    if errors:
        print(f"ERROR: {errors} item(s) failed")
        return 1
    if main_url:
        print(f"Notion: {main_url}")
    return 0


def check():
    token, source = find_token()
    if not token:
        print(f"token: none (set NOTION_TOKEN or add Keychain service '{KEYCHAIN_SERVICE}')")
        print("MODE: mcp")
        return 3
    print(f"token: found ({source})")
    c = Client(token)
    try:
        me = c.call("GET", "/users/me")
        print(f"integration: {me.get('name') or me.get('id')}")
    except NotionError as e:
        print(f"ERROR: token rejected: {e}")
        return 1
    try:
        ds = c.call("GET", f"/data_sources/{DATA_SOURCE_ID}")
        title = "".join(t.get("plain_text", "") for t in ds.get("title", [])) or DATA_SOURCE_ID
        print(f"database: {title} (accessible)")
    except NotionError as e:
        print(f"ERROR: database not accessible ({e}). In Notion, open the Investments page "
              "→ ⋯ → Connections and add this integration.")
        return 1
    print("check: ok")
    return 0


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    allow_bootstrap = "--bootstrap" in args
    args = [a for a in args if a not in ("--dry-run", "--bootstrap")]
    if args == ["--check"]:
        return check()
    if len(args) < 2:
        print("ERROR: usage: notion_push.py <slug> <stage> [<stage> ...] | <slug> all | --check")
        return 1
    slug, stage_args = args[0], args[1:]
    if stage_args == ["all"]:
        stages = ["all"]
    else:
        try:
            stages = [nb.resolve_stage(s) for s in stage_args]
        except nb.BodyError as e:
            print(f"ERROR: {e}")
            return 1
    try:
        return run(slug, stages, dry_run, allow_bootstrap)
    except nb.BodyError as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
