# skill-installer — Claude Instructions

## What this project is

A Python CLI tool (`skill_installer.py`) that installs Claude Code skills from GitHub URLs. Single-file, stdlib-only, no external runtime dependencies.

## Key files

| File | Purpose |
|------|---------|
| `skill_installer.py` | Entire implementation — URL parser, git cache, install/update/purge, CLI |
| `pyproject.toml` | Package metadata, version, PyPI entry point |
| `tests/test_url_parser.py` | URL parsing unit tests |
| `tests/test_installer.py` | Integration tests using real temp git repos |
| `.github/workflows/publish.yml` | CI: publish to PyPI + update Homebrew formula on tag push |
| `CHANGELOG.md` | Release history — MUST be updated before every release |

## Architecture

- `parse_github_url(url)` — parses blob/tree/raw GitHub URLs into owner/repo/ref/path/skill_name
- `_clone_url(owner, repo)` — returns clone URL, extracted for test patching
- `ensure_repo_cached(owner, repo, cache_dir)` — shallow clone or fetch+reset
- `get_current_ref(repo_path)` — returns HEAD SHA
- `pull_repo(repo_path)` — fetch+reset, returns (old_ref, new_ref)
- `install_skill(url, install_dir, cache_dir)` — copies folder, writes `.skill-source.json`
- `update_all(install_dir, cache_dir)` — scans metadata, pulls once per repo, re-copies
- `purge_cache(cache_dir)` — deletes cache dir
- `_validate_metadata_path(value, field)` — prevents path traversal from metadata files
- `main()` — argparse CLI entry point

## Config (env vars)

| Var | Default |
|-----|---------|
| `SKILL_INSTALL_DIR` | `~/Documents/claude-config/skills` |
| `SKILL_CACHE_DIR` | `~/.skill-installer/repos` |

## Testing

Tests use real temp git repos — no subprocess mocks.

```bash
python3 -m pytest tests/ -v
```

All tests must pass before committing. Test output must be clean (no warnings treated as errors yet, but keep output tidy).

## Release process

Follow these steps exactly when releasing a new version:

1. **Update `CHANGELOG.md`** — add a new section `## [x.y.z] - YYYY-MM-DD` with bullet points under `### Added`, `### Changed`, `### Fixed`, or `### Removed` as applicable. Every release needs a changelog entry.
2. **Bump version** in `pyproject.toml` (`version = "x.y.z"`)
3. **Run tests**: `python3 -m pytest tests/ -v` — must all pass
4. **Commit**: `git add CHANGELOG.md pyproject.toml && git commit -m "chore: release vx.y.z"`
5. **Push**: `git push origin main`
6. **Tag**: `git tag vx.y.z && git push origin vx.y.z`

The GitHub Action then automatically:
- Builds and publishes to PyPI
- Updates the Homebrew formula sha256 in `renekann/homebrew-skill-installer`

## Coding conventions

- Single file — do not split into modules
- Stdlib only — no new runtime dependencies
- All subprocess git calls use list form `["git", ...]`, never shell strings
- `_run_git()` is the only place to call git — everything else calls it
- Tests monkey-patch `_clone_url` with try/finally to avoid hitting GitHub

## Distribution

- **PyPI**: `pipx install skill-installer` / `pip install skill-installer`
- **Homebrew**: `brew tap renekann/skill-installer && brew install skill-installer`
- **Tap repo**: `renekann/homebrew-skill-installer` (formula auto-updated by CI)

## Secrets (in renekann/skill-installer GitHub repo)

- `TAP_GITHUB_TOKEN` — PAT with `contents:write` on `homebrew-skill-installer`
- PyPI auth via Trusted Publishers (OIDC, no stored secret)
- GitHub environment `release` must exist for the PyPI job to run
