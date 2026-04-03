import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from skill_installer import ensure_repo_cached, get_current_ref, pull_repo


def make_local_repo(tmp_path: Path, files: dict) -> Path:
    """Create a local git repo with one commit containing `files`."""
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
