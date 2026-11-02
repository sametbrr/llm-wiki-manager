#!/usr/bin/env python3
"""Functional tests for the llm-wiki-manager scripts. Run: python3 -m unittest discover -s tests"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "llm-wiki-manager" / "scripts"


def run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPTS / script), *args],
        capture_output=True, text=True, check=False,
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


class InitTests(unittest.TestCase):
    def test_fresh_wiki_gets_agents_md_and_claude_pointer(self):
        with tempfile.TemporaryDirectory() as d:
            r = run("init_wiki.py", "--path", d, "--name", "T", "--topic", "t", "--quiet")
            self.assertEqual(r.returncode, 0, r.stderr)
            root = Path(d)
            self.assertTrue((root / "AGENTS.md").exists())
            self.assertEqual((root / "CLAUDE.md").read_text(), "@AGENTS.md\n")
            self.assertIn("AGENTS.md", (root / "README.md").read_text())
            self.assertTrue((root / "wiki" / "index.md").exists())

    def test_existing_claude_md_is_kept(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root / "CLAUDE.md", "# My schema\n")
            r = run("init_wiki.py", "--path", d, "--quiet")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((root / "AGENTS.md").exists())
            self.assertEqual((root / "CLAUDE.md").read_text(), "# My schema\n")

    def test_schema_file_override(self):
        with tempfile.TemporaryDirectory() as d:
            r = run("init_wiki.py", "--path", d, "--schema-file", "SCHEMA.md", "--quiet")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((Path(d) / "SCHEMA.md").exists())
            self.assertFalse((Path(d) / "CLAUDE.md").exists())


OBSIDIAN_INDEX = """
# Index

Intro paragraph with [[hot]].

## Reports
- [Lint 2026-10-12](reports/lint-2026-10-12.md) — health pass

## Claude & Anthropic
- [[anthropic-claude-ecosystem]] ★ — hub page `#sitemap`
- [[agent-skills-standard]] — the standard `#claude-skill`

## Open Source (Samet)
- [[skill-hub]] ★ — marketplace

## Meta
- [[overview]] — synthesis
"""


class UpdateIndexTests(unittest.TestCase):
    def make_obsidian(self, d: str) -> Path:
        root = Path(d)
        write(root / "wiki" / "index.md", OBSIDIAN_INDEX)
        for slug in ["anthropic-claude-ecosystem", "agent-skills-standard", "skill-hub", "overview", "hot", "codex-plugins"]:
            write(root / "wiki" / "general" / f"{slug}.md", f"# {slug}\n")
        write(root / "wiki" / "reports" / "lint-2026-10-12.md", "# lint\n")
        return root

    def index(self, root: Path) -> str:
        return (root / "wiki" / "index.md").read_text()

    def test_case_insensitive_category_keeps_heading_and_wikilink_style(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.make_obsidian(d)
            r = run("update_index.py", "--path", d, "--category", "claude & anthropic",
                    "--title", "Codex plugins", "--page-path", "wiki/general/codex-plugins.md",
                    "--summary", "Codex plugin format")
            self.assertEqual(r.returncode, 0, r.stderr)
            text = self.index(root)
            self.assertNotIn("## Claude & anthropic", text)
            self.assertEqual(text.count("## Claude & Anthropic"), 1)
            self.assertIn("- [[codex-plugins|Codex plugins]] — Codex plugin format", text)
            # Inserted inside the existing section, before Open Source.
            self.assertLess(text.index("codex-plugins"), text.index("## Open Source (Samet)"))

    def test_new_category_goes_before_meta_and_keeps_casing(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.make_obsidian(d)
            r = run("update_index.py", "--path", d, "--category", "AI Tools",
                    "--title", "codex-plugins", "--page-path", "wiki/general/codex-plugins.md",
                    "--summary", "x")
            self.assertEqual(r.returncode, 0, r.stderr)
            text = self.index(root)
            self.assertIn("## AI Tools", text)
            self.assertLess(text.index("## AI Tools"), text.index("## Meta"))
            self.assertIn("- [[codex-plugins]] — x", text)
            self.assertIn("Intro paragraph with [[hot]].", text)

    def test_update_keeps_hub_mark_and_summary(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.make_obsidian(d)
            r = run("update_index.py", "--path", d, "--category", "Open Source (Samet)",
                    "--title", "skill-hub", "--page-path", "wiki/general/skill-hub.md")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Index updated", r.stdout)
            text = self.index(root)
            self.assertIn("- [[skill-hub]] ★ — marketplace", text)
            self.assertEqual(text.count("skill-hub"), 1)

    def test_rerun_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.make_obsidian(d)
            args = ("--path", d, "--category", "Meta", "--title", "overview",
                    "--page-path", "wiki/general/overview.md", "--summary", "synthesis")
            run("update_index.py", *args)
            first = self.index(root)
            run("update_index.py", *args)
            self.assertEqual(first, self.index(root))

    def test_markdown_style_on_fresh_wiki(self):
        with tempfile.TemporaryDirectory() as d:
            run("init_wiki.py", "--path", d, "--quiet")
            write(Path(d) / "wiki" / "concepts" / "nutritionism.md", "# N\n")
            r = run("update_index.py", "--path", d, "--category", "concepts", "--title", "Nutritionism",
                    "--page-path", "wiki/concepts/nutritionism.md", "--summary", "s")
            self.assertEqual(r.returncode, 0, r.stderr)
            text = (Path(d) / "wiki" / "index.md").read_text()
            self.assertIn("- [Nutritionism](concepts/nutritionism.md) — s", text)
            self.assertEqual(text.count("## Concepts"), 1)

    def test_duplicate_in_other_category_warns(self):
        with tempfile.TemporaryDirectory() as d:
            self.make_obsidian(d)
            r = run("update_index.py", "--path", d, "--category", "Meta", "--title", "skill-hub",
                    "--page-path", "wiki/general/skill-hub.md", "--summary", "dup")
            self.assertIn("already indexed under 'Open Source (Samet)'", r.stderr)


class LintTests(unittest.TestCase):
    def test_anchor_and_embed_links_are_not_broken_but_dead_index_wikilink_is(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run("init_wiki.py", "--path", d, "--quiet")
            write(root / "wiki" / "notes" / "a.md", """
                # A
                See [[b#Section]], [[b#^block|alias]], [[#Local]] and ![[pic.png]].
                Broken: [[nowhere]].
                Code is not a link: `[[codeonly]]` and

                ```
                [[fenced]] [x](missing.md)
                ```
                """)
            write(root / "wiki" / "notes" / "b.md", "# B\nBack to [[a]].\n")
            (root / "raw").mkdir(exist_ok=True)
            (root / "raw" / "pic.png").write_bytes(b"\x89PNG")
            with open(root / "wiki" / "index.md", "a", encoding="utf-8") as f:
                f.write("\n## Notes\n- [[a]] — a\n- [[b]] — b\n- [[ghost]] — missing page\n")
            r = run("lint_wiki.py", "--path", d, "--stdout")
            self.assertEqual(r.returncode, 1, r.stderr)  # block findings -> exit 1
            out = r.stdout
            self.assertIn("- `[[ghost]]`", out)
            self.assertIn("nowhere", out)
            self.assertIn("ghost", out)
            self.assertNotIn("b#", out)
            self.assertNotIn("pic.png", out)
            self.assertNotIn("Local", out)
            self.assertNotIn("codeonly", out)
            self.assertNotIn("fenced", out)

    def test_schema_version_read_from_agents_md(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run("init_wiki.py", "--path", d, "--quiet")
            (root / "AGENTS.md").write_text("---\nschema_version: 1\n---\n# S\n")
            r = run("lint_wiki.py", "--path", d, "--stdout")
            self.assertIn("schema v1", r.stdout)


class MigrateTests(unittest.TestCase):
    def test_stamps_agents_md_when_claude_md_is_a_pointer(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run("init_wiki.py", "--path", d, "--quiet")
            (root / "AGENTS.md").write_text("# Schema without stamp\n")
            r = run("migrate_wiki.py", "--path", d, "--apply")
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertIn("schema_version: 2", (root / "AGENTS.md").read_text())
            self.assertEqual((root / "CLAUDE.md").read_text(), "@AGENTS.md\n")
            r2 = run("migrate_wiki.py", "--path", d)
            self.assertIn("no-op", r2.stdout)


if __name__ == "__main__":
    unittest.main()
