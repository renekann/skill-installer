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
