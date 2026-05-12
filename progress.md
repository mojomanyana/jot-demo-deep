# progress.md
# Last updated: 2026-05-13 01:17 (slice: jot-cli) — COMPLETE

## Done
- [x] Project scaffold — package.json, tsconfig.json, .gitignore, npm install (0d2ca33)
- [x] Remove Python implementation artifacts (46d7e4b)
- [x] Note type — src/types.ts (9943cab)
- [x] Store module — src/store.ts with addNote, listNotes, getStorePath (90348ea)
- [x] Store unit tests — 7 tests, all green (f41089e)
- [x] CLI entry point — src/cli.ts with argv dispatch (b3d1100)
- [x] CLI integration tests — 6 tests using spawnSync, all green (fdb67f0)
- [x] Bug fix: empty text rejected by `!text` check; changed to `text === undefined` (135435a)
- [x] Manual smoke test: add, add "", list — all working
- [x] Global install test: npm install -g ., jot from /tmp — working
- [x] All 13 tests pass, tsc clean
- [x] .pi/ added to .gitignore

## In progress
- (none — SLICE COMPLETE)

## Open questions / blockers
- (none)

## Notes for future context
- Node v24.14.0, tsc 5.9.3, vitest 1.6.1
- JSON Lines storage at ~/.jot/notes.jsonl (JOT_HOME overridable)
- Zero runtime dependencies; only devDeps: typescript, @types/node, vitest, tsx
- Branch: main (committed directly — no feature branch used)
- See implementation report at docs/implementation-report-jot-ts.md
- See handoff baton at docs/handoff-baton-jot-ts.md