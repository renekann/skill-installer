# Skill Installer — Design Doc

**Date:** 2026-04-03
**Status:** Approved

## Overview

A single Python script (`skill_installer.py`) callable as a binary via symlink. Installs Claude Code skills from GitHub URLs into a local directory, tracks their origin in a metadata file, and supports bulk updates and cache management.

## CLI

```bash
skill-install <url>           # install a skill from a GitHub URL
skill-install --update-all    # update all installed skills to latest HEAD
skill-install --purge-cache   # delete the local git repo cache
```

## Configuration

| Env Var | Default |
|---------|---------|
| `SKILL_INSTALL_DIR` | `~/Documents/claude-config/skills` |
| `SKILL_CACHE_DIR` | `~/.skill-installer/repos` |

## Supported URL Formats

All three GitHub URL formats are supported:

- Blob: `https://github.com/{owner}/{repo}/blob/{ref}/path/to/SKILL.md`
- Tree: `https://github.com/{owner}/{repo}/tree/{ref}/path/to/folder`
- Raw: `https://raw.githubusercontent.com/{owner}/{repo}/{ref}/path/to/file`

For blob and raw URLs pointing to a file, the parent directory is used as the skill folder. The skill name is derived from the folder name in the path (e.g. `optimise-seo`).

## Architecture

### Local Git Cache

```
~/.skill-installer/repos/
  {owner}/
    {repo}/          ← shallow git clone of the repo
```

On install:
- If repo not in cache → `git clone --depth 1 https://github.com/{owner}/{repo} {cache_dir}`
- If repo already in cache → `git -C {cache_dir} fetch --depth 1 origin`

The skill folder is then copied from the cache into `SKILL_INSTALL_DIR/{skill_name}/`.

Rationale: multiple skills from the same repo share one clone; updates require only one `git pull` per repo regardless of how many skills were installed from it.

### Metadata File

Each installed skill gets a `.skill-source.json` written into its folder:

```json
{
  "source_url": "https://github.com/mblode/agent-skills/blob/bbb8ad4.../SKILL.md",
  "owner": "mblode",
  "repo": "agent-skills",
  "ref": "bbb8ad46d8c6b35e6944233f6d8abd19b69c7880",
  "path": "skills/optimise-seo",
  "installed_at": "2026-04-03T10:00:00Z",
  "updated_at": "2026-04-03T10:00:00Z"
}
```

This is the source of truth for `--update-all`. It is never overwritten by the skill content itself.

### Update Flow

1. Scan `SKILL_INSTALL_DIR` for all `.skill-source.json` files
2. Group by `owner/repo`
3. Per repo: `git -C {cache_dir} pull` (fetches latest `HEAD` of default branch)
4. Per skill: overwrite skill folder contents from updated cache (preserving `.skill-source.json`)
5. Update `ref` and `updated_at` in `.skill-source.json`
6. Report per skill: `updated` / `already up-to-date` / `failed`

### Cache Purge

`--purge-cache` deletes `SKILL_CACHE_DIR` entirely. Installed skills are not touched. The cache is rebuilt on next install or update.

## Error Handling

| Situation | Behavior |
|-----------|----------|
| Skill folder already exists | Abort with error, no partial writes |
| Unsupported URL format | Clear error message |
| `git` not found | Error: "git is required" |
| Network / git error | Error with original git output |

## Files

```
skill-installer/
  skill_installer.py    ← script with #!/usr/bin/env python3 shebang
  README.md
```

No external Python dependencies — only stdlib (`argparse`, `json`, `shutil`, `subprocess`, `pathlib`, `datetime`, `urllib.parse`).

## Symlink Setup (user, one-time)

```bash
chmod +x /path/to/skill_installer.py
ln -s /path/to/skill_installer.py /usr/local/bin/skill-install
```
