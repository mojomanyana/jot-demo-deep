import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { spawnSync } from 'node:child_process';
import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import * as os from 'node:os';

let tempDir: string;

function runJot(args: string[]): { stdout: string; stderr: string; exitCode: number } {
  const result = spawnSync('npx', ['tsx', 'src/cli.ts', ...args], {
    env: { ...process.env, JOT_HOME: tempDir },
    encoding: 'utf-8',
    timeout: 5000,
  });
  return {
    stdout: result.stdout.trim(),
    stderr: result.stderr.trim(),
    exitCode: result.status ?? 1,
  };
}

beforeEach(async () => {
  tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'jot-cli-test-'));
});

afterEach(async () => {
  await fs.rm(tempDir, { recursive: true, force: true });
});

describe('jot CLI', () => {
  describe('jot add', () => {
    it('add_command_writes_note_and_exits_0', async () => {
      const result = runJot(['add', 'hello world']);
      expect(result.exitCode).toBe(0);

      const filePath = path.join(tempDir, 'notes.jsonl');
      const content = await fs.readFile(filePath, 'utf-8');
      const lines = content.trim().split('\n');
      expect(lines).toHaveLength(1);

      const note = JSON.parse(lines[0]);
      expect(note.text).toBe('hello world');
      expect(note.ts).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
    });

    it('add_missing_text_shows_usage', () => {
      const result = runJot(['add']);
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toContain('Usage');
    });
  });

  describe('jot list', () => {
    it('list_command_prints_formatted_notes', async () => {
      // Prepopulate the file
      const filePath = path.join(tempDir, 'notes.jsonl');
      const dir = path.dirname(filePath);
      await fs.mkdir(dir, { recursive: true });
      const note1 = JSON.stringify({ text: 'first note', ts: '2026-05-13T14:00:00.000Z' }) + '\n';
      const note2 = JSON.stringify({ text: 'second note', ts: '2026-05-13T15:30:00.000Z' }) + '\n';
      await fs.writeFile(filePath, note1 + note2, 'utf-8');

      const result = runJot(['list']);
      expect(result.exitCode).toBe(0);
      // Timestamps rendered in local timezone — verify format and text only
      expect(result.stdout).toMatch(/\[\d{2}:\d{2}\] first note/);
      expect(result.stdout).toMatch(/\[\d{2}:\d{2}\] second note/);
    });

    it('list_prints_placeholder_when_empty', () => {
      const result = runJot(['list']);
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toContain('No notes yet.');
    });
  });

  describe('usage and errors', () => {
    it('unknown_command_shows_usage', () => {
      const result = runJot(['bogus']);
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toContain('Usage');
    });

    it('no_command_shows_usage_exits_0', () => {
      const result = runJot([]);
      expect(result.exitCode).toBe(0);
      expect(result.stderr).toContain('Usage');
    });
  });
});