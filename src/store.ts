import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import * as os from 'node:os';
import { Note } from './types';

export function getStorePath(): string {
  const jotHome = process.env.JOT_HOME;
  if (jotHome) {
    return path.join(jotHome, 'notes.jsonl');
  }
  return path.join(os.homedir(), '.jot', 'notes.jsonl');
}

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