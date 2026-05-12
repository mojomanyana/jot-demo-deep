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