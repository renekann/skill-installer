# skill-installer

**Claude Code** supports custom skills — Markdown files that teach Claude how to approach specific tasks (code reviews, standups, debugging workflows, and more). Skills live in a local directory and are picked up automatically when you start a session.

`skill-installer` is a CLI tool that fetches skills from GitHub and installs them into your skills directory. You point it at a GitHub URL, it clones the repo locally, copies the skill folder, and writes a metadata file so the tool knows where the skill came from. When a skill author pushes an update, one command brings all your skills up to date.

**You need this if you want to:**
- Install skills shared by others without manually cloning repos and copying folders
- Keep installed skills in sync with their upstream sources
- Manage skills from multiple GitHub repos through a single tool

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

### Config file (recommended)

Create `~/.skill-installer/config` with `KEY=VALUE` entries. Lines starting with `#` are ignored.

```
SKILL_INSTALL_DIR=~/.claude/skills
SKILL_CACHE_DIR=~/.skill-installer/repos
```

### Environment variables

Env vars take precedence over the config file.

```bash
export SKILL_INSTALL_DIR=~/my-skills
skill-install https://github.com/...
```

### Defaults

| Variable | Default |
|----------|---------|
| `SKILL_INSTALL_DIR` | `~/.claude/skills` |
| `SKILL_CACHE_DIR` | `~/.skill-installer/repos` |

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
