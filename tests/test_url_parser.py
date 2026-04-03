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
