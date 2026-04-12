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


def test_blob_at_repo_root_skill_file():
    url = "https://github.com/foo/bar/blob/main/SKILL.md"
    result = parse_github_url(url)
    assert result == {
        "owner": "foo",
        "repo": "bar",
        "ref": "main",
        "path": ".",
        "skill_name": "bar",
    }


def test_raw_at_repo_root_skill_file():
    url = "https://raw.githubusercontent.com/foo/bar/main/SKILL.md"
    result = parse_github_url(url)
    assert result == {
        "owner": "foo",
        "repo": "bar",
        "ref": "main",
        "path": ".",
        "skill_name": "bar",
    }


def test_path_traversal_in_url_raises():
    with pytest.raises(ValueError, match="must not contain '\\.\\.'"):
        parse_github_url("https://github.com/foo/bar/tree/main/skills/../../.ssh")


def test_path_traversal_raw_url_raises():
    with pytest.raises(ValueError, match="must not contain '\\.\\.'"):
        parse_github_url("https://raw.githubusercontent.com/foo/bar/main/skills/../../../etc/SKILL.md")


import subprocess as _subprocess
import sys as _sys


def test_load_config_reads_key_value(tmp_path, monkeypatch):
    import skill_installer
    config_file = tmp_path / "config"
    config_file.write_text("SKILL_INSTALL_DIR=/tmp/myskills\n# comment\nSKILL_CACHE_DIR=/tmp/cache\n\n")
    monkeypatch.setattr(skill_installer, "CONFIG_FILE", config_file)
    monkeypatch.delenv("SKILL_INSTALL_DIR", raising=False)
    monkeypatch.delenv("SKILL_CACHE_DIR", raising=False)
    config = skill_installer.load_config()
    assert config["SKILL_INSTALL_DIR"] == "/tmp/myskills"
    assert config["SKILL_CACHE_DIR"] == "/tmp/cache"


def test_load_config_env_takes_precedence(tmp_path, monkeypatch):
    import skill_installer
    config_file = tmp_path / "config"
    config_file.write_text("SKILL_INSTALL_DIR=/tmp/from-file\n")
    monkeypatch.setattr(skill_installer, "CONFIG_FILE", config_file)
    monkeypatch.setenv("SKILL_INSTALL_DIR", "/tmp/from-env")
    config = skill_installer.load_config()
    assert "SKILL_INSTALL_DIR" not in config


def test_load_config_missing_file(tmp_path, monkeypatch):
    import skill_installer
    monkeypatch.setattr(skill_installer, "CONFIG_FILE", tmp_path / "nonexistent")
    config = skill_installer.load_config()
    assert config == {}


def test_version_flag():
    result = _subprocess.run(
        [_sys.executable, "/Users/rene/dev/skill-installer/skill_installer.py", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "ski" in output
