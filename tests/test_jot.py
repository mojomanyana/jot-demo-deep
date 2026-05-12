"""Unit and integration tests for jot — CLI quick-notes tool."""

import datetime
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import jot


class EnsureDirsTests(unittest.TestCase):
    """Tests for ensure_dirs() using a temporary directory."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)
        self.notes = self.tmp_path / "notes"
        self.attachments = self.tmp_path / "attachments"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_ensure_dirs_creates_directories(self):
        with patch("jot.NOTES_DIR", self.notes), patch("jot.ATTACHMENTS_DIR", self.attachments):
            jot.ensure_dirs()
            self.assertTrue(self.notes.is_dir())
            self.assertTrue(self.attachments.is_dir())

    def test_ensure_dirs_idempotent(self):
        with patch("jot.NOTES_DIR", self.notes), patch("jot.ATTACHMENTS_DIR", self.attachments):
            jot.ensure_dirs()
            jot.ensure_dirs()  # second call should not raise
            self.assertTrue(self.notes.is_dir())
            self.assertTrue(self.attachments.is_dir())


class GenerateSlugTests(unittest.TestCase):
    """Tests for generate_slug()."""

    def test_basic(self):
        self.assertEqual(jot.generate_slug("remember this thing"), "remember-this-thing")

    def test_truncates(self):
        long_text = "a " * 50
        slug = jot.generate_slug(long_text)
        self.assertLessEqual(len(slug), jot.MAX_SLUG_LENGTH)

    def test_strips_special_chars(self):
        self.assertEqual(jot.generate_slug("hello! @world #123"), "hello-world-123")

    def test_empty_fallback(self):
        self.assertEqual(jot.generate_slug(""), "note")

    def test_unicode(self):
        # Python handles unicode natively; special chars are stripped but letters kept
        slug = jot.generate_slug("café résumé")
        self.assertEqual(slug, "café-résumé")


class GenerateFilenameTests(unittest.TestCase):
    """Tests for generate_filename()."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name) / "notes"
        self.tmp_path.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_format(self):
        ts = datetime.datetime(2026, 5, 12, 23, 5, 0)
        with patch("jot.NOTES_DIR", self.tmp_path):
            filename = jot.generate_filename("hi there", ts)
            self.assertEqual(filename, "2026-05-12-230500-hi-there.md")

    def test_collision(self):
        ts = datetime.datetime(2026, 5, 12, 23, 5, 0)
        # Pre-create the base file
        (self.tmp_path / "2026-05-12-230500-hi-there.md").write_text("existing")
        with patch("jot.NOTES_DIR", self.tmp_path):
            filename = jot.generate_filename("hi there", ts)
            self.assertEqual(filename, "2026-05-12-230500-hi-there-2.md")

    def test_multiple_collisions(self):
        ts = datetime.datetime(2026, 5, 12, 23, 5, 0)
        (self.tmp_path / "2026-05-12-230500-hi-there.md").write_text("existing")
        (self.tmp_path / "2026-05-12-230500-hi-there-2.md").write_text("existing")
        with patch("jot.NOTES_DIR", self.tmp_path):
            filename = jot.generate_filename("hi there", ts)
            self.assertEqual(filename, "2026-05-12-230500-hi-there-3.md")


class ExtractHeadingTests(unittest.TestCase):
    """Tests for extract_heading()."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _write(self, name, content):
        fp = self.tmp_path / name
        fp.write_text(content)
        return fp

    def test_heading_from_file(self):
        fp = self._write("test.md", "# Hello\n\nworld")
        self.assertEqual(jot.extract_heading(fp), "Hello")

    def test_no_heading_fallback(self):
        fp = self._write("test.md", "Just a line\nmore text")
        self.assertEqual(jot.extract_heading(fp), "Just a line")

    def test_empty_file(self):
        fp = self._write("test.md", "")
        self.assertEqual(jot.extract_heading(fp), "")

    def test_heading_not_first_line(self):
        fp = self._write("test.md", "Some intro\n# Actual heading\nbody")
        self.assertEqual(jot.extract_heading(fp), "Actual heading")


class FormatListEntryTests(unittest.TestCase):
    """Tests for format_list_entry()."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_format(self):
        fp = self.tmp_path / "2026-05-12-230500-hi.md"
        fp.write_text("# hello world\n\nsome body")
        result = jot.format_list_entry(fp)
        self.assertEqual(result, "2026-05-12 23:05:00    hello world")

    def test_unknown_date(self):
        fp = self.tmp_path / "not-a-timestamp.md"
        fp.write_text("# heading")
        result = jot.format_list_entry(fp)
        self.assertIn("(unknown date)", result)


class CmdAddTests(unittest.TestCase):
    """Integration tests for cmd_add()."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)
        self.notes = self.tmp_path / "notes"
        self.attachments = self.tmp_path / "attachments"
        self.notes.mkdir(parents=True, exist_ok=True)
        self.attachments.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _args(self, text=None):
        """Build a fake argparse namespace for cmd_add."""
        class FakeArgs:
            pass
        a = FakeArgs()
        a.text = text if text is not None else []
        return a

    def test_add_creates_note_file(self):
        with patch("jot.NOTES_DIR", self.notes), patch("jot.ATTACHMENTS_DIR", self.attachments):
            jot.cmd_add(self._args(["hello world"]))

        files = sorted(self.notes.glob("*.md"))
        self.assertEqual(len(files), 1)
        content = files[0].read_text()
        self.assertIn("# hello world", content)

    def test_add_from_stdin(self):
        fake_stdin = io.StringIO("stdin note\n")
        with patch("jot.NOTES_DIR", self.notes), \
             patch("jot.ATTACHMENTS_DIR", self.attachments), \
             patch("sys.stdin", fake_stdin):
            jot.cmd_add(self._args([]))

        files = sorted(self.notes.glob("*.md"))
        self.assertEqual(len(files), 1)
        content = files[0].read_text()
        self.assertIn("# stdin note", content)

    def test_add_multiline(self):
        with patch("jot.NOTES_DIR", self.notes), patch("jot.ATTACHMENTS_DIR", self.attachments):
            jot.cmd_add(self._args(["line1\n", "line2\n", "line3"]))

        files = sorted(self.notes.glob("*.md"))
        self.assertEqual(len(files), 1)
        content = files[0].read_text()
        self.assertIn("# line1", content)
        self.assertIn("line2", content)
        self.assertIn("line3", content)

    def test_add_empty_errors(self):
        with patch("jot.NOTES_DIR", self.notes), patch("jot.ATTACHMENTS_DIR", self.attachments):
            with self.assertRaises(SystemExit) as cm:
                jot.cmd_add(self._args([]))
            self.assertEqual(cm.exception.code, 1)

    def test_add_stdin_tty_errors(self):
        with patch("jot.NOTES_DIR", self.notes), \
             patch("jot.ATTACHMENTS_DIR", self.attachments), \
             patch("sys.stdin.isatty", return_value=True):
            with self.assertRaises(SystemExit) as cm:
                jot.cmd_add(self._args([]))
            self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()