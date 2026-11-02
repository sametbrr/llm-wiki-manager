# llm-wiki-manager — agent guide

Agent Skill + plugin (Claude Code and Codex) for a Karpathy-style LLM-managed markdown wiki.

## Layout
- `skills/llm-wiki-manager/SKILL.md`: mode router. `references/` holds one workflow per mode; `assets/templates/` holds the page templates; `scripts/` holds five stdlib-only Python scripts plus `schema_file.py` (AGENTS.md/CLAUDE.md detection).
- `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`: keep `version` identical in both and in SKILL.md `metadata.version`.
- `tests/test_scripts.py`: functional tests that run every script against temp wikis.

## Rules
- Scripts stay Python stdlib only, idempotent, and take `--path <wiki-root>`. Never hardcode `CLAUDE.md`; go through `schema_file.resolve_schema_file`.
- A structural convention change bumps `EXPECTED_SCHEMA_VERSION` in `migrate_wiki.py` and adds a migration step.
- Host-neutral wording; no `~/.claude/...` paths in skill text.
- Update `CHANGELOG.md` and both READMEs (EN + TR mirror) with every version bump.
- Never commit or push without explicit approval from the maintainer.

## Checks
- `python3 -m unittest discover -s tests`
- `claude plugin validate .`
- Codex: install from a local marketplace in an isolated `CODEX_HOME`; `llm-wiki-manager:llm-wiki-manager` must appear in `codex debug prompt-input`.
