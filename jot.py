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