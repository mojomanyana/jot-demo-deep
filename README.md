# jot

A minimal CLI tool for quick todo notes.

## Usage

```bash
# Add a note
jot add remember to buy milk

# List all notes
jot list
```

## Install

```bash
npm install
npm run build
npm link
```

## Development

```bash
# Run tests
npm test

# Type check
npm run typecheck

# Run directly without building
npx tsx src/cli.ts add "hello world"
npx tsx src/cli.ts list
```

## Storage

Notes are stored in `~/.jot.json`. Override with the `JOT_FILE` environment variable.

## Design

- Zero runtime dependencies
- Two commands: `add` and `list`
- JSON file with atomic writes (temp + rename)
- TypeScript with strict mode
- Full test coverage with vitest
