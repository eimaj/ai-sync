"""Integration tests for all CLI commands."""

import json
import sys
from pathlib import Path

import pytest

from tests.conftest import make_args, seed_manifest

mod = sys.modules["sync_agent_rules"]


class TestCmdStatus:
    def test_output_contains_rules(self, fake_home, capsys):
        seed_manifest(fake_home, rules=[
            ("my-rule", "# My Rule\nContent.\n"),
            ("other-rule", "# Other\nStuff.\n"),
        ])
        mod.cmd_status(make_args(command="status"))
        out = capsys.readouterr().out
        assert "my-rule" in out
        assert "other-rule" in out

    def test_output_contains_targets(self, fake_home, capsys):
        seed_manifest(fake_home, rule_targets=["cursor", "codex"])
        mod.cmd_status(make_args(command="status"))
        out = capsys.readouterr().out
        assert "cursor" in out
        assert "codex" in out

    def test_output_contains_date(self, fake_home, capsys):
        seed_manifest(fake_home)
        mod.cmd_status(make_args(command="status"))
        out = capsys.readouterr().out
        assert "2026-01-01" in out


class TestCmdSync:
    def test_generates_files(self, fake_home):
        seed_manifest(fake_home, rules=[("rule-a", "# A\nContent.\n")])
        mod.cmd_sync(make_args())

        cursor_rules = mod.AGENT_PATHS["cursor"]["rules_dir"]
        codex_file = mod.AGENT_PATHS["codex"]["rules_file"]
        assert (cursor_rules / "rule-a.mdc").exists()
        assert codex_file.exists()

    def test_dry_run_no_files(self, fake_home):
        seed_manifest(fake_home, rules=[("rule-a", "# A\nContent.\n")])
        mod.cmd_sync(make_args(dry_run=True))

        cursor_rules = mod.AGENT_PATHS["cursor"]["rules_dir"]
        codex_file = mod.AGENT_PATHS["codex"]["rules_file"]
        assert not (cursor_rules / "rule-a.mdc").exists()
        assert not codex_file.exists()

    def test_only_filters(self, fake_home):
        seed_manifest(fake_home, rules=[("rule-a", "# A\nContent.\n")])
        mod.cmd_sync(make_args(only="cursor"))

        cursor_rules = mod.AGENT_PATHS["cursor"]["rules_dir"]
        codex_file = mod.AGENT_PATHS["codex"]["rules_file"]
        assert (cursor_rules / "rule-a.mdc").exists()
        assert not codex_file.exists()

    def test_only_invalid_agent(self, fake_home):
        seed_manifest(fake_home)
        with pytest.raises(SystemExit):
            mod.cmd_sync(make_args(only="nonexistent"))


class TestCmdAddRule:
    def test_creates_file_and_manifest(self, fake_home):
        seed_manifest(fake_home, rules=[])
        args = make_args(
            command="add-rule", id="new-rule",
            description="A new rule", file=None,
            no_always_apply=False, exclude="",
        )
        mod.cmd_add_rule(args)

        rule_path = mod.RULES_DIR / "new-rule.md"
        assert rule_path.exists()
        assert "New Rule" in rule_path.read_text()

        manifest = json.loads(mod.MANIFEST_PATH.read_text())
        ids = [r["id"] for r in manifest["rules"]]
        assert "new-rule" in ids

    def test_dry_run_no_file(self, fake_home):
        seed_manifest(fake_home, rules=[])
        args = make_args(
            command="add-rule", id="new-rule", dry_run=True,
            description="Test", file=None,
            no_always_apply=False, exclude="",
        )
        mod.cmd_add_rule(args)

        assert not (mod.RULES_DIR / "new-rule.md").exists()
        manifest = json.loads(mod.MANIFEST_PATH.read_text())
        ids = [r["id"] for r in manifest["rules"]]
        assert "new-rule" not in ids

    def test_duplicate_errors(self, fake_home):
        seed_manifest(fake_home, rules=[("existing", "# Existing\nContent.\n")])
        args = make_args(
            command="add-rule", id="existing",
            description="", file=None,
            no_always_apply=False, exclude="",
        )
        with pytest.raises(SystemExit):
            mod.cmd_add_rule(args)

    def test_from_file(self, fake_home, tmp_path):
        seed_manifest(fake_home, rules=[])
        source = tmp_path / "source-rule.md"
        source.write_text("# Imported Rule\n\nImported content.\n")

        args = make_args(
            command="add-rule", id="imported",
            description="Imported", file=str(source),
            no_always_apply=False, exclude="",
        )
        mod.cmd_add_rule(args)

        rule_path = mod.RULES_DIR / "imported.md"
        assert rule_path.exists()
        assert "Imported content." in rule_path.read_text()


class TestCmdRemoveRule:
    def test_removes_file_and_manifest(self, fake_home):
        seed_manifest(fake_home, rules=[
            ("keep-me", "# Keep\nContent.\n"),
            ("delete-me", "# Delete\nContent.\n"),
        ])
        mod.cmd_remove_rule(make_args(command="remove-rule", id="delete-me"))

        assert not (mod.RULES_DIR / "delete-me.md").exists()
        manifest = json.loads(mod.MANIFEST_PATH.read_text())
        ids = [r["id"] for r in manifest["rules"]]
        assert "delete-me" not in ids
        assert "keep-me" in ids

    def test_dry_run_preserves(self, fake_home):
        seed_manifest(fake_home, rules=[("rule-a", "# A\nContent.\n")])
        mod.cmd_remove_rule(make_args(command="remove-rule", id="rule-a", dry_run=True))

        assert (mod.RULES_DIR / "rule-a.md").exists()
        manifest = json.loads(mod.MANIFEST_PATH.read_text())
        ids = [r["id"] for r in manifest["rules"]]
        assert "rule-a" in ids

    def test_not_found_errors(self, fake_home):
        seed_manifest(fake_home)
        with pytest.raises(SystemExit):
            mod.cmd_remove_rule(make_args(command="remove-rule", id="nonexistent"))


class TestCmdSet:
    def test_set_scalar(self, fake_home):
        seed_manifest(fake_home)
        mod.cmd_set(make_args(command="set", key="agents_md.header", value="# Custom"))

        manifest = json.loads(mod.MANIFEST_PATH.read_text())
        assert manifest["agents_md"]["header"] == "# Custom"

    def test_set_array(self, fake_home):
        seed_manifest(fake_home)
        mod.cmd_set(make_args(
            command="set", key="agents_md.paths",
            value="~/a/AGENTS.md,~/b/AGENTS.md",
        ))

        manifest = json.loads(mod.MANIFEST_PATH.read_text())
        assert manifest["agents_md"]["paths"] == ["~/a/AGENTS.md", "~/b/AGENTS.md"]

    def test_invalid_key_errors(self, fake_home):
        seed_manifest(fake_home)
        with pytest.raises(SystemExit):
            mod.cmd_set(make_args(command="set", key="bad.key", value="x"))


class TestCmdClean:
    def test_removes_generated_files(self, fake_home):
        seed_manifest(fake_home, rules=[("rule-a", "# A\nContent.\n")])
        mod.cmd_sync(make_args())

        cursor_file = mod.AGENT_PATHS["cursor"]["rules_dir"] / "rule-a.mdc"
        assert cursor_file.exists()

        mod.cmd_clean(make_args(command="clean"))
        assert not cursor_file.exists()

    def test_dry_run_preserves(self, fake_home):
        seed_manifest(fake_home, rules=[("rule-a", "# A\nContent.\n")])
        mod.cmd_sync(make_args())

        cursor_file = mod.AGENT_PATHS["cursor"]["rules_dir"] / "rule-a.mdc"
        assert cursor_file.exists()

        mod.cmd_clean(make_args(command="clean", dry_run=True))
        assert cursor_file.exists()


class TestCmdReconfigure:
    def test_yes_preserves_defaults(self, fake_home, capsys):
        seed_manifest(fake_home, rule_targets=["cursor", "codex"])
        mod.cmd_reconfigure(make_args(command="reconfigure"))

        manifest = json.loads(mod.MANIFEST_PATH.read_text())
        assert "cursor" in manifest["active_targets"]["rules"]
        assert "codex" in manifest["active_targets"]["rules"]


class TestCmdInit:
    def test_imports_from_seeded_source(self, fake_home, capsys):
        cursor_rules = mod.AGENT_PATHS["cursor"]["rules_dir"]
        cursor_rules.mkdir(parents=True)
        (cursor_rules / "imported-rule.mdc").write_text(
            "---\nalwaysApply: true\n---\n# Imported\n\nSome content.\n"
        )

        mod.cmd_init(make_args(command="init"))

        assert (mod.RULES_DIR / "imported-rule.md").exists()
        assert mod.MANIFEST_PATH.exists()

        manifest = json.loads(mod.MANIFEST_PATH.read_text())
        ids = [r["id"] for r in manifest["rules"]]
        assert "imported-rule" in ids

    def test_skips_generated_files(self, fake_home, capsys):
        cursor_rules = mod.AGENT_PATHS["cursor"]["rules_dir"]
        cursor_rules.mkdir(parents=True)
        (cursor_rules / "generated.mdc").write_text(
            "---\n---\n" + mod.GENERATED_HEADER + "\nGenerated content."
        )
        (cursor_rules / "real.mdc").write_text(
            "---\nalwaysApply: true\n---\n# Real\nReal content.\n"
        )

        mod.cmd_init(make_args(command="init"))

        manifest = json.loads(mod.MANIFEST_PATH.read_text())
        ids = [r["id"] for r in manifest["rules"]]
        assert "real" in ids
        assert "generated" not in ids
