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


def parse_github_url(url: str) -> dict:
    """Parse a GitHub URL into components needed for installation.

    Supports blob, tree, and raw.githubusercontent.com URLs.
    Returns dict with keys: owner, repo, ref, path, skill_name.
    Raises ValueError for unsupported formats.
    """
    parsed = urlparse(url)

    if parsed.hostname == "raw.githubusercontent.com":
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 4:
            raise ValueError(f"Invalid raw GitHub URL: {url}")
        owner, repo, ref = parts[0], parts[1], parts[2]
        path = "/".join(parts[3:-1])
    elif parsed.hostname == "github.com":
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 4:
            raise ValueError(f"Unsupported GitHub URL (too short): {url}")
        owner, repo, url_type = parts[0], parts[1], parts[2]
        if url_type not in ("blob", "tree"):
            raise ValueError(f"Unsupported GitHub URL type '{url_type}': {url}")
        if len(parts) < 5:
            raise ValueError(f"Unsupported GitHub URL (too short): {url}")
        ref = parts[3]
        if url_type == "blob":
            path = "/".join(parts[4:-1])
        elif url_type == "tree":
            path = "/".join(parts[4:])
    else:
        raise ValueError(f"Unsupported URL host '{parsed.hostname}': {url}")

    if not path:
        raise ValueError(f"Could not determine skill folder path from URL: {url}")

    skill_name = path.rstrip("/").split("/")[-1]
    return {
        "owner": owner,
        "repo": repo,
        "ref": ref,
        "path": path,
        "skill_name": skill_name,
    }
