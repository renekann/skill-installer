# Skill Installer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A single Python script that installs Claude Code skills from GitHub URLs into a local directory, tracks their origins in a `.skill-source.json` metadata file, and supports bulk updates and cache purging.

**Architecture:** One file (`skill_installer.py`) with a `#!/usr/bin/env python3` shebang. URL parsing extracts owner/repo/ref/path from blob, tree, and raw GitHub URLs. A local git cache (`~/.skill-installer/repos/{owner}/{repo}`) holds shallow clones; skill folders are copied from the cache. `.skill-source.json` in each installed skill folder is the source of truth for `--update-all`.

**Tech Stack:** Python 3.9+ stdlib only (argparse, json, shutil, subprocess, pathlib, datetime, urllib.parse, os), pytest for tests, git CLI.

---

### Task 1: Project scaffold

**Files:**
- Create: `skill_installer.py`
- Create: `tests/__init__.py`
- Create: `tests/test_url_parser.py`
- Create: `tests/test_installer.py`

- [ ] **Step 1: Create `skill_installer.py` with shebang and imports**

```python
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
```

- [ ] **Step 2: Create test files**

`tests/__init__.py` — empty file.

`tests/test_url_parser.py`:
```python
import pytest
```

`tests/test_installer.py`:
```python
import pytest
```

- [ ] **Step 3: Verify pytest runs**

```bash
cd /Users/rene/dev/skill-installer && python3 -m pytest tests/ -v
```
Expected: `no tests ran` (0 errors, 0 failures).

- [ ] **Step 4: Commit**

```bash
command git add skill_installer.py tests/
command git commit -m "chore: project scaffold"
```

---

### Task 2: URL Parser

**Files:**
- Modify: `skill_installer.py` (add `parse_github_url`)
- Modify: `tests/test_url_parser.py`

- [ ] **Step 1: Write failing tests**

`tests/test_url_parser.py`:
```python
import pytest
from skill_installer import parse_github_url


def test_blob_url():
    url = "https://github.com/mblode/agent-skills/blob/bbb8ad46/skills/optimise-seo/SKILL.md"
    result = parse_github_url(url)
    assert result == {
        "owner": "mblode",
        "repo": "agent-skills",
        "ref": "bbb8ad46",
        "path": "skills/optimise-seo",
        "skill_name": "optimise-seo",
    }


def test_tree_url():
    url = "https://github.com/mblode/agent-skills/tree/main/skills/optimise-seo"
    result = parse_github_url(url)
    assert result == {
        "owner": "mblode",
        "repo": "agent-skills",
        "ref": "main",
        "path": "skills/optimise-seo",
        "skill_name": "optimise-seo",
    }


def test_raw_url():
    url = "https://raw.githubusercontent.com/mblode/agent-skills/bbb8ad46/skills/optimise-seo/SKILL.md"
    result = parse_github_url(url)
    assert result == {
        "owner": "mblode",
        "repo": "agent-skills",
        "ref": "bbb8ad46",
        "path": "skills/optimise-seo",
        "skill_name": "optimise-seo",
    }


def test_invalid_host_raises():
    with pytest.raises(ValueError, match="Unsupported URL"):
        parse_github_url("https://gitlab.com/foo/bar")


def test_unsupported_url_type_raises():
    with pytest.raises(ValueError, match="Unsupported GitHub URL type"):
        parse_github_url("https://github.com/foo/bar/pulls/123")


def test_blob_at_repo_root_raises():
    # blob URL with file directly at repo root (no parent folder = no skill name)
    with pytest.raises(ValueError, match="skill folder path"):
        parse_github_url("https://github.com/foo/bar/blob/main/SKILL.md")
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python3 -m pytest tests/test_url_parser.py -v
```
Expected: `ImportError` or `FAILED` — `parse_github_url` does not exist yet.

- [ ] **Step 3: Implement `parse_github_url` in `skill_installer.py`**

Add after the constants:
```python
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
        if len(parts) < 5:
            raise ValueError(f"Unsupported GitHub URL (too short): {url}")
        owner, repo, url_type, ref = parts[0], parts[1], parts[2], parts[3]
        if url_type == "blob":
            path = "/".join(parts[4:-1])
        elif url_type == "tree":
            path = "/".join(parts[4:])
        else:
            raise ValueError(f"Unsupported GitHub URL type '{url_type}': {url}")
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python3 -m pytest tests/test_url_parser.py -v
```
Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
command git add skill_installer.py tests/test_url_parser.py
command git commit -m "feat: URL parser for blob/tree/raw GitHub URLs"
```

---

### Task 3: Git cache helpers

**Files:**
- Modify: `skill_installer.py` (add `_run_git`, `ensure_repo_cached`, `get_current_ref`, `pull_repo`)
- Modify: `tests/test_installer.py`

These tests use real temp git repos — no mocks.

- [ ] **Step 1: Write failing tests**

`tests/test_installer.py`:
```python
import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from skill_installer import ensure_repo_cached, get_current_ref, pull_repo


def make_local_repo(tmp_path: Path, files: dict) -> Path:
    """Create a bare-ish local git repo with one commit containing `files`."""
    repo = tmp_path / "remote"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    for rel_path, content in files.items():
        p = repo / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    return repo


def test_ensure_repo_cached_clones(tmp_path):
    remote = make_local_repo(tmp_path, {"skills/my-skill/SKILL.md": "# My Skill"})
    cache_dir = tmp_path / "cache"

    # Monkey-patch clone to use local path instead of github URL
    import skill_installer
    original = skill_installer._clone_url
    skill_installer._clone_url = lambda owner, repo: str(remote)

    try:
        repo_path = ensure_repo_cached("testowner", "testrepo", cache_dir)
        assert repo_path.is_dir()
        assert (repo_path / "skills" / "my-skill" / "SKILL.md").exists()
    finally:
        skill_installer._clone_url = original


def test_get_current_ref(tmp_path):
    remote = make_local_repo(tmp_path, {"README.md": "hello"})
    cache_dir = tmp_path / "cache"

    import skill_installer
    original = skill_installer._clone_url
    skill_installer._clone_url = lambda owner, repo: str(remote)

    try:
        repo_path = ensure_repo_cached("o", "r", cache_dir)
        ref = get_current_ref(repo_path)
        assert len(ref) == 40  # full SHA1
    finally:
        skill_installer._clone_url = original


def test_pull_repo_already_up_to_date(tmp_path):
    remote = make_local_repo(tmp_path, {"README.md": "hello"})
    cache_dir = tmp_path / "cache"

    import skill_installer
    original = skill_installer._clone_url
    skill_installer._clone_url = lambda owner, repo: str(remote)

    try:
        repo_path = ensure_repo_cached("o", "r", cache_dir)
        old_ref, new_ref = pull_repo(repo_path)
        assert old_ref == new_ref  # no new commits
    finally:
        skill_installer._clone_url = original
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python3 -m pytest tests/test_installer.py -v
```
Expected: `ImportError` — git functions not yet defined.

- [ ] **Step 3: Implement git helpers in `skill_installer.py`**

Add after `parse_github_url`:
```python
def _clone_url(owner: str, repo: str) -> str:
    """Return the clone URL for a GitHub repo. Extracted for testability."""
    return f"https://github.com/{owner}/{repo}"


def _run_git(args: list, cwd: Path = None) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git"] + args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result


def ensure_repo_cached(owner: str, repo: str, cache_dir: Path) -> Path:
    """Clone repo if not cached, otherwise fetch and reset to origin/HEAD."""
    repo_path = cache_dir / owner / repo
    if repo_path.exists():
        _run_git(["fetch", "--depth", "1", "origin"], cwd=repo_path)
        _run_git(["reset", "--hard", "origin/HEAD"], cwd=repo_path)
    else:
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        _run_git(["clone", "--depth", "1", _clone_url(owner, repo), str(repo_path)])
    return repo_path


def get_current_ref(repo_path: Path) -> str:
    """Return the current HEAD commit hash."""
    return _run_git(["rev-parse", "HEAD"], cwd=repo_path).stdout.strip()


def pull_repo(repo_path: Path) -> tuple[str, str]:
    """Fetch + reset to origin/HEAD. Returns (old_ref, new_ref)."""
    old_ref = get_current_ref(repo_path)
    _run_git(["fetch", "--depth", "1", "origin"], cwd=repo_path)
    _run_git(["reset", "--hard", "origin/HEAD"], cwd=repo_path)
    new_ref = get_current_ref(repo_path)
    return old_ref, new_ref
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python3 -m pytest tests/test_installer.py -v -k "cached or ref or pull"
```
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
command git add skill_installer.py tests/test_installer.py
command git commit -m "feat: git cache helpers (clone/fetch/pull)"
```

---

### Task 4: Install command

**Files:**
- Modify: `skill_installer.py` (add `install_skill`)
- Modify: `tests/test_installer.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_installer.py`:
```python
from skill_installer import install_skill, METADATA_FILE


def test_install_skill(tmp_path):
    remote = make_local_repo(tmp_path, {
        "skills/my-skill/SKILL.md": "# My Skill",
        "skills/my-skill/prompts/prompt.md": "do stuff",
    })
    cache_dir = tmp_path / "cache"
    install_dir = tmp_path / "skills"
    install_dir.mkdir()

    import skill_installer
    original = skill_installer._clone_url
    skill_installer._clone_url = lambda o, r: str(remote)

    try:
        install_skill(
            "https://github.com/testowner/testrepo/tree/main/skills/my-skill",
            install_dir,
            cache_dir,
        )
        skill_dir = install_dir / "my-skill"
        assert (skill_dir / "SKILL.md").exists()
        assert (skill_dir / "prompts" / "prompt.md").exists()
        meta = json.loads((skill_dir / METADATA_FILE).read_text())
        assert meta["owner"] == "testowner"
        assert meta["repo"] == "testrepo"
        assert meta["path"] == "skills/my-skill"
        assert meta["skill_name"] == "my-skill"
        assert "installed_at" in meta
        assert "ref" in meta
    finally:
        skill_installer._clone_url = original


def test_install_skill_already_exists(tmp_path):
    remote = make_local_repo(tmp_path, {"skills/my-skill/SKILL.md": "# My Skill"})
    cache_dir = tmp_path / "cache"
    install_dir = tmp_path / "skills"
    (install_dir / "my-skill").mkdir(parents=True)

    import skill_installer
    original = skill_installer._clone_url
    skill_installer._clone_url = lambda o, r: str(remote)

    try:
        with pytest.raises(FileExistsError, match="already exists"):
            install_skill(
                "https://github.com/testowner/testrepo/tree/main/skills/my-skill",
                install_dir,
                cache_dir,
            )
    finally:
        skill_installer._clone_url = original
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python3 -m pytest tests/test_installer.py -v -k "install"
```
Expected: `ImportError` — `install_skill` not defined.

- [ ] **Step 3: Implement `install_skill` in `skill_installer.py`**

Add after `pull_repo`:
```python
def install_skill(url: str, install_dir: Path, cache_dir: Path) -> None:
    """Install a skill from a GitHub URL into install_dir."""
    parsed = parse_github_url(url)
    skill_name = parsed["skill_name"]
    dest = install_dir / skill_name

    if dest.exists():
        raise FileExistsError(f"Skill '{skill_name}' already exists at {dest}")

    repo_path = ensure_repo_cached(parsed["owner"], parsed["repo"], cache_dir)
    source = repo_path / parsed["path"]

    if not source.is_dir():
        raise FileNotFoundError(f"Skill folder not found in repo: {parsed['path']}")

    shutil.copytree(source, dest)

    now = datetime.now(timezone.utc).isoformat()
    metadata = {
        "source_url": url,
        "owner": parsed["owner"],
        "repo": parsed["repo"],
        "ref": get_current_ref(repo_path),
        "path": parsed["path"],
        "skill_name": skill_name,
        "installed_at": now,
        "updated_at": now,
    }
    (dest / METADATA_FILE).write_text(json.dumps(metadata, indent=2))
    print(f"Installed '{skill_name}' to {dest}")
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python3 -m pytest tests/test_installer.py -v -k "install"
```
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
command git add skill_installer.py tests/test_installer.py
command git commit -m "feat: install_skill command"
```

---

### Task 5: Update command

**Files:**
- Modify: `skill_installer.py` (add `update_all`)
- Modify: `tests/test_installer.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_installer.py`:
```python
from skill_installer import update_all


def _make_remote_with_commit(tmp_path: Path, subdir: str, initial_content: str) -> Path:
    remote = make_local_repo(tmp_path, {f"{subdir}/SKILL.md": initial_content})
    return remote


def test_update_all_no_skills(tmp_path, capsys):
    install_dir = tmp_path / "skills"
    install_dir.mkdir()
    update_all(install_dir, tmp_path / "cache")
    assert "No installed skills" in capsys.readouterr().out


def test_update_all_already_up_to_date(tmp_path, capsys):
    remote = make_local_repo(tmp_path, {"skills/my-skill/SKILL.md": "v1"})
    cache_dir = tmp_path / "cache"
    install_dir = tmp_path / "skills"
    install_dir.mkdir()

    import skill_installer
    original = skill_installer._clone_url
    skill_installer._clone_url = lambda o, r: str(remote)

    try:
        install_skill(
            "https://github.com/o/r/tree/main/skills/my-skill",
            install_dir,
            cache_dir,
        )
        capsys.readouterr()  # clear output
        update_all(install_dir, cache_dir)
        out = capsys.readouterr().out
        assert "up-to-date" in out
    finally:
        skill_installer._clone_url = original


def test_update_all_updates_skill(tmp_path, capsys):
    remote = make_local_repo(tmp_path, {"skills/my-skill/SKILL.md": "v1"})
    cache_dir = tmp_path / "cache"
    install_dir = tmp_path / "skills"
    install_dir.mkdir()

    import skill_installer
    original = skill_installer._clone_url
    skill_installer._clone_url = lambda o, r: str(remote)

    try:
        install_skill(
            "https://github.com/o/r/tree/main/skills/my-skill",
            install_dir,
            cache_dir,
        )

        # Add a new commit to the remote
        (remote / "skills" / "my-skill" / "SKILL.md").write_text("v2")
        subprocess.run(["git", "add", "."], cwd=remote, check=True, capture_output=True)
        subprocess.run(["git", "-c", "user.email=t@t.com", "-c", "user.name=T",
                        "commit", "-m", "update"], cwd=remote, check=True, capture_output=True)

        capsys.readouterr()
        update_all(install_dir, cache_dir)
        out = capsys.readouterr().out
        assert "updated" in out
        assert (install_dir / "my-skill" / "SKILL.md").read_text() == "v2"
        meta = json.loads((install_dir / "my-skill" / METADATA_FILE).read_text())
        assert meta["updated_at"] != meta["installed_at"]
    finally:
        skill_installer._clone_url = original
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python3 -m pytest tests/test_installer.py -v -k "update"
```
Expected: `ImportError` — `update_all` not defined.

- [ ] **Step 3: Implement `update_all` in `skill_installer.py`**

Add after `install_skill`:
```python
def update_all(install_dir: Path, cache_dir: Path) -> None:
    """Update all installed skills to latest HEAD of their source repos."""
    metadata_files = list(install_dir.glob(f"*/{METADATA_FILE}"))
    if not metadata_files:
        print("No installed skills found.")
        return

    # Group by repo
    by_repo: dict[tuple, list] = {}
    for mf in metadata_files:
        meta = json.loads(mf.read_text())
        key = (meta["owner"], meta["repo"])
        by_repo.setdefault(key, []).append((mf, meta))

    # Pull each repo once, then update each skill
    for (owner, repo), skills in by_repo.items():
        repo_path = cache_dir / owner / repo
        if not repo_path.exists():
            print(f"Re-cloning {owner}/{repo}...")
            ensure_repo_cached(owner, repo, cache_dir)
            old_ref = new_ref = get_current_ref(repo_path)
        else:
            old_ref, new_ref = pull_repo(repo_path)

        for mf, meta in skills:
            skill_dir = mf.parent
            skill_name = skill_dir.name
            source = repo_path / meta["path"]

            if not source.is_dir():
                print(f"  FAILED {skill_name}: path '{meta['path']}' not found in repo")
                continue

            if old_ref == new_ref:
                print(f"  up-to-date {skill_name}")
                continue

            # Replace contents, preserving metadata file
            for item in skill_dir.iterdir():
                if item.name == METADATA_FILE:
                    continue
                shutil.rmtree(item) if item.is_dir() else item.unlink()

            for item in source.iterdir():
                dest_item = skill_dir / item.name
                shutil.copytree(item, dest_item) if item.is_dir() else shutil.copy2(item, dest_item)

            meta["ref"] = new_ref
            meta["updated_at"] = datetime.now(timezone.utc).isoformat()
            mf.write_text(json.dumps(meta, indent=2))
            print(f"  updated {skill_name} ({old_ref[:7]}..{new_ref[:7]})")
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python3 -m pytest tests/test_installer.py -v -k "update"
```
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
command git add skill_installer.py tests/test_installer.py
command git commit -m "feat: update_all command"
```

---

### Task 6: Purge cache command

**Files:**
- Modify: `skill_installer.py` (add `purge_cache`)
- Modify: `tests/test_installer.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_installer.py`:
```python
from skill_installer import purge_cache


def test_purge_cache_deletes_cache(tmp_path, capsys):
    cache_dir = tmp_path / "cache"
    (cache_dir / "owner" / "repo").mkdir(parents=True)
    (cache_dir / "owner" / "repo" / "file.txt").write_text("data")

    purge_cache(cache_dir)
    assert not cache_dir.exists()
    assert "purged" in capsys.readouterr().out


def test_purge_cache_nonexistent(tmp_path, capsys):
    cache_dir = tmp_path / "nonexistent"
    purge_cache(cache_dir)
    assert "does not exist" in capsys.readouterr().out
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python3 -m pytest tests/test_installer.py -v -k "purge"
```
Expected: `ImportError` — `purge_cache` not defined.

- [ ] **Step 3: Implement `purge_cache` in `skill_installer.py`**

Add after `update_all`:
```python
def purge_cache(cache_dir: Path) -> None:
    """Delete the local git repo cache. Installed skills are not affected."""
    if not cache_dir.exists():
        print(f"Cache directory does not exist: {cache_dir}")
        return
    shutil.rmtree(cache_dir)
    print(f"Cache purged: {cache_dir}")
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python3 -m pytest tests/test_installer.py -v -k "purge"
```
Expected: 2 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
python3 -m pytest tests/ -v
```
Expected: all tests PASS, no warnings.

- [ ] **Step 6: Commit**

```bash
command git add skill_installer.py tests/test_installer.py
command git commit -m "feat: purge_cache command"
```

---

### Task 7: CLI entry point + README

**Files:**
- Modify: `skill_installer.py` (add `main`, make executable)
- Create: `README.md`

- [ ] **Step 1: Add `main()` to `skill_installer.py`**

Append to `skill_installer.py`:
```python
def main():
    result = subprocess.run(["git", "--version"], capture_output=True)
    if result.returncode != 0:
        print("Error: git is required but not found in PATH", file=sys.stderr)
        sys.exit(1)

    install_dir = Path(os.environ.get("SKILL_INSTALL_DIR", str(DEFAULT_INSTALL_DIR))).expanduser()
    cache_dir = Path(os.environ.get("SKILL_CACHE_DIR", str(DEFAULT_CACHE_DIR))).expanduser()

    parser = argparse.ArgumentParser(
        prog="skill-install",
        description="Install Claude Code skills from GitHub",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("url", nargs="?", help="GitHub URL of the skill to install")
    group.add_argument("--update-all", action="store_true", help="Update all installed skills to latest")
    group.add_argument("--purge-cache", action="store_true", help="Delete the local git repo cache")

    args = parser.parse_args()

    try:
        if args.update_all:
            update_all(install_dir, cache_dir)
        elif args.purge_cache:
            purge_cache(cache_dir)
        elif args.url:
            install_skill(args.url, install_dir, cache_dir)
        else:
            parser.print_help()
            sys.exit(1)
    except (ValueError, FileExistsError, FileNotFoundError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make script executable**

```bash
chmod +x /Users/rene/dev/skill-installer/skill_installer.py
```

- [ ] **Step 3: Smoke test CLI**

```bash
python3 skill_installer.py --help
```
Expected output:
```
usage: skill-install [-h] [--update-all | --purge-cache] [url]
...
```

- [ ] **Step 4: Write `README.md`**

```markdown
# skill-installer

Install Claude Code skills from GitHub with one command.

## Setup

```bash
# Make executable and symlink to PATH
chmod +x /path/to/skill_installer.py
ln -s /path/to/skill_installer.py /usr/local/bin/skill-install
```

## Usage

```bash
# Install a skill (blob, tree, or raw.githubusercontent.com URL)
skill-install https://github.com/mblode/agent-skills/blob/main/skills/optimise-seo/SKILL.md

# Update all installed skills to latest
skill-install --update-all

# Clear the local git repo cache
skill-install --purge-cache
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SKILL_INSTALL_DIR` | `~/Documents/claude-config/skills` | Where skills are installed |
| `SKILL_CACHE_DIR` | `~/.skill-installer/repos` | Local git clone cache |

```bash
export SKILL_INSTALL_DIR=~/my-skills
skill-install https://github.com/...
```

## How it works

1. The GitHub URL is parsed to extract the owner, repo, and skill folder path.
2. The repo is cloned (shallow) into `SKILL_CACHE_DIR/{owner}/{repo}/` — or fetched if already cached.
3. The skill folder is copied into `SKILL_INSTALL_DIR/{skill-name}/`.
4. A `.skill-source.json` file is written into the skill folder with the source URL, repo, and commit hash.

Multiple skills from the same repo share one cached clone. `--update-all` runs one `git pull` per repo, then re-copies all affected skill folders.

## Requirements

- Python 3.9+
- `git` in PATH
- No additional Python packages required
```

- [ ] **Step 5: Run full test suite one final time**

```bash
python3 -m pytest tests/ -v
```
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
command git add skill_installer.py README.md
command git commit -m "feat: CLI entry point and README"
```
