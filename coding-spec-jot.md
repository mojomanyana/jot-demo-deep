# Coding Spec — jot v1: CLI quick-notes tool

**Status:** draft
**Spec author:** tech-lead (date: 2026-05-12)
**Upstream:** decision brief `/home/alavanja/prepos/jot-demo-deep/decision-brief-jot.md`
**Downstream:** coder

---

## 1. Outcome

A single-file Python CLI (`jot`) with three subcommands — `add`, `list`, `search` — that stores each note as an individual timestamped markdown file in `~/.jot/notes/`. Zero dependencies. Install by copying `jot.py` to PATH. WHEN the user runs `jot add "text"`, the system shall create a new markdown file in `~/.jot/notes/` with a sortable timestamp-slug filename and a `# heading` as its first line. WHEN the user runs `jot list`, the system shall display the 10 most recent notes with timestamps and headings. WHEN the user runs `jot search "query"`, the system shall shell out to `rg` over the notes directory.

---

## 2. Scope

**In scope:**

- `jot add "note text"` — positional args as note content
- `jot add` (no args) — reads note from stdin
- `jot list` — last 10 notes (filename + heading)
- `jot list -n N` — last N notes
- `jot search "query"` — wraps `rg "query" ~/.jot/notes/`
- `jot search --tag tagname` — wraps `rg '#tagname' ~/.jot/notes/`
- Auto-creates `~/.jot/notes/` and `~/.jot/attachments/` on first use
- Slug generation from note text (kebab-case, first ~5 words, max 60 chars)
- Timestamp embedded in filename (`YYYY-MM-DD-HHMMSS`)
- Help text via `--help` (provided by argparse)

**Out of scope (explicitly considered):**

- `jot edit` — deferred to v2 (edit via filesystem directly in v1)
- `jot delete` — deferred to v2 (delete via `rm` in v1)
- `jot attach <file>` — deferred to v1.1 (dir exists, command not yet wired)
- YAML frontmatter — deferred (decision: `# heading` as first line is sufficient)
- Config file, env vars for customization
- Piping `jot list` output to `fzf` (works naturally; no special support needed)
- Colored output, fancy formatting (plain text, scannable)
- Any dependency outside Python stdlib (not even `pytest`)
- pi extension integration (separate future workstream)

---

## 3. Exploration notes

**Surface:** Greenfield project. Python 3.12.3 available (`/usr/bin/python3`). Node v24.14.0 available but not used. `rg` 15.1.0 available (`/home/alavanja/.pi/agent/bin/rg`). Bash shell. No existing code, no build system, no config files, no git history. Empty repo except for the decision brief.

**Affected files:**
- `jot.py` — new (the entire application; single file)
- `tests/__init__.py` — new (empty, package marker)
- `tests/test_jot.py` — new (all tests)

**Conventions discovered (none — greenfield; conventions established by this spec):**

| Domain | Convention | Source |
|---|---|---|
| Naming | `snake_case` functions, `UPPER_CASE` constants | Python stdlib convention; this spec establishes |
| Errors | `print(msg, file=sys.stderr)` + `sys.exit(1)` for user/system errors | Standard CLI convention |
| Tests | `unittest` (stdlib), `tests/` directory, `test_*.py` naming | This spec establishes |
| Types | No type annotations in v1 (keeps it simple; add later if desired) | Deliberate omission for minimalism |
| Imports | Stdlib only: `argparse`, `pathlib`, `subprocess`, `datetime`, `re`, `sys`, `os`, `textwrap`, `shutil` | Zero-dependency constraint |
| CLI | `argparse` with subcommands (`add`, `list`, `search`) | Stdlib pattern |
| Docstrings | One-line module docstring; no per-function docstrings (code is short enough) | Minimalism |

**Types & contracts:**

```python
# jot.py — no types, but the data contract:

# File path pattern:
#   ~/.jot/notes/YYYY-MM-DD-HHMMSS-slug.md
#   ~/.jot/attachments/  (empty dir in v1)

# File format:
#   # <heading — first line of user input>
#
#   <body — remaining lines, if any>

# list output format (tab-separated for alignment):
#   2026-05-12 23:05:00    docker-networking-issue
#   2026-05-12 23:00:00    remember thing

# search output: raw rg output, forwarded to stdout/sterr
```

**Tests baseline:** No tests exist (greenfield). Baseline is `python3 -m unittest discover tests` with zero tests.

**Risks observed:**
- `rg` might not be installed — `jot search` must detect and give a clear error message
- Timestamp collisions (sub-second race) — edge case, handled by append-counter if it occurs
- PATH install is manual — user must `cp jot.py /usr/local/bin/jot` or `ln -s`; document in `--help` or README
- Single-file might grow unwieldy — acceptable for v1; extract to module if v2 needs it

---

## 4. Design

### `jot.py` (new)

**Purpose:** The entire CLI application. Single file, executable via `python3 jot.py` or (after install) `jot`.

**Public surface:**

The file is the public surface. Entry point: `main()` function. Three subcommands via argparse, each dispatching to a private function.

```python
#!/usr/bin/env python3
"""jot — quick notes from the command line. Store notes in ~/.jot/notes/."""

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

JOT_DIR = Path.home() / ".jot"
NOTES_DIR = JOT_DIR / "notes"
ATTACHMENTS_DIR = JOT_DIR / "attachments"
MAX_SLUG_LENGTH = 60

# --- helpers ---

def ensure_dirs():
    ...

def generate_slug(text: str) -> str:
    """'remember this thing' → 'remember-this-thing'"""
    ...

def generate_filename(text: str, ts: datetime.datetime) -> str:
    """→ '2026-05-12-230500-remember-this-thing.md'"""
    ...

def extract_heading(filepath: Path) -> str:
    """Read first # heading from a markdown file."""
    ...

def format_list_entry(filepath: Path) -> str:
    """→ '2026-05-12 23:05:00    remember-this-thing'"""
    ...

# --- commands ---

def cmd_add(args):
    """If args.text, use it; otherwise read stdin."""
    ...

def cmd_list(args):
    """List NOTES_DIR/*.md sorted reverse, first args.count entries."""
    ...

def cmd_search(args):
    """Shell out to rg. If --tag, search '#tagname'. Otherwise pass query through."""
    ...

# --- entry point ---

def build_parser() -> argparse.ArgumentParser:
    ...

def main():
    ...
```

**Key internals:**

- **`ensure_dirs()`** — creates `NOTES_DIR` and `ATTACHMENTS_DIR` with `parents=True, exist_ok=True`. Called at the top of every command. Idempotent.
- **`generate_slug()`** — takes first ~5 words, lowercases, strips non-alphanumeric (keeps hyphens), collapses multiple hyphens into one, strips leading/trailing hyphens, truncates to `MAX_SLUG_LENGTH`. If text is empty, slug is `note`.
- **`generate_filename()`** — `f"{ts:%Y-%m-%d-%H%M%S}-{slug}.md"`. If filename collision (unlikely at second precision), append `-2`, `-3`, etc. until unique.
- **`extract_heading()`** — opens file, reads lines until finds one starting with `# `, returns it without the `# ` prefix (stripped). Returns first non-empty line if no `# ` heading found.
- **`format_list_entry()`** — parses timestamp from filename prefix, calls `extract_heading()`, formats as `YYYY-MM-DD HH:MM:SS    heading`. Tab between timestamp and heading for easy column alignment.
- **`cmd_add()`** — if `args.text` is non-empty, use it as content (join with space if multiple positional args). Otherwise, read `sys.stdin.read()`. Split content on first newline: first line → heading, rest → body. Write `# heading\n\nbody` (omit `\n\nbody` if no body). Print created file path.
- **`cmd_list()`** — `sorted(NOTES_DIR.glob("*.md"), reverse=True)[:args.count]`. For each, print `format_list_entry()`.
- **`cmd_search()`** — build `rg` args. If `args.tag`: `['rg', f'#{args.tag}', str(NOTES_DIR)]`. Otherwise: `['rg', args.query, str(NOTES_DIR)]`. Also pass through `args.rg_args` if provided (to allow `-i`, `-C`, etc.). Use `subprocess.run()`. If `rg` not found (`FileNotFoundError`), print clear error and exit 1. Forward `rg`'s exit code.

**Parser structure:**

```
jot
├── add [text ...]          # positional, nargs='*'
├── list
│   └── -n, --count N       # default 10
└── search
    ├── query               # positional
    ├── --tag TAG           # mutually exclusive with positional query
    └── --rg-args ...       # passthrough args to rg (nargs='*' or remaining)
```

Wait — `search` needs either `query` OR `--tag`, not both. Cleanest design: make `query` positional but `nargs='?'`, and `--tag` an optional flag. If both given, `--tag` wins. If neither, error.

Actually, even simpler for v1: `jot search "query"` and `jot search --tag tagname`. No `--rg-args` passthrough in v1 — the user can run `rg` directly if they need flags. `jot search` is the 80% case.

```python
# Parser sketch — final:

parser = argparse.ArgumentParser(description="jot — quick notes from the CLI")
subs = parser.add_subparsers(dest="command")

add_p = subs.add_parser("add", help="Add a new note")
add_p.add_argument("text", nargs="*", help="Note text (reads from stdin if omitted)")
add_p.set_defaults(func=cmd_add)

list_p = subs.add_parser("list", help="List recent notes")
list_p.add_argument("-n", "--count", type=int, default=10, help="Number of notes to show (default: 10)")
list_p.set_defaults(func=cmd_list)

search_p = subs.add_parser("search", help="Search notes with ripgrep")
search_p.add_argument("query", nargs="?", default=None, help="Search query")
search_p.add_argument("--tag", "-t", default=None, help="Search for #tag")
search_p.set_defaults(func=cmd_search)
```

**Code sketch — `cmd_add`:**

```python
def cmd_add(args):
    ensure_dirs()
    if args.text:
        content = " ".join(args.text)
    else:
        if sys.stdin.isatty():
            print("Error: no text provided and stdin is a terminal.", file=sys.stderr)
            print("Usage: jot add 'note text'  OR  echo 'text' | jot add", file=sys.stderr)
            sys.exit(1)
        content = sys.stdin.read().strip()
    
    if not content:
        print("Error: note text cannot be empty.", file=sys.stderr)
        sys.exit(1)
    
    lines = content.split("\n", 1)
    heading = lines[0].strip()
    body = lines[1].strip() if len(lines) > 1 else ""
    
    ts = datetime.datetime.now()
    filename = generate_filename(heading, ts)
    filepath = NOTES_DIR / filename
    
    with open(filepath, "w") as f:
        f.write(f"# {heading}\n")
        if body:
            f.write(f"\n{body}\n")
    
    print(str(filepath))
```

**Code sketch — `cmd_list`:**

```python
def cmd_list(args):
    ensure_dirs()
    files = sorted(NOTES_DIR.glob("*.md"), reverse=True)
    for fp in files[:args.count]:
        print(format_list_entry(fp))
    if not files:
        print("No notes yet. Add one with: jot add 'your note'")
```

**Code sketch — `cmd_search`:**

```python
def cmd_search(args):
    ensure_dirs()
    if args.tag:
        pattern = f"#{args.tag}"
    elif args.query:
        pattern = args.query
    else:
        print("Error: provide a search query or --tag.", file=sys.stderr)
        sys.exit(1)
    
    try:
        subprocess.run(["rg", pattern, str(NOTES_DIR)])
    except FileNotFoundError:
        print("Error: 'rg' (ripgrep) not found. Install it: https://github.com/BurntSushi/ripgrep", file=sys.stderr)
        sys.exit(1)
```

---

## 5. Test plan

Tests use `unittest` (stdlib). Test isolation via `tempfile.TemporaryDirectory` for filesystem tests — no global `~/.jot/` pollution. The `JOT_DIR` / `NOTES_DIR` / `ATTACHMENTS_DIR` constants are monkeypatched in test setup to point at a temp directory.

| Test name | Level | File | Assertion |
|---|---|---|---|
| `test_ensure_dirs_creates_directories` | unit | `tests/test_jot.py` | After call with temp path, both `notes/` and `attachments/` subdirs exist |
| `test_ensure_dirs_idempotent` | unit | same | Calling twice doesn't raise; dirs still exist |
| `test_generate_slug_basic` | unit | same | `"remember this thing"` → `"remember-this-thing"` |
| `test_generate_slug_truncates` | unit | same | Very long text → slug ≤ 60 chars |
| `test_generate_slug_strips_special_chars` | unit | same | `"hello! @world #123"` → `"hello-world-123"` |
| `test_generate_slug_empty_fallback` | unit | same | `""` → `"note"` |
| `test_generate_slug_unicode` | unit | same | `"café résumé"` → `"café-résumé"` (Python handles unicode) |
| `test_generate_filename_format` | unit | same | Given heading `"hi"` and datetime(2026,5,12,23,5,0) → `"2026-05-12-230500-hi.md"` |
| `test_generate_filename_collision` | unit | same | When file exists, append `-2` before `.md`; check until unique |
| `test_extract_heading_from_file` | unit | same | File with `# Hello\n\nworld` → `"Hello"` |
| `test_extract_heading_no_heading_fallback` | unit | same | File with no `#` line → first non-empty line |
| `test_format_list_entry` | unit | same | File named `2026-05-12-230500-hi.md` with heading `"hi"` → `"2026-05-12 23:05:00    hi"` |
| `test_add_creates_note_file` | integration | same | `cmd_add` with text `"hello world"` → file exists at expected path with `# hello world` content |
| `test_add_from_stdin` | integration | same | Pipe `"stdin note"` via `sys.stdin` → file created with heading `"stdin note"` |
| `test_add_multiline` | integration | same | `"line1\nline2\nline3"` → heading `"line1"`, body `"line2\nline3"` |
| `test_add_empty_errors` | unit | same | `cmd_add` with empty text → `SystemExit(1)` |
| `test_add_stdin_tty_errors` | unit | same | `sys.stdin.isatty()` returns True, no text → `SystemExit(1)` |
| `test_list_shows_recent` | integration | same | Pre-create 3 note files → `cmd_list` output has 3 lines, newest first |
| `test_list_respects_count` | integration | same | Pre-create 20 notes, `args.count=5` → output has 5 lines |
| `test_list_empty_shows_message` | integration | same | Empty notes dir → output contains "No notes yet" |
| `test_search_calls_rg` | unit | same | Mock `subprocess.run`; assert called with `["rg", "query", str(NOTES_DIR)]` |
| `test_search_tag_calls_rg` | unit | same | `args.tag="meeting"` → assert called with `["rg", "#meeting", str(NOTES_DIR)]` |
| `test_search_no_rg_errors` | unit | same | Mock `subprocess.run` to raise `FileNotFoundError` → `SystemExit(1)` |
| `test_search_no_query_errors` | unit | same | Neither `query` nor `tag` given → `SystemExit(1)` |
| `test_full_add_then_list` | integration | same | Add note via `cmd_add`, then `cmd_list` → note appears in output |

**Edge cases acknowledged (covered by named tests above):**

- Empty notes directory (`test_list_empty`)
- Empty input (`test_add_empty`)
- Unicode in content (`test_generate_slug_unicode`, Python handles unicode natively in files)
- Filename collision (`test_generate_filename_collision`)
- Multi-line input from stdin (`test_add_multiline`)
- `rg` not installed (`test_search_no_rg`)

**Mocks (and what's deliberately not mocked):**

- Mock: `subprocess.run` in search tests — we're testing arg construction, not `rg` itself
- Mock: `sys.stdin` in add-stdin tests — we control the input stream
- Not mocked (deliberately): filesystem operations — tests use `tempfile.TemporaryDirectory` which is fast and real; mocking `open()` / `Path` would test the mock, not the behavior

**TDD discipline:**

- [x] Tests for pure helpers (`generate_slug`, `generate_filename`, `extract_heading`, `format_list_entry`) are specified to be written test-first — they're pure I/O-free functions.
- [ ] For bug fixes: not applicable (initial implementation).

**Baseline:**

- No existing tests.
- New tests added: +26.
- Coverage expectation: all functions in `jot.py` exercised; command entry points covered via integration tests with temp dirs.

---

## 6. Dependencies & ripples

**Dependencies:**

- Add: **none** — Python stdlib only.
- Remove: n/a.
- Bump: n/a.

**Affected callers:** n/a (greenfield; no existing code to break).

**Deleted / renamed exports:** none.

**Side effects:**

- New IO: reads/writes to `~/.jot/notes/*.md` (filesystem); reads stdin in add mode; shells out to `rg` in search mode.
- New logs: none (prints to stdout for results, stderr for errors — standard CLI).
- New env vars / config: none. `JOT_DIR` is hardcoded to `~/.jot/`.
- New metrics: none.
- New background jobs: none.
- Schema / data layout changes: n/a (initial creation).

**Migration plan:** n/a (initial implementation; no existing data).

---

## 7. Reversibility

| Decision | Tag | Rationale | Kill criterion (🔴 only) |
|---|---|---|---|
| Python 3 as implementation language | 🟡 | Zero-deps goal met; changing language later means rewrite, but no data migration | — |
| Single file `jot.py` architecture | 🟢 | Extract to package later is trivial; import paths change but no behavior change | — |
| `~/.jot/notes/` + `~/.jot/attachments/` layout | 🟢 | Flatten to single dir later is a one-line `mv`; migrate to DB is a migration script | — |
| `YYYY-MM-DD-HHMMSS-slug.md` filename format | 🟡 | Renaming files later requires a migration script; data is preserved in content | — |
| `# heading` as first line (no YAML frontmatter) | 🟢 | Adding YAML later is backward-compatible — new files get YAML; old files don't break | — |
| `rg` as search backend | 🟢 | Swap to `grep`, `ag`, or custom search later; just change the `subprocess.run` call | — |
| Tab-separated list output (not JSON) | 🟢 | Change output format later — no data migration needed | — |
| No `jot edit` / `jot delete` in v1 | 🟢 | Add commands later — additive, no reversal cost | — |

---

## 8. Smell-check

Approach: a clean single-file Python CLI with no external dependencies matches the "minimal personal tool" constraint perfectly — no `pip install`, no `package.json`, no build step. Smaller alternative considered (shell alias/function) — rejected in the decision brief because it couldn't handle the heterogeneous content or attachments. No duplicate utility exists (greenfield). Underlying problem (capture friction) is addressed directly: `jot add "text"` is ~15 keystrokes, sub-second execution, no app to open, no structure to fight. Sizing fits one slice well — ~200 lines of Python, one test file, no ripples into existing code. Follow-up surfaced: if this grows, extract helpers into a `jot/` package and add `pyproject.toml`; if search gets painful, add an SQLite index that references file paths (per the pre-mortem fallback plan).

---

## 9. Flagged assumptions

- ASSUMES: `rg` is installed and in PATH. If wrong: `jot search` prints a clear error; user must install ripgrep.
- ASSUMES: User will install `jot.py` by copying/symlinking to a directory in PATH (e.g., `cp jot.py /usr/local/bin/jot`). If wrong: they run `python3 jot.py` instead — works identically.
- ASSUMES: `~/.jot/` is writable and has reasonable disk space. If wrong: Python will raise `OSError` / `PermissionError` on file write; catch and surface as user error in the coder's implementation (this is a standard Python filesystem error, no special handling needed in v1).
- ASSUMES: Notes are short enough that reading the first line for heading extraction is fast (no multi-megabyte markdown files). If wrong: `cmd_list` slows down. Coder should use `open()` and read only first few lines (not whole file).
- ASSUMES: Python 3.9+ available (uses `argparse` subparsers with `set_defaults(func=...)` pattern, which works in all modern Pythons). Confirmed: user has Python 3.12.3.

---

## 10. Handoff baton → coder

**Spec:** `/home/alavanja/prepos/jot-demo-deep/coding-spec-jot.md` (this document)

**Outcome (one-liner):** A zero-dependency Python CLI at `jot.py` with `add`, `list`, `search` subcommands storing notes as markdown files in `~/.jot/notes/`.

**First concrete action:** Create `jot.py` with the shebang, module docstring, imports, and constant definitions from §4. Confirm the file runs (`python3 jot.py --help` exits 0). Then add the helper functions (`ensure_dirs`, `generate_slug`, `generate_filename`, `extract_heading`, `format_list_entry`) as the first commit.

**Reconfirm before coding:**

- [ ] `rg` 15.1.0 is at `/home/alavanja/.pi/agent/bin/rg` — verify with `which rg`. If not found, still implement; search will error gracefully at runtime.
- [ ] `python3` is 3.12.3 at `/usr/bin/python3` — verify with `python3 --version`. The spec targets 3.9+.
- [ ] `tests/` directory doesn't exist yet — create it with `__init__.py`.

**Acceptance signal:**

1. `python3 -m unittest discover tests` exits 0 (all 26 tests pass).
2. `python3 jot.py --help` exits 0 and shows usage.
3. `python3 jot.py add "test note from spec"` creates `~/.jot/notes/<timestamp>-test-note-from-spec.md` with `# test note from spec` inside.
4. `python3 jot.py list` shows the note just added.
5. `python3 jot.py search "test note"` finds it (via rg).
6. `python3 jot.py search --tag test` finds it (if you add `#test` to the note — or test with a known tag).

**Stop conditions (pause and return to tech-lead):**

- Any flagged assumption above is wrong and affects the design (e.g., a Python version <3.9).
- The test plan reveals a behavior gap requiring more than a one-line addition.
- A convention conflict surfaces (unlikely for greenfield, but if the user has preferences).
- `unittest` discovery can't find tests — suggests packaging issue that needs resolution.

**Commit hygiene:**

- Conventional commits: `feat(jot): ...`, `test(jot): ...`
- Small commits, one per logical step:
  1. `feat(jot): scaffold jot.py with imports and constants`
  2. `feat(jot): add helper functions (ensure_dirs, generate_slug, generate_filename, extract_heading, format_list_entry)`
  3. `test(jot): add unit tests for all helpers`
  4. `feat(jot): add 'jot add' command`
  5. `test(jot): add integration tests for jot add`
  6. `feat(jot): add 'jot list' command`
  7. `test(jot): add tests for jot list`
  8. `feat(jot): add 'jot search' command`
  9. `test(jot): add tests for jot search`
  10. `feat(jot): add main entry point and argparse wiring`
- Write a progress note to `progress.md` after each commit.
- Hand the resulting branch to `project-git` for PR once acceptance signal is green.

---

## Revision history

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-05-12 | v1 | Initial draft — jot v1 CLI spec | tech-lead |