# Decision Brief: jot — Quick-note CLI tool

**Date:** 2026-05-13
**Session mode:** A (Problem exploration)
**Status:** Decided

---

## 1. The question, reframed

**What we set out to ask:**
> "I want to build a CLI tool for quick notes. Something like `jot add 'remember thing'` and `jot list`. Simple, TypeScript, quality code."

**What we actually decided we were asking:**
> "How do I build a globally-installable CLI that captures quick todo notes so they survive terminal sessions, with well-crafted TypeScript code as the primary deliverable quality?"

**Why the reframe matters:**
The original framing was already close — the main addition was surfacing "global install" and "survives terminal sessions" as hard constraints, and making explicit that "quality" means code quality (structure, types, tests), not persistence guarantees.

---

## 2. Constraints and assumptions

**Hard constraints:**
- Global install — invocable as `jot add "..."` and `jot list` from any directory
- Survives terminal sessions — notes aren't lost when the terminal closes
- TypeScript with well-structured code
- Core commands: `add` and `list`

**Soft constraints:**
- Single machine, single user
- Minimal dependencies
- Fast to type — friction must be negligible or the tool won't be used

**Explicit non-constraints:**
- Long-term persistence — notes are disposable scratchpad items, no backup/sync needed
- Multi-user, multi-machine, cloud sync
- Rich formatting, search, categories, tags

**Assumptions made:**
- Single-user, single-terminal-at-a-time concurrency is acceptable — verified (user said "just for you")
- JSON file in home directory is acceptable for storage — unverified; worth confirming during implementation
- Node.js and npm are available globally on the target machine — verified (user is in a Node/TS dev environment)

---

## 3. Options considered

| # | Option | One-line description | Pros | Cons | Reversibility |
|---|--------|----------------------|------|------|---------------|
| 1 | Shell aliases | `alias jot-add='echo "..." >> ~/.jot.txt'` | Zero code, zero deps, already global | No structure, no types, no quality — undermines the goal | Two-way |
| 2 | Single-file script | One `index.ts`, JSON file, `process.argv` parsing | Fast to build, minimal structure | No tests, harder to extend, lower code quality | Two-way |
| 3 | Multi-file TS project with tests | Full project: `src/cli.ts`, `src/store.ts`, `src/commands.ts`, tests | Code quality first, typed, tested, maintainable | More upfront time, risk of over-engineering for scope | Two-way |
| 4 | In-memory daemon | Background process, Unix socket/HTTP | Survives terminal sessions, zero files | Over-engineered, daemon management complexity | Two-way |
| 5 | SQLite store | Option 3 but with SQLite backend | Structured queries, timestamps built-in | Native dependency, database overhead for a scratchpad | Two-way |
| 6 (do nothing) | Status quo | Keep typing notes into terminal prompts and losing them | Zero effort | Still losing notes | n/a |

**Options the user had already rejected before the session, and why:**
- Long-term persistence / database-heavy solutions — implicitly rejected by "no long term persistence"
- Complex feature sets (sync, categories, multi-user) — rejected by "simple"

**Steel-man of the strongest rejected option:**
> Option 2 (single-file script) is the pragmatic choice: you get a working tool in 30 minutes, it's globally installable, it does the job, and you haven't spent a day setting up a project scaffold for what's fundamentally a JSON append. The risk of over-engineering is real — the best tool is the one that exists.

---

## 4. Pre-mortem on the chosen path

> _Imagine it's 6 months later. `jot` sits unused in `/usr/local/lib/node_modules`. The story is:_

**Top failure modes:**

1. **JSON file corruption from concurrent writes** — Two terminal tabs write simultaneously, the JSON array structure breaks, notes are lost.
   - Likelihood: Medium × Severity: High
   - Mitigation: Use JSON Lines (append-only, one JSON object per line) instead of a single JSON array. Each write is one atomic `fs.appendFile` call. No parsing required for reads — read lines, parse each.

2. **Over-engineering kills momentum** — Two days spent on project scaffold, testing infrastructure, linting config before a single note is stored.
   - Likelihood: Medium × Severity: Medium
   - Mitigation: Build the working MVP (add + list against a temp file) in one sitting first. Add tests, polish, and structure on the second pass. Ship before you perfect.

3. **nvm Node version switch nukes the global install** — `npm install -g` is per-Node-version with nvm. Switching versions loses the binary.
   - Likelihood: Medium × Severity: Low (reinstall is one command)
   - Mitigation: Document the install command in the README. Alternatively, use a local clone + `npm link`, or install to a stable system Node outside nvm.

4. **The habit doesn't form** — `echo >> file` is just as fast and already muscle memory.
   - Likelihood: Low × Severity: Medium (the tool worked but isn't used)
   - Mitigation: `jot add "milk"` is actually fewer characters than `echo "milk" >> ~/notes` and you don't need to remember the file path. This might not be a real problem.

---

## 5. Decision

**The decision:** Build a multi-file TypeScript CLI project with JSON Lines storage in `~/.jot/notes.jsonl`, core commands `add` and `list`, with tests, following a quality-first code structure.

**Decision rule used:** Best fit to constraints — Options 1 and 2 fail the "code quality/types" constraint, Options 4 and 5 fail "simple," and Option 3 is the one choice that satisfies all hard constraints.

**Why this option:**
Option 3 is the only option that delivers on the stated priority (code quality, types, tests) without introducing unnecessary infrastructure (daemon, database). The JSON Lines storage pattern (one JSON object per line, append-only) eliminates the concurrent-write corruption risk identified in the pre-mortem while keeping the storage dead simple — a file you can `cat` and read with your eyes.

**What we're explicitly trading away:**
> We're trading development speed and minimalism for code quality and testability. A single-file script would be working sooner; this approach buys a codebase you'd be proud to reference or extend later.

---

## 6. Reversibility

**Classification:** Two-way door

**How to reverse:**
- `npm uninstall -g jot` to remove the binary
- Delete `~/.jot/` to remove all notes
- Total cost to reverse: under 10 seconds, zero data contract breakage

**Trigger for reversal:** The tool sits unused for 2+ weeks, or the install/friction story is annoying enough that it's not worth keeping.

---

## 7. Open questions

Things deliberately not decided in this session:

- **Should there be a `delete` or `clear` command?** — Ship `add` and `list` first. Add `clear` if the JSONL file gets noisy. `delete` by index is a nice-to-have that can come later.
- **Should notes have timestamps?** — JSONL makes it trivial to add `{ text, ts }` per entry. Worth doing from the start for `list` ordering, but it's a one-field addition so it's a low-cost decision.
- **Exact project structure?** — Defer to `tech-lead` skill which will design the file layout, interfaces, and test strategy.

---

## 8. Handoff

**The next step is owned by:** `tech-lead` skill

Hand off to `tech-lead` skill. Key inputs:
- Decision: Multi-file TypeScript CLI, JSON Lines storage at `~/.jot/notes.jsonl`
- Acceptance criteria: `jot add "text"` (global), `jot list` (global), survives terminal sessions, typed, tested
- Key design decision from pre-mortem: Use JSON Lines (append-only) instead of a JSON array to prevent concurrent-write corruption
- Constraints: global install, minimal deps, simple interface

---

## 9. Session notes

- The user's actual pain point is typing notes into terminal prompts that vanish — not a missing note-taking system per se, but the gap between "terminal thought" and "captured."
- "Quality" was clarified to mean code quality (structure, types, tests), not data durability.
- JSON Lines was surfaced as the key architectural insight during the pre-mortem — it solves the biggest risk (corruption) with no added complexity.

---

## 10. Self-check

- [x] At least 3 options were considered (6, including "do nothing" and the boring option).
- [x] The chosen option survived a real pre-mortem (4 failure modes identified, #1 has a concrete mitigation).
- [x] Reversibility is named (two-way door, trivial to reverse).
- [x] The trade-off is named ("speed/minimalism for code quality/testability").
- [x] The handoff points to a specific next step (`tech-lead` skill, with concrete inputs).
- [x] The user agreed with the reframing (chose Option 3 from the roster).