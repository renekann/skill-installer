# Packaging (PyPI + Homebrew) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make skill-installer installable via `pipx install skill-installer` and `brew install renekann/skill-installer/skill-installer`, with a GitHub Action that auto-publishes on tag push.

**Architecture:** Add `pyproject.toml` for PyPI packaging and a `--version` flag to the script. A single GitHub Action on `v*` tags publishes to PyPI via Trusted Publishers (OIDC) and commits an updated sha256 into the Homebrew tap formula. The tap lives in a separate repo `renekann/homebrew-skill-installer`.

**Tech Stack:** Python hatchling (build), PyPI Trusted Publishers (OIDC), GitHub Actions, Homebrew Ruby formula, `gh` CLI.

---

### Task 1: pyproject.toml + --version flag

**Files:**
- Create: `pyproject.toml`
- Modify: `skill_installer.py` (add `__version__`, add `--version` to argparse)
- Modify: `tests/test_url_parser.py` (add version flag test)

- [ ] **Step 1: Write failing test for --version flag**

Append to `tests/test_url_parser.py`:

```python
import subprocess as _subprocess
import sys as _sys


def test_version_flag():
    result = _subprocess.run(
        [_sys.executable, "/Users/rene/dev/skill-installer/skill_installer.py", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    # output contains prog name and a version string
    output = result.stdout + result.stderr  # argparse may use either
    assert "skill-install" in output
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /Users/rene/dev/skill-installer && python3 -m pytest tests/test_url_parser.py::test_version_flag -v
```
Expected: FAILED — argparse exits with error 2 (unrecognised argument `--version`).

- [ ] **Step 3: Create `pyproject.toml`**

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

- [ ] **Step 4: Add `__version__` and `--version` to `skill_installer.py`**

Add after the existing imports (after `from urllib.parse import urlparse`), before `DEFAULT_INSTALL_DIR`:

```python
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("skill-installer")
except PackageNotFoundError:
    __version__ = "dev"
```

In `main()`, add `--version` to the parser — insert after `parser = argparse.ArgumentParser(...)` block, before `group = parser.add_mutually_exclusive_group(...)`:

```python
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
```

No other changes needed. Argparse's `version` action calls `sys.exit(0)` before the required-group check fires, so `required=True` on the group is unaffected. The `else: parser.print_help()` branch already exists in the current code.

- [ ] **Step 5: Run test to confirm it passes**

```bash
cd /Users/rene/dev/skill-installer && python3 -m pytest tests/test_url_parser.py::test_version_flag -v
```
Expected: PASSED. Output will contain `skill-install dev` (not installed as package yet).

- [ ] **Step 6: Run full test suite**

```bash
cd /Users/rene/dev/skill-installer && python3 -m pytest tests/ -v
```
Expected: all 17 tests PASS.

- [ ] **Step 7: Verify build works**

```bash
cd /Users/rene/dev/skill-installer && pip install build hatchling --quiet && python3 -m build --wheel --outdir /tmp/skill-installer-dist/
```
Expected: `Successfully built skill_installer-0.1.0-py3-none-any.whl` in `/tmp/skill-installer-dist/`.

- [ ] **Step 8: Commit**

```bash
command git -C /Users/rene/dev/skill-installer add pyproject.toml skill_installer.py tests/test_url_parser.py
command git -C /Users/rene/dev/skill-installer commit -m "feat: add pyproject.toml and --version flag"
```

---

### Task 2: GitHub Actions publish workflow

**Files:**
- Create: `.github/workflows/publish.yml`

No unit tests — validate by checking YAML syntax.

- [ ] **Step 1: Create `.github/workflows/` directory**

```bash
mkdir -p /Users/rene/dev/skill-installer/.github/workflows
```

- [ ] **Step 2: Create `.github/workflows/publish.yml`**

```yaml
name: Publish

on:
  push:
    tags:
      - 'v*'

jobs:
  pypi:
    name: Publish to PyPI
    runs-on: ubuntu-latest
    environment: release
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Build package
        run: |
          pip install build hatchling
          python -m build

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1

  homebrew:
    name: Update Homebrew tap
    runs-on: ubuntu-latest
    needs: pypi
    steps:
      - name: Compute sha256 of release tarball
        id: meta
        run: |
          VERSION="${GITHUB_REF_NAME#v}"
          URL="https://github.com/renekann/skill-installer/archive/refs/tags/${GITHUB_REF_NAME}.tar.gz"
          SHA=$(curl -sL "$URL" | sha256sum | cut -d' ' -f1)
          echo "version=$VERSION" >> "$GITHUB_OUTPUT"
          echo "url=$URL" >> "$GITHUB_OUTPUT"
          echo "sha=$SHA" >> "$GITHUB_OUTPUT"

      - name: Update formula in tap repo
        uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.TAP_GITHUB_TOKEN }}
          script: |
            const owner = 'renekann';
            const repo = 'homebrew-skill-installer';
            const path = 'Formula/skill-installer.rb';
            const version = '${{ steps.meta.outputs.version }}';
            const sha = '${{ steps.meta.outputs.sha }}';
            const url = '${{ steps.meta.outputs.url }}';

            const { data: file } = await github.rest.repos.getContent({ owner, repo, path });
            let content = Buffer.from(file.content, 'base64').toString();

            content = content.replace(/url ".*"/, `url "${url}"`);
            content = content.replace(/sha256 ".*"/, `sha256 "${sha}"`);
            content = content.replace(/version ".*"/, `version "${version}"`);

            await github.rest.repos.createOrUpdateFileContents({
              owner, repo, path,
              message: `chore: update to v${version}`,
              content: Buffer.from(content).toString('base64'),
              sha: file.sha,
            });
```

- [ ] **Step 3: Validate YAML syntax**

```bash
python3 -c "
import yaml, sys
with open('/Users/rene/dev/skill-installer/.github/workflows/publish.yml') as f:
    yaml.safe_load(f)
print('YAML valid')
" 2>/dev/null || pip install pyyaml --quiet && python3 -c "
import yaml
with open('/Users/rene/dev/skill-installer/.github/workflows/publish.yml') as f:
    yaml.safe_load(f)
print('YAML valid')
"
```
Expected: `YAML valid`

- [ ] **Step 4: Commit**

```bash
command git -C /Users/rene/dev/skill-installer add .github/
command git -C /Users/rene/dev/skill-installer commit -m "ci: add PyPI + Homebrew tap publish workflow"
```

---

### Task 3: Homebrew tap repo + initial formula

**Files (in new repo `renekann/homebrew-skill-installer`):**
- Create: `Formula/skill-installer.rb`

- [ ] **Step 1: Create the tap repo on GitHub**

```bash
gh repo create renekann/homebrew-skill-installer --public --description "Homebrew tap for skill-installer"
```
Expected: repo created at `https://github.com/renekann/homebrew-skill-installer`

- [ ] **Step 2: Clone the new tap repo**

```bash
command git clone git@github.com:renekann/homebrew-skill-installer.git /tmp/homebrew-skill-installer
```

- [ ] **Step 3: Create `Formula/skill-installer.rb`**

```bash
mkdir -p /tmp/homebrew-skill-installer/Formula
```

Write `/tmp/homebrew-skill-installer/Formula/skill-installer.rb`:

```ruby
class SkillInstaller < Formula
  desc "Install Claude Code skills from GitHub"
  homepage "https://github.com/renekann/skill-installer"
  url "https://github.com/renekann/skill-installer/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
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

Note: the sha256 placeholder `000...` will be replaced automatically by the publish workflow on the first `v0.1.0` tag push.

- [ ] **Step 4: Commit and push formula**

```bash
cd /tmp/homebrew-skill-installer
command git config user.email "rene@example.com"
command git config user.name "René Kann"
command git add Formula/skill-installer.rb
command git commit -m "feat: add skill-installer formula"
command git push origin main
```

- [ ] **Step 5: Verify tap repo on GitHub**

```bash
gh repo view renekann/homebrew-skill-installer
```
Expected: repo visible with `Formula/skill-installer.rb`.

---

### Task 4: README install instructions

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace the Setup section in `README.md`**

Replace the existing `## Setup` section:

```markdown
## Setup

### pipx (recommended)

```bash
pipx install skill-installer
```

### Homebrew

```bash
brew tap renekann/skill-installer
brew install skill-installer
```

### pip

```bash
pip install skill-installer
```

### Manual (symlink)

```bash
git clone https://github.com/renekann/skill-installer.git
chmod +x skill-installer/skill_installer.py
ln -s "$PWD/skill-installer/skill_installer.py" /usr/local/bin/skill-install
```
```

- [ ] **Step 2: Verify README renders correctly**

```bash
cat /Users/rene/dev/skill-installer/README.md | head -40
```

- [ ] **Step 3: Commit**

```bash
command git -C /Users/rene/dev/skill-installer add README.md
command git -C /Users/rene/dev/skill-installer commit -m "docs: add pipx and Homebrew install instructions"
```

---

### Task 5: First release — v0.1.0

**Pre-flight checklist (manual steps you must complete before this task):**

1. **PyPI account**: create account at https://pypi.org if you don't have one
2. **PyPI Trusted Publisher**: go to pypi.org → Your account → Publishing → Add a new publisher
   - PyPI project name: `skill-installer`
   - Owner: `renekann`
   - Repository: `skill-installer`
   - Workflow filename: `publish.yml`
   - Environment: `release`
3. **GitHub environment**: go to github.com/renekann/skill-installer → Settings → Environments → New environment → name: `release`
4. **TAP_GITHUB_TOKEN**: create a GitHub PAT at github.com/settings/tokens with `contents:write` scope on `homebrew-skill-installer`, then add it as a secret in `skill-installer` repo Settings → Secrets → `TAP_GITHUB_TOKEN`

- [ ] **Step 1: Confirm all pre-flight steps are done**

Manually verify the 4 items above before continuing.

- [ ] **Step 2: Push all commits to GitHub**

```bash
command git -C /Users/rene/dev/skill-installer push origin main
```

- [ ] **Step 3: Tag and push v0.1.0**

```bash
command git -C /Users/rene/dev/skill-installer tag v0.1.0
command git -C /Users/rene/dev/skill-installer push origin v0.1.0
```

- [ ] **Step 4: Watch the Action run**

```bash
gh run watch --repo renekann/skill-installer
```
Expected: both jobs (`pypi` and `homebrew`) complete green.

- [ ] **Step 5: Verify PyPI package**

```bash
pip index versions skill-installer 2>/dev/null || pip install skill-installer==0.1.0 --dry-run
```
Expected: version `0.1.0` appears.

- [ ] **Step 6: Verify Homebrew formula updated**

```bash
gh api repos/renekann/homebrew-skill-installer/contents/Formula/skill-installer.rb \
  --jq '.content' | base64 -d | grep sha256
```
Expected: sha256 is no longer `000...` — it's a real 64-char hex hash.

- [ ] **Step 7: Smoke test pipx install**

```bash
pipx install skill-installer
skill-install --version
```
Expected: `skill-install 0.1.0`

- [ ] **Step 8: Smoke test Homebrew install**

```bash
brew tap renekann/skill-installer
brew install skill-installer
skill-install --version
```
Expected: `skill-install 0.1.0`
