# Changelog

All notable changes to skill-installer are documented here.

## [0.1.8] - 2026-04-04

### Added
- `ski --list` / `ski -l` — list all installed skills with source repo and last update date; untracked skills shown without metadata
- `ski --remove <name>` — remove an installed skill
- `ski --info <name>` — show source URL, repo, path, ref, install and update dates for a skill
- `ski -u <name>` — update a single specific skill (without argument: update all)
- Short flag `-u` as alias for update (replaces `--update-all`); `--update-all` removed

## [0.1.7] - 2026-04-04

### Security
- Fix path traversal via `..` in URL path component — now raises `ValueError` in `parse_github_url()`
- Fix `shutil.copytree` following symlinks from cloned repos — `symlinks=True` prevents exfiltration of local files via malicious repos

## [0.1.6] - 2026-04-04

### Added
- `ski` alias — shorter command alongside `skill-install` (both work identically)

## [0.1.5] - 2026-04-04

### Fixed
- `--version` now shows the correct version when installed via Homebrew (reads `SKILL_INSTALLER_VERSION` env var injected by the Homebrew wrapper script)

## [0.1.4] - 2026-04-04

### Added
- GitHub Release is automatically created on tag push, using the matching CHANGELOG section as release notes

## [0.1.3] - 2026-04-04

### Added
- Config file support: `~/.skill-installer/config` with `KEY=VALUE` entries — env vars take precedence

### Changed
- Default `SKILL_INSTALL_DIR` changed from `~/Documents/claude-config/skills` to `~/.claude/skills`

## [0.1.2] - 2026-04-04

### Changed
- Expanded README intro with context, use cases, and explanation of what Claude Code skills are

## [0.1.1] - 2026-04-04

### Fixed
- PyPI project description was empty — added `readme = "README.md"` to `pyproject.toml`

## [0.1.0] - 2026-04-04

### Added
- `skill-install <url>` — install a skill from a GitHub blob, tree, or raw URL
- `skill-install --update-all` — update all installed skills to latest HEAD
- `skill-install --purge-cache` — delete the local git repo cache
- `skill-install --version` — show installed version
- Git-based local repo cache (`SKILL_CACHE_DIR`, default `~/.skill-installer/repos`)
- `.skill-source.json` metadata file written into each installed skill folder
- Configurable install directory via `SKILL_INSTALL_DIR` env var
- PyPI package (`pipx install skill-installer`)
- Homebrew tap (`brew tap renekann/skill-installer && brew install skill-installer`)
- GitHub Action: auto-publish to PyPI + update Homebrew formula on tag push
