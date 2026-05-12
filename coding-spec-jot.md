# Coding Spec — `jot` CLI quick-note tool

**Status:** reviewed
**Spec author:** tech-lead (date: 2026-05-13)
**Upstream:** decision-brief-jot.md (brainstorming session, 2026-05-13)
**Downstream:** coder

---

## 1. Outcome

`jot add "text"` appends a timestamped note to `~/.jot/notes.jsonl`. `jot list` prints all notes as `[HH:MM] text`, one per line. The tool is globally installable via `npm install -g`, ships zero runtime dependencies, and has full unit + integration test coverage.

---

## 2. Scope

**In scope:**

- `jot add "note text"` — append a note
- `jot list` — list all notes with timestamps
- `jot` (no args) — print usage
- Unknown command — print usage with non-zero exit
- JSON Lines storage at `~/.jot/notes.jsonl`
- Timestamps on every note (ISO 8601, displayed as `HH:MM`)
- Global npm install (`bin` in package.json → compiled JS)
- Unit tests for the store module
- Integration tests spawning the CLI process
- `JOT_HOME` env var to override storage directory (for testing)

**Out of scope (explicitly considered):**

- `jot delete`, `jot clear`, `jot edit` — add later if needed
- Search / filter — add later if needed
- Categories, tags, priorities — not a task manager
- Multiple named note files — single scratchpad only
- Config file / `jot config` — unnecessary for 2-command tool
- Piping / stdin input — `jot add "text"` covers the use case
- Daemon / background process — JSON file on disk survives terminal sessions
- Publishing to npm registry — user installs from local repo

---

## 3. Exploration notes

**Surface:** Greenfield project. Empty repository except for `decision-brief-jot.md`. No existing code, conventions, or tests. All conventions are established by this spec.

**Affected files:**
- `src/types.ts` — new
- `src/store.ts` — new
- `src/cli.ts` — new
- `tests/store.test.ts` — new
- `tests/cli.test.ts` — new
- `package.json` — new
- `tsconfig.json` — new

**Conventions established:**

| Domain | Convention | Source |
|---|---|---|
| Naming | camelCase functions, PascalCase types/interfaces | This spec |
| Errors | Explicit error handling — store functions throw on IO errors caught by CLI; CLI returns non-zero exit codes | This spec |
| Tests | vitest, colocated in `tests/` directory, named `*.test.ts` | This spec |
| Types | tsconfig strict mode, explicit return types on public functions | This spec |
| Imports | No path aliases (small project); relative imports | This spec |
| Logging | stdout for list output, stderr for errors/usage | This spec |
| Formatter / lint | None specified (user didn't request; can add later) | This spec |

**Types & contracts:**

```typescript
// src/types.ts

export interface Note {
  /** The note content — user-provided text. May be empty string. */
  text: string;
  /** ISO 8601 timestamp of when the note was created. */
  ts: string;
}
```

```typescript
// src/store.ts — public surface

/** Append a note to the JSONL file. Creates directory + file if needed. */
export async function addNote(text: string): Promise<void>;

/** Read all notes from the JSONL file in insertion order. Returns [] if no file. */
export async function listNotes(): Promise<Note[]>;

/** Resolve the store path. Honors JOT_HOME env var; defaults to ~/.jot/notes.jsonl. */
export function getStorePath(): string;
```

**Tests baseline:**

- Existing tests in scope: 0. This is greenfield.
- Baseline command: `npx vitest run` (will be added to package.json scripts).

**Risks observed:**

- Greenfield — no adjacent code to regress against.
- Concurrent terminal writes: JSON Lines append-only pattern eliminates corruption risk (from decision brief pre-mortem). Each `add` is one `fs.appendFile` — atomic for writes under the OS buffer size (default 4KB+).
- The only real risk is the `~/.jot/` directory not being writable, or the file growing unboundedly. Both are acceptable for a scratchpad tool — the user can `rm ~/.jot/notes.jsonl` to clear.

---

## 4. Design

### `src/types.ts` (new)

**Purpose:** Shared type definitions — the single source of truth for the Note shape.

**Public surface:**

```typescript
export interface Note {
  text: string;
  ts: string; // ISO 8601, e.g. "2026-05-13T14:23:00.000Z"
}
```

**Key internals:** None — pure type file.

---

### `src/store.ts` (new)

**Purpose:** Read and write the JSON Lines note file. All file I/O lives here; rest of the tool never touches `fs` directly.

**Public surface:**

```typescript
import { Note } from './types';

export async function addNote(text: string): Promise<void>;
export async function listNotes(): Promise<Note[]>;
export function getStorePath(): string;
```

**Key internals:**

- `getStorePath()` reads `process.env.JOT_HOME` — if set, uses `path.join(JOT_HOME, 'notes.jsonl')`. Otherwise defaults to `path.join(os.homedir(), '.jot', 'notes.jsonl')`. Does NOT create the directory (that's done in `addNote`).
- `addNote(text)`:
  1. Calls `getStorePath()`, creates directory via `fs.mkdir(dirname(path), { recursive: true })`.
  2. Builds a `Note` object: `{ text, ts: new Date().toISOString() }`.
  3. Appends `JSON.stringify(note) + '\n'` via `fs.appendFile(path, line, 'utf-8')`.
  4. Does NOT catch errors — lets them propagate to the CLI handler. The CLI catches and prints to stderr.
- `listNotes()`:
  1. Calls `getStorePath()`.
  2. Checks if file exists via `fs.access()`. If absent, returns `[]`.
  3. Reads entire file via `fs.readFile(path, 'utf-8')`.
  4. Splits on `'\n'`, filters empty lines (last line is often empty if file ends with newline).
  5. Parses each line as `JSON.parse(line)` and casts to `Note`. If a line fails to parse, it's skipped silently (resilience against partial/corrupt writes — though append-only makes this unlikely).
  6. Returns array of `Note` objects in file order.

**Code sketch (addNote):**

```typescript
export async function addNote(text: string): Promise<void> {
  const filePath = getStorePath();
  const dir = path.dirname(filePath);
  await fs.mkdir(dir, { recursive: true });

  const note: Note = {
    text,
    ts: new Date().toISOString(),
  };

  const line = JSON.stringify(note) + '\n';
  await fs.appendFile(filePath, line, 'utf-8');
}
```

**Code sketch (listNotes):**

```typescript
export async function listNotes(): Promise<Note[]> {
  const filePath = getStorePath();

  try {
    await fs.access(filePath);
  } catch {
    return [];
  }

  const content = await fs.readFile(filePath, 'utf-8');
  const lines = content.split('\n').filter(line => line.trim() !== '');

  return lines.reduce<Note[]>((notes, line) => {
    try {
      notes.push(JSON.parse(line) as Note);
    } catch {
      // Skip malformed lines silently
    }
    return notes;
  }, []);
}
```

---

### `src/cli.ts` (new)

**Purpose:** CLI entry point. Parses argv, dispatches to commands, formats output. Shebangs to `#!/usr/bin/env node`.

**Public surface:** No exports — this is the entry point. The file is executed directly.

**Key internals:**

```
argv[0] = node
argv[1] = path/to/cli.js
argv[2] = command (add | list | undefined)
argv[3] = argument (note text for 'add')
```

Dispatch logic:

```
if argv[2] === 'add':
  - Read note text from argv[3]. If missing, print "Usage: jot add <text>" to stderr, exit 1.
  - Call store.addNote(text).
  - On success: silent exit 0 (jot add is fire-and-forget).
  - On error: print error message to stderr, exit 1.

if argv[2] === 'list':
  - Call store.listNotes().
  - For each note, print "[HH:MM] text" to stdout.
    - Extract HH:MM from note.ts (ISO 8601 → new Date(note.ts) → local time → toLocaleTimeString or manual padStart).
  - If no notes, print "No notes yet." to stdout.
  - On error: print error message to stderr, exit 1.

else (unknown or no command):
  - Print usage to stderr:
    "Usage:
       jot add <text>    Add a note
       jot list          List all notes"
  - Exit 1 if unknown command; exit 0 if no command (just `jot`).
    - Let's be consistent: both exit 0 since it's informational usage display, not an error.
```

**Code sketch (cli.ts):**

```typescript
#!/usr/bin/env node

import { addNote, listNotes } from './store';

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const command = args[0];
  const text = args[1];

  switch (command) {
    case 'add': {
      if (!text) {
        console.error('Usage: jot add <text>');
        process.exit(1);
      }
      try {
        await addNote(text);
      } catch (err) {
        console.error('Error adding note:', (err as Error).message);
        process.exit(1);
      }
      break;
    }
    case 'list': {
      try {
        const notes = await listNotes();
        if (notes.length === 0) {
          console.log('No notes yet.');
        } else {
          for (const note of notes) {
            const d = new Date(note.ts);
            const hh = String(d.getHours()).padStart(2, '0');
            const mm = String(d.getMinutes()).padStart(2, '0');
            console.log(`[${hh}:${mm}] ${note.text}`);
          }
        }
      } catch (err) {
        console.error('Error listing notes:', (err as Error).message);
        process.exit(1);
      }
      break;
    }
    default: {
      console.error('Usage:');
      console.error('  jot add <text>    Add a note');
      console.error('  jot list          List all notes');
      process.exit(command ? 1 : 0);
    }
  }
}

main();
```

---

### `package.json` (new)

**Purpose:** Project metadata, scripts, binary declaration.

Key fields:

```json
{
  "name": "jot",
  "version": "1.0.0",
  "description": "Quick terminal notes",
  "bin": {
    "jot": "./dist/cli.js"
  },
  "scripts": {
    "build": "tsc",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "devDependencies": {
    "@types/node": "^20",
    "typescript": "^5",
    "vitest": "^1",
    "tsx": "^4"
  },
  "engines": {
    "node": ">=18"
  },
  "license": "MIT"
}
```

Note: `tsx` is a devDependency used for running integration tests against the TypeScript source directly (no pre-build needed for tests). Runtime has zero dependencies.

---

### `tsconfig.json` (new)

**Purpose:** TypeScript compilation config — strict mode, output to `dist/`.

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "moduleResolution": "node"
  },
  "include": ["src"],
  "exclude": ["tests", "dist"]
}
```

---

## 5. Test plan

| Test name | Level | File | Assertion |
|---|---|---|---|
| `adds_note_to_file` | unit | `tests/store.test.ts` | Add one note with text "hello", then listNotes returns exactly `[{ text: "hello", ts: <ISO string> }]`. |
| `lists_multiple_notes_in_order` | unit | `tests/store.test.ts` | Add "a", "b", "c". listNotes returns 3 notes in insertion order with matching text. |
| `lists_empty_array_when_no_file` | unit | `tests/store.test.ts` | On a clean temp dir (no prior notes file), listNotes returns `[]`. |
| `handles_unicode_text` | unit | `tests/store.test.ts` | Add text `"café 你好 🎉"`. listNotes returns the exact string including multi-byte chars and emoji. |
| `handles_empty_text` | unit | `tests/store.test.ts` | Add `""`. listNotes returns `[{ text: "", ts: <ISO> }]`. |
| `handles_newlines_in_text` | unit | `tests/store.test.ts` | Add text containing `\n`. Read back — text is preserved (JSON serialization escapes the newline so JSONL line integrity holds). |
| `getStorePath_respects_JOT_HOME` | unit | `tests/store.test.ts` | Set `process.env.JOT_HOME = '/tmp/test-jot'`; getStorePath returns `/tmp/test-jot/notes.jsonl`. Restore env after test. |
| `add_command_writes_note_and_exits_0` | integration | `tests/cli.test.ts` | Spawn `npx tsx src/cli.ts add "hello"` with `JOT_HOME=<temp>`. File at `<temp>/notes.jsonl` contains one JSON line with text "hello". Exit code 0. |
| `list_command_prints_formatted_notes` | integration | `tests/cli.test.ts` | Prepopulate `notes.jsonl` with two entries. Spawn `npx tsx src/cli.ts list` with `JOT_HOME=<temp>`. Stdout contains `[HH:MM] text` for both entries. Exit code 0. |
| `list_prints_placeholder_when_empty` | integration | `tests/cli.test.ts` | No file. Spawn `jot list`. Stdout contains "No notes yet." |
| `add_missing_text_shows_usage` | integration | `tests/cli.test.ts` | Spawn `jot add` (no text arg). Stderr contains "Usage". Exit code 1. |
| `unknown_command_shows_usage` | integration | `tests/cli.test.ts` | Spawn `jot unknown`. Stderr contains "Usage". Exit code 1. |
| `no_command_shows_usage_exits_0` | integration | `tests/cli.test.ts` | Spawn `jot` (no args). Stderr contains "Usage". Exit code 0. |

**Edge cases acknowledged (covered by named tests above):**

- Empty note text — covered by `handles_empty_text`
- Unicode / emoji — covered by `handles_unicode_text`
- Newlines in text — covered by `handles_newlines_in_text`
- Missing `~/.jot/` directory — handled by `mkdir` in `addNote`; `listNotes` returns `[]` if dir doesn't exist
- Corrupt JSON line — silently skipped in `listNotes` (tested implicitly by the type system; malformed lines fail `JSON.parse`, caught by try/catch)
- Concurrent writes — JSONL append-only handles this at the design level; not tested directly (would require OS-level process spawning with timing, over-scope for this tool)
- Very large note file — not tested (scratchpad use case; user manually clears); no pagination needed

**Mocks (and what's deliberately not mocked):**

- Mock: `process.env.JOT_HOME` — temporarily set during tests to point to a temp directory. Each test gets a fresh temp dir via `fs.mkdtemp` (unit) or `os.tmpdir` + random subdir (integration). Cleaned up in `afterEach`.
- Not mocked (deliberately): `fs` module — we use the real filesystem to verify actual JSONL behavior. Temp directories make this cheap and isolated.
- Not mocked (deliberately): `Date` — we assert that `note.ts` is an ISO string; exact timestamp values aren't asserted (would be flaky).

**TDD discipline:**

- [x] Tests specified test-first: store unit tests should be written and seen failing (file doesn't exist) before implementing `src/store.ts`.
- [x] Integration tests should fail (no binary, no module) before `src/cli.ts` exists.
- N/A — no bug fix, this is greenfield.

**Baseline:**

- Existing tests: 0. Greenfield.
- New tests added: +13 (7 unit + 6 integration).
- Coverage expectation: 100% of `src/` modules. No uncovered branches in store.ts or cli.ts.

---

## 6. Dependencies & ripples

**Dependencies:**

- Add: none (runtime). The tool ships zero runtime dependencies.
- Dev add: `typescript@^5`, `@types/node@^20`, `vitest@^1`, `tsx@^4` — standard TypeScript dev toolchain, MIT licensed, well-maintained.
- Remove: none.
- Bump: none.

**Affected callers:** N/A — greenfield, no existing callers.

**Deleted / renamed exports:** N/A — greenfield.

**Side effects:**

- New IO: Writes to `~/.jot/notes.jsonl` (or `$JOT_HOME/notes.jsonl`). ~/.jot/ directory created if absent.
- New logs: None (stdout for list output, stderr for errors/usage).
- New env vars / config: `JOT_HOME` — optional override for storage directory, defaults to `~/.jot`.
- New metrics: None.
- New background jobs: None.
- Schema / data layout changes: N/A — greenfield.

**Migration plan:** N/A — greenfield.

---

## 7. Reversibility

| Decision | Tag | Rationale | Kill criterion (🔴 only) |
|---|---|---|---|
| JSON Lines format (`Note { text, ts }`) | 🟢 | Adding fields is backward-compatible (new fields on new writes; old reads skip unknown). Removing fields would require ignoring them in read path — also fine. Format is append-only so corruption is near-impossible. | — |
| Storage path `~/.jot/` | 🟡 | Changing the path later orphanes existing notes. But users can `mv ~/.jot ~/.new-jot` and set `JOT_HOME`. Not a data loss risk. | — |
| Global install via npm `bin` field | 🟢 | Trivial to switch to a different distribution method (npx, shell wrapper, brew tap). The compiled JS is independent of npm after install. | — |
| Zero runtime dependencies | 🟢 | Adding a dependency later is a single `npm install`. Removing is `npm uninstall` + code change. | — |
| No CLI framework (manual argv parsing) | 🟢 | If commands grow beyond 3-4, add `commander` or `yargs`. Switching is a cli.ts rewrite — contained to one file. | — |
| Node >= 18 engine requirement | 🟡 | Bumping the engine later requires all users to upgrade Node. Backward-compatible unless we start using Node 20+ APIs. | — |

---

## 8. Smell-check

Smell-check: greenfield project — no existing codebase to fight, no conventions to match, no utilities to accidentally re-implement. The approach is deliberately minimal: one type file, one I/O module, one CLI entry point. Considered a single-file script (Option 2 from the decision brief) — rejected because the user explicitly chose the multi-file structure with tests. Considered using `commander` for CLI parsing — rejected because with exactly two commands, the dependency is heavier than the problem it solves; manual `switch` on `process.argv[2]` is 15 lines and fully transparent. No underlying-problem concern: the user's actual pain point (losing terminal notes) is directly addressed by persistent file storage. Sizing fits one slice perfectly — 3 source files, 2 test files, ~200 lines of implementation code.

---

## 9. Flagged assumptions

- ASSUMES: `os.homedir()` returns a writable directory on the user's machine. If wrong: `mkdir` in `addNote` will throw — CLI catches and prints the error. The user gets a clear failure message. No spec change needed; this is a runtime error the code already handles.
- ASSUMES: `fs.appendFile` with a single JSON line + `\n` is atomic on the target OS (true for writes under the OS buffer size, which a single note line is — well under 4KB). If wrong (e.g., exotic filesystem): partial writes could produce malformed lines, which `listNotes` skips silently. The design degrades gracefully. No spec change needed.
- ASSUMES: Node.js `>=18` is available on the user's machine. If wrong: `tsc` compilation will fail on ES2022 target. Downgrade `target` to `ES2020` and `lib` accordingly. Minor tsconfig change, coder can handle without spec update.

---

## 10. Handoff baton → coder

**Spec:** `coding-spec-jot.md` (this file, at repo root alongside `decision-brief-jot.md`).

**Outcome:** `jot add "text"` appends a timestamped note; `jot list` prints all notes as `[HH:MM] text`. Global install, zero runtime deps, full test coverage.

**First concrete action:** Initialize the project scaffold — create `package.json`, `tsconfig.json` per spec §4, run `npm install`, and confirm `npx tsc --noEmit` exits 0 (no source files yet, so it'll pass vacuously — first real check is after writing `src/types.ts`). Then write `src/types.ts` (the minimal file — one interface).

**Reconfirm before coding:**

- [ ] `npx tsc --version` shows TypeScript 5.x — verified as available.
- [ ] `node --version` shows >= 18 — verified as available.
- [ ] `os.homedir()` returns a path on this machine — quick `node -e "console.log(require('os').homedir())"` to confirm.
- [ ] No existing `~/.jot/` directory with important data — if it exists, warn but proceed (the tool only appends, won't overwrite).

**Acceptance signal:**

1. `npx vitest run` exits 0 (13 tests pass).
2. `npx tsc --noEmit` exits 0 (no type errors).
3. Manual smoke test:
   - `npm run build && node dist/cli.js add "test note"` — exits 0.
   - `node dist/cli.js list` — prints `[HH:MM] test note`.
   - `node dist/cli.js add ""` — exits 0 (empty text allowed).
   - `node dist/cli.js list` — prints both notes.
   - `rm ~/.jot/notes.jsonl` (clean up after manual test).
4. Global install test: `npm install -g .` from repo root, then `jot add "global test" && jot list` in a different directory — confirms binary resolution. Then `npm uninstall -g jot`.

**Stop conditions (pause and return to tech-lead):**

- An assumption above is wrong (e.g., Node < 18 — spec may need target/library adjustment).
- The test strategy reveals a gap — e.g., temp dir cleanup isn't reliable on this OS, needing a different isolation approach.
- Integration tests fail intermittently due to timing/spawn issues — needs test design adjustment.
- The user decides mid-implementation they want a feature from the "out of scope" list — pause and update spec.

**Commit hygiene:**

- Conventional commits: `feat:`, `test:`, `chore:`.
- Small commits — one per logical step:
  1. `chore: initialize project scaffold` — package.json, tsconfig.json, npm install
  2. `feat: add Note type`
  3. `feat: implement store module (addNote, listNotes)`
  4. `test: add store unit tests`
  5. `feat: implement CLI entry point`
  6. `test: add CLI integration tests`
  7. `chore: final adjustments and README` (if time)
- Write a progress note to `progress.md` after each commit.
- Hand the resulting branch to `project-git` for PR once acceptance signal is green.

---

## Revision history

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-05-13 | v1 | Initial draft | tech-lead |