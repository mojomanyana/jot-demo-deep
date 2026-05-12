# Decision Brief: jot — CLI quick-notes tool

**Date:** 2026-05-12
**Session mode:** A — Problem Exploration (full Diamond)
**Status:** Decided

---

## 1. The question, reframed

**What we set out to ask:**
> "I want to build a CLI tool for quick notes. Something like `jot add 'remember thing'` and `jot list`. Help me think through the design before I commit to anything."

**What we actually decided we were asking:**
> "I lose transient thoughts because the cost of capturing them exceeds my willingness to pay in the moment. When I do capture, they scatter across tools and surfaces. How do I build a single, instant, minimal capture point that accepts anything I throw at it and gets out of my way?"

**Why the reframe matters:**
The original framing jumped to a solution (`jot add` / `jot list`) and surface-level implementation questions (storage, search). The real problem is *capture friction* — the activation energy required to dump a thought before it evaporates. The tool exists to make that number as close to zero as possible, not to be a note-taking app.

---

## 2. Constraints and assumptions

**Hard constraints:**
- CLI-first. Must work from any terminal, with minimal keystrokes.
- Heterogeneous capture: text, URLs, command snippets, filenames, file attachments — not all the same shape.
- Standalone CLI now; must be usable as a pi extension later.
- Personal tool — single user, single machine. No sync, no multi-tenancy, no auth.
- Minimal. Not a product. Not a knowledge base. Not a "second brain."

**Soft constraints:**
- Capture should feel instant — sub-second, no friction loops.
- Retrieval should be dead-simple. No query language, no schema to learn.
- Each note should be independently addressable (edit, delete, share one note without touching others).

**Explicit non-constraints (we chose not to be limited by):**
- **No need to build search infrastructure upfront.** `rg`/`grep` is sufficient until it demonstrably isn't. Lifted because over-indexing on search would compromise minimalism.
- **No cross-platform portability burden.** Runs where the user runs (Linux/macOS). No Windows support needed.
- **No structured schema enforcement.** Notes are freeform. Conventions can emerge, but the tool doesn't enforce them.

**Assumptions we made:**
- `rg` (ripgrep) is available and sufficient for retrieval on a personal scale (hundreds to low thousands of notes) — *unverified, will be discovered in practice.*
- The file-per-note model scales acceptably for personal use — *unverified; pre-mortem addresses the failure mode.*
- User is comfortable with the filesystem as a database — *verified* (CLI-native user).

---

## 3. Options considered

| # | Option | One-line | Pros | Cons | Reversibility |
|---|--------|----------|------|------|---------------|
| A | Shell alias | `alias jot='echo "$(date) $*" >> ~/jot.txt'` | Zero dependencies, done in seconds | No search, no attachments, no structure | Two-way |
| B | Single flat text file | One `notes.txt`, thin CLI wrapper | Dead simple, grep-able, single file | No metadata, no per-note addressing | Two-way |
| C | JSONL with tags | One `notes.jsonl`, `jq`-able, substring search | Structured, scriptable, single file, tags built in | Not per-note addressable, attachments as dead strings, git diffs are line-level in a giant file | Two-way |
| **D** | **Directory of markdown files** | **Each note is `~/.jot/YYYY-MM-DD-HHMMSS-slug.md`** | **Git-friendly, per-note addressing, attachments as siblings, filesystem-is-the-DB, rg search** | **Directory explosion at scale, no ranked search, inconsistent formatting without discipline, "what was the slug?" retrieval friction** | **Two-way** |
| E | SQLite + FTS5 | Single `.db`, ranked full-text search | Real search, fast, metadata-rich | Not grep-able, schema to maintain, more code, less Unix-native | Two-way |
| F | Pipe-native, stdin-first | `echo "thought" \| jot`, output designed for piping | Maximally Unix-composable | Attachments awkward, no per-note file identity | Two-way |

**Options the user had already rejected before the session:**
- Todo apps / GUI note apps — too structured, imposed a task/project model that fights "just remember this."
- Scattered ad-hoc capture (browser tabs, Slack DMs to self, random text files) — this is the status quo that's failing.

**Steel-man of the strongest rejected option (Option C — JSONL):**
> A single JSONL file is easier to back up, easier to pipe through `jq` for filtering, and avoids directory explosion entirely. A pi extension reads one file. The attachment problem (path strings divorced from notes) could be solved by copying files into a managed directory and referencing them by hash or UUID. The git-diff concern is real but manageable if notes are mostly appended. If Option D fails on *scale* or *search*, Option C is the first fallback — not E (SQLite), because C keeps the Unix-philosophy simplicity while adding just enough structure.

---

## 4. Pre-mortem on the chosen path

> *Imagine it's 12 months later. Option D failed. The story is:*

You have ~1,500 notes in a flat directory. `rg` searches take a noticeable beat. You search for "docker networking issue" and get 40 results — no ranking, no fuzzy matching — and the one you want is result #17. You misspelled "database" as "databse" and got zero results. You've stopped trusting retrieval, so you don't bother searching anymore. Notes accumulate but you never revisit them. The tool became a write-only sink.

Meanwhile, `~/.jot/` is cluttered with 200 `.png` screenshots and `.pdf` attachments mixed among `.md` files with no separation. Half your notes have YAML frontmatter, half don't. Some use `#tag` in the body, some use frontmatter `tags: [...]`. You can't remember which convention a given note uses, so filtering is unreliable. You drift back to todo apps for anything you actually need to find later.

**Top failure modes:**

| # | Mode | Likelihood × Severity | Mitigation or acceptance |
|---|------|----------------------|--------------------------|
| 1 | **Directory scalability** — `rg` becomes slow with 1,000+ files; no ranked/fuzzy search | Medium × Medium | Acceptance for now. If it bites, migrate to Option C or add a lightweight SQLite search index that references file paths. Two-way door. |
| 2 | **Inconsistent formatting** — notes diverge without enforced conventions | High × Low | Mitigation: establish a minimal frontmatter convention in the implementation spec and stick to it from day one. The CLI generates the template; the user rarely writes raw markdown by hand. |
| 3 | **Attachment clutter** — flat directory mixes `.md` with `.png`, `.pdf`, etc. | High × Low | Mitigation: use a `notes/` + `attachments/` subdirectory structure from the start. The CLI places attachments in `attachments/` and references them relatively. |
| 4 | **"What was the slug?"** — timestamp-based filenames make retrieval by memory harder | Medium × Medium | Mitigation: `jot list` shows recent notes with their content summaries, not just filenames. `jot search` (backed by `rg`) searches content, not filenames. The slug is an optimization for the filesystem, not for the user. |

---

## 5. Decision

**The decision:** Store notes as individual timestamped markdown files in a `~/.jot/` directory, with a `notes/` subdirectory for content and an `attachments/` subdirectory for attached files.

**Decision rule used:** The most Unix-native, git-friendly, and independently-addressable option that requires no dependencies beyond what ships on a developer machine.

**Why this option, in one paragraph:**
Each note is a file. That means each note can be edited, deleted, shared, or committed to git independently — no database to corrupt, no schema to migrate, no lock-in. `rg` is fast enough for personal scale. The filesystem is the database, and that keeps the tool honest: `jot` is a convenience layer, not a platform. If it ever isn't enough, migrating to JSONL or SQLite is a one-time script.

**What we're explicitly trading away:**
> We're giving up **ranked full-text search and structured metadata** to get **filesystem-native simplicity, git-friendliness, and per-note independence**. The bet is that for one person's transient thoughts, `rg` is enough and the filesystem-as-DB is a feature, not a limitation.

---

## 6. Reversibility

**Classification:** Two-way door

**Reversal trigger:** Retrieval becomes unreliable — searches take >1 second, or you regularly fail to find notes you know exist.

**Reversal mechanism:** Write a migration script that iterates `~/.jot/notes/*.md`, extracts content + timestamp + tags into a JSONL file or SQLite DB, and optionally rebuilds the file tree from the new store. The CLI interface (`jot add`, `jot list`, `jot search`) doesn't change — only the storage backend. Estimated migration effort: <1 hour.

**Secondary trigger:** The directory exceeds ~2,000 files and filesystem operations become noticeably slow. Same reversal mechanism.

---

## 7. Open questions

Deliberately not decided — to be addressed in implementation planning or first-use discovery:

- **Subdirectory layout:** `~/.jot/notes/` + `~/.jot/attachments/` is the working assumption, but `~/.jot/` flat directory is simpler. Decide during implementation based on first-use feel. *(Resolve at tech-lead / coding spec phase.)*
- **Frontmatter convention:** YAML frontmatter with `tags`, `created`, `modified`? Or just a `# title` and body? The pre-mortem says consistency matters — pick one and enforce it. *(Resolve at tech-lead phase.)*
- **Filename format:** ISO timestamp + slug (`2026-05-12-143022-meeting-notes.md`) vs just slug (`meeting-notes.md`) with timestamp in frontmatter? Timestamp-first ensures sortability but costs readability. *(Resolve at tech-lead phase.)*
- **`jot edit` command?** Should `jot edit <slug>` open the file in `$EDITOR`, or is `jot` a capture-only tool and editing happens via the filesystem? The current scope is capture + list (+ search via rg), but edit is a natural extension. *(Defer to v2 unless it's trivial to add.)*
- **Pi extension integration pattern:** Should the pi extension call the CLI as a subprocess, or read/write `.md` files directly? Depends on pi's extension API. *(Resolve when pi extension work begins.)*

---

## 8. Handoff

**The next step is owned by:** `tech-lead` skill — this is a small, single-slice implementation that needs a coding spec before keystrokes.

> Hand off to `tech-lead` skill. Key inputs:
> - **Decision:** Directory of timestamped markdown files (`~/.jot/`)
> - **Command surface:** `jot add "text"`, `jot list`, `jot search "query"` (wrapping `rg`), optional `jot attach <file>` as v1 or v1.1
> - **Acceptance criteria:** Capture is sub-second. List shows recent notes with summaries. Search finds notes by content.
> - **Open questions to resolve:** subdirectory layout, frontmatter convention, filename format, `jot edit` scope.
> - **Store location:** `~/.jot/`

**Do NOT invoke tech-lead from this session.** The user runs the next skill. This brief is the handoff package.

---

## 9. Session notes

- **Bias caught:** The user initially framed this as a "CLI tool with commands" question — solution-side thinking. Rewinding to capture friction as the real problem unlocked the right design space.
- **Useful analogy:** "Filesystem-is-the-DB" emerged as the organizing principle. The tool is a convenience layer, not a platform — this constraint held throughout and eliminated options E and F cleanly.
- **Thing to remember when revisiting:** The user said "all of the above" to both "what happens when you don't capture" and "what shapes are the notes." That heterogeneity is the design challenge — the tool must accept anything without ceremony.

---

## 10. Self-check

- [x] At least 3 options were considered (6 options, including shell alias / do-nothing).
- [x] The chosen option survived a real pre-mortem (4 failure modes, 2 mitigated, 2 accepted with reversal triggers).
- [x] Reversibility is named (two-way door; migration script; specific triggers).
- [x] The trade-off is named ("giving up ranked full-text search and structured metadata to get filesystem-native simplicity, git-friendliness, and per-note independence").
- [x] The handoff points to a specific next step (tech-lead skill, with specific inputs).
- [x] The user agreed with the reframing (confirmed by "go on" through all four Diamond phases).
