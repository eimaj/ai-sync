"""Shared fixtures for sync_agent_rules tests."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Load the script as a module (not in a package).
# Register in sys.modules so all test files share the SAME instance.
# ---------------------------------------------------------------------------

_SCRIPT = Path(__file__).parent.parent / "scripts" / "sync_agent_rules.py"

if "sync_agent_rules" not in sys.modules:
    _spec = importlib.util.spec_from_file_location("sync_agent_rules", _SCRIPT)
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules["sync_agent_rules"] = _mod
    _spec.loader.exec_module(_mod)

mod = sys.modules["sync_agent_rules"]

_REAL_HOME = Path.home()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Redirect all module-level paths into a temp directory."""
    home = tmp_path / "home"
    agent_dir = home / ".ai-agent"
    agent_dir.mkdir(parents=True)

    monkeypatch.setattr(mod, "AGENT_DIR", agent_dir)
    monkeypatch.setattr(mod, "MANIFEST_PATH", agent_dir / "manifest.json")
    monkeypatch.setattr(mod, "RULES_DIR", agent_dir / "rules")
    monkeypatch.setattr(mod, "SKILLS_DIR", agent_dir / "skills")
    monkeypatch.setattr(mod, "BACKUPS_DIR", agent_dir / "backups")
    monkeypatch.setattr(mod, "_current_backup", None)

    for key, info in mod.AGENT_PATHS.items():
        patched = dict(info)
        for path_key in ("rules_dir", "rules_file", "skills_dir"):
            if path_key in patched:
                orig = patched[path_key]
                patched[path_key] = home / orig.relative_to(_REAL_HOME)
        monkeypatch.setitem(mod.AGENT_PATHS, key, patched)

    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))

    return home


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def seed_manifest(
    home: Path,
    rules: list[tuple[str, str]] | None = None,
    rule_targets: list[str] | None = None,
    skill_targets: list[str] | None = None,
    agents_md_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Create manifest.json and rule files under the fake home. Returns manifest dict."""
    agent_dir = home / ".ai-agent"
    rules_dir = agent_dir / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    if rules is None:
        rules = [("test-rule", "# Test Rule\n\nTest content.\n")]

    rule_entries = []
    for rid, content in rules:
        (rules_dir / f"{rid}.md").write_text(content)
        rule_entries.append({
            "id": rid,
            "file": f"{rid}.md",
            "imported_from": "test",
            "cursor": {"alwaysApply": True, "description": f"Test {rid}"},
        })

    manifest: dict[str, Any] = {
        "version": "1.0",
        "updated": "2026-01-01",
        "imported_from": ["test"],
        "active_targets": {
            "rules": rule_targets if rule_targets is not None else ["cursor", "codex"],
            "skills": skill_targets if skill_targets is not None else [],
        },
        "rules": rule_entries,
        "skills": {"shared_dir": "skills"},
        "agents_md": {
            "paths": agents_md_paths or [],
            "header": "# AGENTS Rules",
            "preamble": "",
        },
    }
    (agent_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def make_args(**overrides: Any) -> argparse.Namespace:
    """Create an argparse.Namespace with sensible test defaults."""
    defaults: dict[str, Any] = {
        "dry_run": False,
        "diff": False,
        "verbose": False,
        "only": None,
        "yes": True,
        "command": "sync",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)
