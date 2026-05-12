export interface Note {
  /** The note content — user-provided text. May be empty string. */
  text: string;
  /** ISO 8601 timestamp of when the note was created. */
  ts: string;
}