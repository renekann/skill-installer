# Changelog

All notable changes to skill-installer are documented here.

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
