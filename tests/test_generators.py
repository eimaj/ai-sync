"""Tests for agent-specific generators and skill syncing."""

import sys
from pathlib import Path

from tests.conftest import make_args, seed_manifest

mod = sys.modules["sync_agent_rules"]


class TestGenCursor:
    def test_creates_mdc_files(self, fake_home):
        seed_manifest(fake_home, rules=[
            ("rule-a", "# Rule A\nContent A.\n"),
            ("rule-b", "# Rule B\nContent B.\n"),
        ])
        manifest = mod.read_manifest()
        mod.gen_cursor(manifest, make_args())

        rules_dir = mod.AGENT_PATHS["cursor"]["rules_dir"]
        mdc_a = rules_dir / "rule-a.mdc"
        mdc_b = rules_dir / "rule-b.mdc"
        assert mdc_a.exists()
        assert mdc_b.exists()

        text = mdc_a.read_text()
        assert text.startswith("---")
        assert mod.GENERATED_HEADER in text
        assert "Content A." in text

    def test_stale_cleanup(self, fake_home):
        seed_manifest(fake_home, rules=[("rule-a", "# Rule A\nA.\n")])

        rules_dir = mod.AGENT_PATHS["cursor"]["rules_dir"]
        rules_dir.mkdir(parents=True, exist_ok=True)
        stale = rules_dir / "old-rule.mdc"
        stale.write_text("---\n---\n" + mod.GENERATED_HEADER + "\nStale content")

        manifest = mod.read_manifest()
        mod.gen_cursor(manifest, make_args())

        assert not stale.exists()
        assert (rules_dir / "rule-a.mdc").exists()


class TestGenCodex:
    def test_creates_instructions(self, fake_home):
        seed_manifest(fake_home, rules=[
            ("rule-a", "# Rule A\nContent A.\n"),
            ("rule-b", "# Rule B\nContent B.\n"),
        ])
        manifest = mod.read_manifest()
        mod.gen_codex(manifest, make_args())

        rules_file = mod.AGENT_PATHS["codex"]["rules_file"]
        assert rules_file.exists()
        text = rules_file.read_text()
        assert mod.GENERATED_HEADER in text
        assert "## Rule: rule-a" in text
        assert "## Rule: rule-b" in text
        assert "Content A." in text


class TestGenClaude:
    def test_creates_claude_md(self, fake_home):
        seed_manifest(fake_home, rules=[("rule-a", "# Rule A\nContent.\n")])
        manifest = mod.read_manifest()
        mod.gen_claude(manifest, make_args())

        rules_file = mod.AGENT_PATHS["claude"]["rules_file"]
        assert rules_file.exists()
        text = rules_file.read_text()
        assert mod.GENERATED_HEADER in text
        assert "Content." in text


class TestGenAgentsMd:
    def test_creates_numbered_summary(self, fake_home):
        target = fake_home / "projects" / "AGENTS.md"
        seed_manifest(
            fake_home,
            rules=[("rule-a", "# Rule A\nContent.\n")],
            agents_md_paths=[str(target)],
        )
        manifest = mod.read_manifest()
        mod.gen_agents_md(manifest, make_args())

        assert target.exists()
        text = target.read_text()
        assert mod.GENERATED_HEADER in text
        assert "1. **rule-a**" in text

    def test_no_paths_skips(self, fake_home, capsys):
        seed_manifest(fake_home, rules=[("rule-a", "Content.\n")])
        manifest = mod.read_manifest()
        mod.gen_agents_md(manifest, make_args())
        out = capsys.readouterr().out
        assert "no paths configured" in out


class TestSyncSkills:
    def test_creates_symlinks(self, fake_home):
        skills_dir = fake_home / ".ai-agent" / "skills"
        skill = skills_dir / "my-skill"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("# My Skill")

        target_dir = fake_home / ".cursor" / "skills"
        mod.sync_skills(target_dir, make_args())

        link = target_dir / "my-skill"
        assert link.is_symlink()
        assert link.resolve() == skill.resolve()

    def test_removes_stale_symlinks(self, fake_home):
        skills_dir = fake_home / ".ai-agent" / "skills"
        skills_dir.mkdir(parents=True)

        target_dir = fake_home / ".cursor" / "skills"
        target_dir.mkdir(parents=True)
        stale = target_dir / "gone-skill"
        stale.symlink_to(skills_dir / "gone-skill")

        mod.sync_skills(target_dir, make_args())
        assert not stale.exists()
