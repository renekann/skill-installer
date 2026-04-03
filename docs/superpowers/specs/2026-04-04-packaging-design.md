# Packaging — Design Doc

**Date:** 2026-04-04
**Status:** Approved

## Overview

Add PyPI and Homebrew distribution to `renekann/skill-installer`. A single GitHub Action on tag push handles both: publishing to PyPI and auto-updating the Homebrew tap formula.

## Install Commands (end state)

```bash
# pipx (recommended)
pipx install skill-installer

# pip
pip install skill-installer

# Homebrew
brew tap renekann/skill-installer
brew install skill-installer
```

## Files Changed / Created

### In `renekann/skill-installer`

| File | Change |
|------|--------|
| `pyproject.toml` | New — package metadata, entry point, hatchling build |
| `skill_installer.py` | Add `--version` flag via `importlib.metadata` |
| `.github/workflows/publish.yml` | New — publish to PyPI + update tap on tag push |
| `README.md` | Add install instructions section |

### New repo `renekann/homebrew-skill-installer`

| File | Description |
|------|-------------|
| `Formula/skill-installer.rb` | Homebrew formula referencing GitHub release tarball |

## pyproject.toml

```toml
[project]
name = "skill-installer"
version = "0.1.0"
description = "Install Claude Code skills from GitHub"
requires-python = ">=3.9"
dependencies = []

[project.scripts]
skill-install = "skill_installer:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

No external dependencies. Entry point maps `skill-install` binary to `skill_installer:main`.

## --version Flag

Add to `skill_installer.py` after existing imports:

```python
from importlib.metadata import version as _pkg_version, PackageNotFoundError

try:
    __version__ = _pkg_version("skill-installer")
except PackageNotFoundError:
    __version__ = "dev"
```

Add to argparse in `main()`:
```python
parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
```

When run from git checkout (not installed), version shows `dev`.

## GitHub Action: publish.yml

Triggered on `push` to tags matching `v*`.

**Job 1 — pypi:**
- Uses PyPI Trusted Publishers (OIDC) — no API token stored as secret
- Builds with `python -m build`
- Publishes via `pypa/gh-action-pypi-publish@release/v1`
- Requires environment `release` configured in GitHub repo settings

**Job 2 — homebrew** (runs after pypi):
- Computes sha256 of the GitHub release tarball
- Updates `Formula/skill-installer.rb` in `renekann/homebrew-skill-installer` via GitHub API commit
- Requires `TAP_GITHUB_TOKEN` secret (PAT with `contents:write` on tap repo)

## Homebrew Formula

Lives in `renekann/homebrew-skill-installer/Formula/skill-installer.rb`.

```ruby
class SkillInstaller < Formula
  desc "Install Claude Code skills from GitHub"
  homepage "https://github.com/renekann/skill-installer"
  url "https://github.com/renekann/skill-installer/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "PLACEHOLDER_UPDATED_BY_CI"
  version "0.1.0"
  license "MIT"

  depends_on "python3"

  def install
    bin.install "skill_installer.py" => "skill-install"
  end

  test do
    system "#{bin}/skill-install", "--version"
  end
end
```

The `url`, `sha256`, and `version` fields are automatically updated by the GitHub Action on each release.

## Release Flow

```
git tag v0.2.0
git push origin v0.2.0
  → Action builds + publishes to PyPI
  → Action computes sha256 of tarball
  → Action commits updated formula to homebrew-skill-installer
```

Users then get the new version via:
```bash
pipx upgrade skill-installer
brew upgrade skill-installer
```

## Manual One-Time Setup (by you)

1. **Create `renekann/homebrew-skill-installer`** repo on GitHub with `Formula/` directory
2. **PyPI Trusted Publisher**: on pypi.org → Publishing → Add publisher → GitHub → repo: `skill-installer`, workflow: `publish.yml`, environment: `release`
3. **GitHub Secret**: in `skill-installer` repo settings → Secrets → `TAP_GITHUB_TOKEN` (PAT with `contents:write` on homebrew repo)
4. **GitHub Environment**: in `skill-installer` repo settings → Environments → create `release`
