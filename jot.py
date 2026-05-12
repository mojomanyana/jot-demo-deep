#!/usr/bin/env python3
"""jot — quick notes from the command line. Store notes in ~/.jot/notes/."""

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

JOT_DIR = Path.home() / ".jot"
NOTES_DIR = JOT_DIR / "notes"
ATTACHMENTS_DIR = JOT_DIR / "attachments"
MAX_SLUG_LENGTH = 60


# --- helpers ---

def ensure_dirs():
    """Create JOT_DIR, NOTES_DIR, and ATTACHMENTS_DIR if they don't exist."""
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)


def generate_slug(text):
    """Convert text to a kebab-case slug used in filenames.

    'remember this thing' -> 'remember-this-thing'
    """
    if not text or not text.strip():
        return "note"

    # Lowercase, take first ~5 words
    words = text.strip().lower().split()[:5]
    joined = "-".join(words)

    # Strip non-alphanumeric (keep hyphens), collapse multiple hyphens
    slug = re.sub(r"[^\w-]", "", joined)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")

    if not slug:
        return "note"

    # Truncate
    if len(slug) > MAX_SLUG_LENGTH:
        slug = slug[:MAX_SLUG_LENGTH].rstrip("-")

    return slug


def generate_filename(heading, ts):
    """Generate a collision-free note filename.

    'remember this thing', datetime(2026,5,12,23,5,0)
    -> '2026-05-12-230500-remember-this-thing.md'

    If the filename already exists, appends -2, -3, etc. until unique.
    """
    slug = generate_slug(heading)
    base = f"{ts:%Y-%m-%d-%H%M%S}-{slug}"
    filename = f"{base}.md"
    filepath = NOTES_DIR / filename

    if not filepath.exists():
        return filename

    counter = 2
    while True:
        filename = f"{base}-{counter}.md"
        filepath = NOTES_DIR / filename
        if not filepath.exists():
            return filename
        counter += 1


def extract_heading(filepath):
    """Read the first '# ' heading from a markdown file.

    Falls back to the first non-empty line if no heading found.
    Reads only the first few lines for performance.
    """
    try:
        with open(filepath) as f:
            first_line = None
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                if first_line is None:
                    first_line = stripped
                if stripped.startswith("# "):
                    return stripped[2:]
            # No # heading found; return first non-empty line
            return first_line if first_line else ""
    except (OSError, IOError):
        return ""


def format_list_entry(filepath):
    """Format a note file for display in 'jot list'.

    '2026-05-12 23:05:00    heading-text'
    """
    # Parse timestamp from filename: YYYY-MM-DD-HHMMSS-slug.md
    name = filepath.name
    try:
        prefix = name[:17]  # '2026-05-12-230500'
        ts = datetime.datetime.strptime(prefix, "%Y-%m-%d-%H%M%S")
    except (ValueError, IndexError):
        return f"{name}    (unknown date)"

    heading = extract_heading(filepath)
    return f"{ts:%Y-%m-%d %H:%M:%S}    {heading}"


# --- commands ---

def cmd_add(args):
    """Add a new note from args.text or stdin."""
    ensure_dirs()
    if args.text:
        content = " ".join(args.text)
    else:
        if sys.stdin.isatty():
            print("Error: no text provided and stdin is a terminal.", file=sys.stderr)
            print("Usage: jot add 'note text'  OR  echo 'text' | jot add", file=sys.stderr)
            sys.exit(1)
        content = sys.stdin.read().strip()

    if not content:
        print("Error: note text cannot be empty.", file=sys.stderr)
        sys.exit(1)

    lines = content.split("\n", 1)
    heading = lines[0].strip()
    body = lines[1].strip() if len(lines) > 1 else ""

    ts = datetime.datetime.now()
    filename = generate_filename(heading, ts)
    filepath = NOTES_DIR / filename

    with open(filepath, "w") as f:
        f.write(f"# {heading}\n")
        if body:
            f.write(f"\n{body}\n")

    print(str(filepath))