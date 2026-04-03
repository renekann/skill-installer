#!/usr/bin/env python3
"""skill-install: Install Claude Code skills from GitHub."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_INSTALL_DIR = Path.home() / "Documents" / "claude-config" / "skills"
DEFAULT_CACHE_DIR = Path.home() / ".skill-installer" / "repos"
METADATA_FILE = ".skill-source.json"
