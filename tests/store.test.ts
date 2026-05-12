import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import * as os from 'node:os';

// Store module doesn't exist yet — tests will fail to import (TDD red phase).
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { addNote, listNotes, getStorePath } from '../src/store';

let tempDir: string;
let originalJotHome: string | undefined;

beforeEach(async () => {
  tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'jot-test-'));
  originalJotHome = process.env.JOT_HOME;
  process.env.JOT_HOME = tempDir;
});

afterEach(async () => {
  process.env.JOT_HOME = originalJotHome;
  await fs.rm(tempDir, { recursive: true, force: true });
});

describe('store', () => {
  describe('addNote', () => {
    it('adds_note_to_file', async () => {
      await addNote('hello');

      const notes = await listNotes();
      expect(notes).toHaveLength(1);
      expect(notes[0].text).toBe('hello');
      expect(notes[0].ts).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
    });

    it('handles_unicode_text', async () => {
      const text = 'café 你好 🎉';
      await addNote(text);

      const notes = await listNotes();
      expect(notes[0].text).toBe(text);
    });

    it('handles_empty_text', async () => {
      await addNote('');

      const notes = await listNotes();
      expect(notes).toHaveLength(1);
      expect(notes[0].text).toBe('');
    });

    it('handles_newlines_in_text', async () => {
      await addNote('line1\nline2');

      const notes = await listNotes();
      expect(notes[0].text).toBe('line1\nline2');
    });
  });

  describe('listNotes', () => {
    it('lists_multiple_notes_in_order', async () => {
      await addNote('a');
      await addNote('b');
      await addNote('c');

      const notes = await listNotes();
      expect(notes).toHaveLength(3);
      expect(notes.map(n => n.text)).toEqual(['a', 'b', 'c']);
    });

    it('lists_empty_array_when_no_file', async () => {
      const notes = await listNotes();
      expect(notes).toEqual([]);
    });
  });

  describe('getStorePath', () => {
    it('getStorePath_respects_JOT_HOME', () => {
      const storePath = getStorePath();
      expect(storePath).toBe(path.join(tempDir, 'notes.jsonl'));
    });
  });
});