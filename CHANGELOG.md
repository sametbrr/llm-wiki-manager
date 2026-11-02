# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2026-11-02

### Changed
- Plugin layout: the skill moved to `skills/llm-wiki-manager/` (scripts, references and assets with it) so Codex discovers it. The Claude Code skill ID is unchanged. **Scripts now live at `<plugin>/skills/llm-wiki-manager/scripts/`**: update any hardcoded script paths.
- Schema file is host-neutral: every script auto-detects `AGENTS.md` or `CLAUDE.md` (`--schema-file` overrides). New wikis get `AGENTS.md` plus a one-line `CLAUDE.md` (`@AGENTS.md`), so Claude Code and Codex load the same schema.
- `update_index.py` rewritten:
  - case-insensitive category match that keeps the existing heading spelling;
  - section order and content (blank lines, prose) preserved;
  - new categories go before `## Meta` (`--tail`);
  - link style follows the index, markdown or `[[wikilinks]]` (`--link-style`);
  - `★` hub marks and old summaries kept on update.
- Agent-neutral wording; multi-wiki examples use skill-relative script paths instead of `~/.claude/skills/...`.

### Added
- `.codex-plugin/plugin.json` (Codex plugin), `AGENTS.md`, `version` in both manifests.
- `tests/test_scripts.py`: functional tests for init, update_index, lint and migrate.

### Fixed
- `lint_wiki.py`: links inside inline code and fenced code blocks are examples, not links, and are no longer checked. `[[page#heading]]`, `[[page#^block]]`, `[[#local]]` and `![[embed.png]]` are no longer reported as broken; dead `[[slug]]` entries in the index are now reported instead of silently ignored.
- Release workflow reads the version from `.claude-plugin/plugin.json`, checks the Codex manifest matches, and passes notes via `--notes-file`. Commit text is no longer interpolated into shell.
- SKILL.md said "four" scripts (there are five); README said 8 modes (there are 9). The README's `.skill` download option pointed to a release asset that never existed and was removed.

## [1.4.0] - 2026-06-10

### Added
- `scripts/migrate_wiki.py` — schema upgrade tool (v1 → v2): deduplicates `index.md`, moves dated changelog blocks from `hot.md` into `log.md`, stamps `schema_version` in the wiki's `CLAUDE.md`. Dry-run by default, applies with `--apply`. Idempotent.
- `references/migrate-workflow.md` — full migrate workflow documentation.
- Lint expansion: broken-link detection for markdown and `[[wiki-link]]` formats, duplicate index entries, hot.md bloat, tag hygiene (single-use tags, over-tagged pages), ambiguous wiki-link slugs, log gaps, and schema-version drift.
- Schema version check (Step 0) in every operating mode — offers migration when the wiki is behind the expected schema.

### Changed
- Template revisions for clearer `hot.md` structure (changelog history now lives in `log.md`).
- Lint thresholds configurable via `--stub-words`, `--log-gap-days`, `--hot-max-words`, `--max-tags`.

### Fixed
- README counts corrected (5 scripts, 11 reference docs); `migrate_wiki.py` added to the script table in both READMEs.
- `lint_wiki.py`: script directory is put on `sys.path` so the `migrate_wiki` import works when invoked from any cwd; frontmatter parser exception handling narrowed.
- `migrate_wiki.py`: the `hot.md` → `log.md` move now verifies the full block content on disk before deleting from `hot.md`.

## [1.3.0] - 2026-05-31

### Added
- Turkish README (`README.tr.md`).

### Changed
- Restructured main `README.md`.
- Removed outdated related-projects section from README.

## [1.2.1] - 2026-05-21

### Added
- CI: auto-release workflow on SKILL.md version bump (`.github/workflows/release.yml`).

## [1.2.0] - 2026-05-21

### Added
- `hot.md` hot cache — most recently ingested sources and active references.
- Obsidian wiki-link (`[[...]]`) support in lint and index handling.

### Changed
- Script improvements: flexible log/index path detection in both `wiki/` and root layouts.

## [1.1.0] - 2026-05-07

### Added
- Multi-wiki routing with safeguards — routes writes between a project wiki and a global wiki via the `External Wiki:` declaration in the project `CLAUDE.md`.
- `references/multi-wiki-routing.md` with four canonical scenarios.
- Discoverability improvements (release badge, installation instructions).

## [1.0.0] - 2026-05-07

### Added
- Initial release: Bootstrap, Ingest, Query, Update, Lint, Schema-evolve, and Teach modes.
- Scripts: `init_wiki.py`, `append_log.py`, `update_index.py`, `lint_wiki.py` (Python stdlib only, idempotent).
- 8 page templates and core reference documentation.

[1.4.0]: https://github.com/sametbrr/llm-wiki-manager/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/sametbrr/llm-wiki-manager/compare/v1.2.1...v1.3.0
[1.2.1]: https://github.com/sametbrr/llm-wiki-manager/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/sametbrr/llm-wiki-manager/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/sametbrr/llm-wiki-manager/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/sametbrr/llm-wiki-manager/releases/tag/v1.0.0
