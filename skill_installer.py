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

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _pkg_version
except ImportError:
    PackageNotFoundError = ModuleNotFoundError
    _pkg_version = None

try:
    __version__ = _pkg_version("skill-installer") if _pkg_version else "dev"
except (PackageNotFoundError, Exception):
    __version__ = os.environ.get("SKILL_INSTALLER_VERSION", "dev")

DEFAULT_INSTALL_DIR = Path.home() / ".claude" / "skills"
DEFAULT_CACHE_DIR = Path.home() / ".skill-installer" / "repos"
CONFIG_FILE = Path.home() / ".skill-installer" / "config"
METADATA_FILE = ".skill-source.json"


def load_config() -> dict:
    """Read ~/.skill-installer/config (KEY=VALUE) and return values not already in env.

    Env vars always take precedence. Lines starting with # and blank lines are ignored.
    Values may use ~ for home directory expansion.
    """
    config = {}
    if not CONFIG_FILE.exists():
        return config
    for line in CONFIG_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            config[key] = value
    return config


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

    if ".." in Path(path).parts:
        raise ValueError(f"URL path must not contain '..': {url}")

    skill_name = path.rstrip("/").split("/")[-1]
    return {
        "owner": owner,
        "repo": repo,
        "ref": ref,
        "path": path,
        "skill_name": skill_name,
    }


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
        _run_git(["reset", "--hard", "FETCH_HEAD"], cwd=repo_path)
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
    _run_git(["reset", "--hard", "FETCH_HEAD"], cwd=repo_path)
    new_ref = get_current_ref(repo_path)
    return old_ref, new_ref


def install_skill(url: str, install_dir: Path, cache_dir: Path) -> None:
    """Install a skill from a GitHub URL into install_dir."""
    parsed = parse_github_url(url)
    skill_name = parsed["skill_name"]
    dest = install_dir / skill_name

    install_dir.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        raise FileExistsError(f"Skill '{skill_name}' already exists at {dest}")

    repo_path = ensure_repo_cached(parsed["owner"], parsed["repo"], cache_dir)
    source = repo_path / parsed["path"]

    if not source.is_dir():
        raise FileNotFoundError(f"Skill folder not found in repo: {parsed['path']}")

    shutil.copytree(source, dest, symlinks=True)

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


def _apply_skill_update(skill_dir: Path, source: Path, mf: Path, meta: dict, old_ref: str, new_ref: str) -> str:
    """Replace skill files from source, preserving metadata. Returns status line."""
    skill_name = skill_dir.name
    if not source.is_dir():
        return f"  FAILED {skill_name}: path '{meta['path']}' not found in repo"
    if old_ref == new_ref:
        return f"  up-to-date {skill_name}"
    for item in skill_dir.iterdir():
        if item.name == METADATA_FILE:
            continue
        shutil.rmtree(item) if item.is_dir() else item.unlink()
    for item in source.iterdir():
        dest_item = skill_dir / item.name
        shutil.copytree(item, dest_item, symlinks=True) if item.is_dir() else shutil.copy2(item, dest_item)
    meta["ref"] = new_ref
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    mf.write_text(json.dumps(meta, indent=2))
    return f"  updated {skill_name} ({old_ref[:7]}..{new_ref[:7]})"


def update_all(install_dir: Path, cache_dir: Path) -> None:
    """Update all installed skills to latest HEAD of their source repos."""
    metadata_files = list(install_dir.glob(f"*/{METADATA_FILE}"))
    if not metadata_files:
        print("No installed skills found.")
        return

    by_repo: dict[tuple, list] = {}
    for mf in metadata_files:
        meta = json.loads(mf.read_text())
        try:
            _validate_metadata_path(meta["owner"], "owner")
            _validate_metadata_path(meta["repo"], "repo")
            _validate_metadata_path(meta["path"], "path")
        except (ValueError, KeyError) as e:
            print(f"  SKIPPED {mf.parent.name}: invalid metadata — {e}")
            continue
        key = (meta["owner"], meta["repo"])
        by_repo.setdefault(key, []).append((mf, meta))

    for (owner, repo), skills in by_repo.items():
        repo_path = cache_dir / owner / repo
        if not repo_path.exists():
            print(f"Re-cloning {owner}/{repo}...")
            ensure_repo_cached(owner, repo, cache_dir)
            old_ref = new_ref = get_current_ref(repo_path)
        else:
            old_ref, new_ref = pull_repo(repo_path)
        for mf, meta in skills:
            print(_apply_skill_update(mf.parent, repo_path / meta["path"], mf, meta, old_ref, new_ref))


def update_skill(skill_name: str, install_dir: Path, cache_dir: Path) -> None:
    """Update a single installed skill to latest HEAD."""
    skill_dir = install_dir / skill_name
    if not skill_dir.is_dir():
        raise FileNotFoundError(f"Skill '{skill_name}' is not installed")
    mf = skill_dir / METADATA_FILE
    if not mf.exists():
        raise FileNotFoundError(f"Skill '{skill_name}' has no source metadata — cannot update")
    meta = json.loads(mf.read_text())
    try:
        _validate_metadata_path(meta["owner"], "owner")
        _validate_metadata_path(meta["repo"], "repo")
        _validate_metadata_path(meta["path"], "path")
    except (ValueError, KeyError) as e:
        raise ValueError(f"Invalid metadata for '{skill_name}': {e}")
    repo_path = cache_dir / meta["owner"] / meta["repo"]
    if not repo_path.exists():
        print(f"Re-cloning {meta['owner']}/{meta['repo']}...")
        ensure_repo_cached(meta["owner"], meta["repo"], cache_dir)
        old_ref = new_ref = get_current_ref(repo_path)
    else:
        old_ref, new_ref = pull_repo(repo_path)
    print(_apply_skill_update(skill_dir, repo_path / meta["path"], mf, meta, old_ref, new_ref))


def list_skills(install_dir: Path) -> None:
    """List all installed skills with source repo and last update date."""
    if not install_dir.exists():
        print("No skills directory found.")
        return
    entries = []
    for skill_dir in sorted(install_dir.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        mf = skill_dir / METADATA_FILE
        if mf.exists():
            meta = json.loads(mf.read_text())
            source = f"{meta.get('owner', '?')}/{meta.get('repo', '?')}"
            updated = meta.get("updated_at", "")[:10]
        else:
            source, updated = "(untracked)", ""
        entries.append((skill_dir.name, source, updated))
    if not entries:
        print("No skills installed.")
        return
    name_w = max(len(e[0]) for e in entries)
    src_w = max(len(e[1]) for e in entries)
    for name, source, updated in entries:
        print(f"{name:<{name_w}}  {source:<{src_w}}  {updated}")


def info_skill(skill_name: str, install_dir: Path) -> None:
    """Show metadata for an installed skill."""
    skill_dir = install_dir / skill_name
    if not skill_dir.is_dir():
        raise FileNotFoundError(f"Skill '{skill_name}' is not installed")
    mf = skill_dir / METADATA_FILE
    if not mf.exists():
        print(f"Skill:    {skill_name}")
        print(f"Location: {skill_dir}")
        print("Source:   (untracked — no metadata)")
        return
    meta = json.loads(mf.read_text())
    print(f"Skill:     {skill_name}")
    print(f"Source:    {meta.get('source_url', '?')}")
    print(f"Repo:      {meta.get('owner', '?')}/{meta.get('repo', '?')}")
    print(f"Path:      {meta.get('path', '?')}")
    print(f"Ref:       {meta.get('ref', '?')}")
    print(f"Installed: {meta.get('installed_at', '?')[:10]}")
    print(f"Updated:   {meta.get('updated_at', '?')[:10]}")


def remove_skill(skill_name: str, install_dir: Path) -> None:
    """Remove an installed skill."""
    skill_dir = install_dir / skill_name
    if not skill_dir.is_dir():
        raise FileNotFoundError(f"Skill '{skill_name}' is not installed")
    shutil.rmtree(skill_dir)
    print(f"Removed '{skill_name}'")


def purge_cache(cache_dir: Path) -> None:
    """Delete the local git repo cache. Installed skills are not affected."""
    if not cache_dir.exists():
        print(f"Cache directory does not exist: {cache_dir}")
        return
    shutil.rmtree(cache_dir)
    print(f"Cache purged: {cache_dir}")


def _validate_metadata_path(value: str, field: str) -> None:
    """Raise ValueError if value contains path traversal or is absolute."""
    p = Path(value)
    if p.is_absolute():
        raise ValueError(f"Metadata field '{field}' must be a relative path, got: {value!r}")
    if ".." in p.parts:
        raise ValueError(f"Metadata field '{field}' must not contain '..', got: {value!r}")


def main():
    """Entry point: parse CLI args and dispatch to install/update/purge."""
    result = subprocess.run(["git", "--version"], capture_output=True)
    if result.returncode != 0:
        print("Error: git is required but not found in PATH", file=sys.stderr)
        sys.exit(1)

    config = load_config()
    install_dir = Path(os.environ.get("SKILL_INSTALL_DIR", config.get("SKILL_INSTALL_DIR", str(DEFAULT_INSTALL_DIR)))).expanduser()
    cache_dir = Path(os.environ.get("SKILL_CACHE_DIR", config.get("SKILL_CACHE_DIR", str(DEFAULT_CACHE_DIR)))).expanduser()

    parser = argparse.ArgumentParser(
        prog="ski",
        description="Install and manage Claude Code skills from GitHub",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("url", nargs="?", help="GitHub URL of the skill to install")
    group.add_argument(
        "-u", "--update", nargs="?", const="__ALL__", metavar="SKILL",
        help="Update all installed skills, or a specific one by name",
    )
    group.add_argument("-l", "--list", action="store_true", help="List all installed skills")
    group.add_argument("--info", metavar="SKILL", help="Show details for an installed skill")
    group.add_argument("--remove", metavar="SKILL", help="Remove an installed skill")
    group.add_argument("--purge-cache", action="store_true", help="Delete the local git repo cache")

    args = parser.parse_args()

    try:
        if args.update is not None:
            if args.update == "__ALL__":
                update_all(install_dir, cache_dir)
            else:
                update_skill(args.update, install_dir, cache_dir)
        elif args.list:
            list_skills(install_dir)
        elif args.info:
            info_skill(args.info, install_dir)
        elif args.remove:
            remove_skill(args.remove, install_dir)
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
