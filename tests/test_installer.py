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


def test_install_skill_from_repo_root(tmp_path):
    remote = make_local_repo(tmp_path, {
        "SKILL.md": "# Root Skill",
        "references/usage.md": "use it",
    })
    cache_dir = tmp_path / "cache"
    install_dir = tmp_path / "skills"
    install_dir.mkdir()

    import skill_installer
    original = skill_installer._clone_url
    skill_installer._clone_url = lambda o, r: str(remote)

    try:
        install_skill(
            "https://github.com/testowner/testrepo/blob/main/SKILL.md",
            install_dir,
            cache_dir,
        )
        skill_dir = install_dir / "testrepo"
        assert (skill_dir / "SKILL.md").exists()
        assert (skill_dir / "references" / "usage.md").exists()
        assert not (skill_dir / ".git").exists()
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


from skill_installer import update_all


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


from skill_installer import list_skills, info_skill, remove_skill, update_skill


def test_list_skills_empty(tmp_path, capsys):
    install_dir = tmp_path / "skills"
    install_dir.mkdir()
    list_skills(install_dir)
    assert "No skills" in capsys.readouterr().out


def test_list_skills_shows_tracked_and_untracked(tmp_path, capsys):
    install_dir = tmp_path / "skills"
    (install_dir / "tracked-skill").mkdir(parents=True)
    (install_dir / "tracked-skill" / METADATA_FILE).write_text(json.dumps({
        "owner": "foo", "repo": "bar", "updated_at": "2026-04-04T00:00:00+00:00",
    }))
    (install_dir / "untracked-skill").mkdir()

    list_skills(install_dir)
    out = capsys.readouterr().out
    assert "tracked-skill" in out
    assert "foo/bar" in out
    assert "untracked-skill" in out
    assert "(untracked)" in out


def test_info_skill_with_metadata(tmp_path, capsys):
    install_dir = tmp_path / "skills"
    (install_dir / "my-skill").mkdir(parents=True)
    (install_dir / "my-skill" / METADATA_FILE).write_text(json.dumps({
        "source_url": "https://github.com/foo/bar/tree/main/skills/my-skill",
        "owner": "foo", "repo": "bar", "path": "skills/my-skill",
        "ref": "abc123def456", "installed_at": "2026-04-04T00:00:00+00:00",
        "updated_at": "2026-04-04T00:00:00+00:00",
    }))
    info_skill("my-skill", install_dir)
    out = capsys.readouterr().out
    assert "foo/bar" in out
    assert "abc123def456" in out
    assert "2026-04-04" in out


def test_info_skill_not_installed(tmp_path):
    with pytest.raises(FileNotFoundError, match="not installed"):
        info_skill("nonexistent", tmp_path / "skills")


def test_remove_skill(tmp_path, capsys):
    install_dir = tmp_path / "skills"
    (install_dir / "my-skill").mkdir(parents=True)
    (install_dir / "my-skill" / "SKILL.md").write_text("content")

    remove_skill("my-skill", install_dir)
    assert not (install_dir / "my-skill").exists()
    assert "Removed" in capsys.readouterr().out


def test_remove_skill_not_installed(tmp_path):
    with pytest.raises(FileNotFoundError, match="not installed"):
        remove_skill("nonexistent", tmp_path / "skills")


def test_update_skill_single(tmp_path, capsys):
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
            install_dir, cache_dir,
        )
        (remote / "skills" / "my-skill" / "SKILL.md").write_text("v2")
        subprocess.run(["git", "add", "."], cwd=remote, check=True, capture_output=True)
        subprocess.run(["git", "-c", "user.email=t@t.com", "-c", "user.name=T",
                        "commit", "-m", "update"], cwd=remote, check=True, capture_output=True)

        capsys.readouterr()
        update_skill("my-skill", install_dir, cache_dir)
        out = capsys.readouterr().out
        assert "updated" in out
        assert (install_dir / "my-skill" / "SKILL.md").read_text() == "v2"
    finally:
        skill_installer._clone_url = original
