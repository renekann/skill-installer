---
name: ski
description: Install, update, list, and remove Claude Code skills from GitHub with a single command. Use when managing Claude Code skills — installing from GitHub URLs, keeping skills up to date, or removing skills.
---

# ski — Claude Code Skill Installer

`ski` is a CLI tool that manages Claude Code skills from GitHub repositories. It clones repos locally, copies skill folders, tracks their origin in metadata, and can update all installed skills in one command.

## When to Use This Skill

Invoke this skill when a user asks to:
- Install a Claude Code skill from a GitHub URL
- Update installed skills to their latest version
- List, inspect, or remove installed skills
- Manage the local skill cache

## Commands

```bash
# Install a skill (supports blob, tree, and raw GitHub URLs)
ski https://github.com/owner/repo/blob/main/skills/skill-name/SKILL.md

# List all installed skills with their source repo
ski --list

# Show details (source URL, repo, ref, install date) for a skill
ski --info skill-name

# Update all installed skills to latest HEAD
ski -u

# Update a specific skill only
ski -u skill-name

# Remove an installed skill
ski --remove skill-name

# Clear the local git repo cache
ski --purge-cache
```

## Setup

```bash
# Homebrew (recommended)
brew tap renekann/skill-installer
brew install skill-installer

# pipx
pipx install skill-installer
```

## Configuration

Create `~/.skill-installer/config` to set defaults:

```
SKILL_INSTALL_DIR=~/.claude/skills
SKILL_CACHE_DIR=~/.skill-installer/repos
```

Source: https://github.com/renekann/skill-installer
