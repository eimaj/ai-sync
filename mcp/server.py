#!/usr/bin/env python3
"""MCP server exposing sync-ai-rules operations as structured tools."""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import sync_agent_rules as sync  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

mcp = FastMCP(
    "sync-ai-rules",
    instructions="Manage AI agent rules and skills synchronization across Cursor, Codex, Claude Code, and other tools.",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_args(**kwargs: Any) -> argparse.Namespace:
    defaults = {
        "dry_run": False,
        "diff": False,
        "verbose": False,
        "only": None,
        "yes": True,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@contextmanager
def _capture_output():
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = buf_out = io.StringIO()
    sys.stderr = buf_err = io.StringIO()
    try:
        yield buf_out, buf_err
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def _run_cmd(fn, args: argparse.Namespace) -> dict[str, Any]:
    with _capture_output() as (out, err):
        try:
            fn(args)
        except SystemExit as e:
            return {
                "success": False,
                "error": err.getvalue().strip() or out.getvalue().strip() or f"exit code {e.code}",
            }
    return {
        "success": True,
        "output": out.getvalue().strip(),
    }


# ---------------------------------------------------------------------------
# Read-only tools
# ---------------------------------------------------------------------------


@mcp.tool()
def sync_status() -> dict[str, Any]:
    """Return the current sync configuration and state as structured JSON."""
    manifest = sync.read_manifest()
    rules = manifest.get("rules", [])

    active_skills: list[str] = []
    if sync.SKILLS_DIR.exists():
        active_skills = sorted(d.name for d in sync.SKILLS_DIR.iterdir() if d.is_dir())

    archived: list[str] = []
    if sync.SKILLS_ARCHIVED_DIR.exists():
        archived = sorted(d.name for d in sync.SKILLS_ARCHIVED_DIR.iterdir() if d.is_dir())

    return {
        "rules": [
            {
                "id": r["id"],
                "file": r.get("file", ""),
                "imported_from": r.get("imported_from", ""),
                "alwaysApply": r.get("cursor", {}).get("alwaysApply", False),
                "description": r.get("cursor", {}).get("description", ""),
            }
            for r in rules
        ],
        "active_targets": manifest.get("active_targets", {}),
        "skills": active_skills,
        "archived_skills": archived,
        "agents_md_paths": manifest.get("agents_md", {}).get("paths", []),
        "last_synced": manifest.get("updated", "never"),
    }


@mcp.tool()
def sync_list_archived() -> dict[str, Any]:
    """List all archived (inactive) skills."""
    archived: list[str] = []
    if sync.SKILLS_ARCHIVED_DIR.exists():
        archived = sorted(d.name for d in sync.SKILLS_ARCHIVED_DIR.iterdir() if d.is_dir())
    return {"archived_skills": archived}


# ---------------------------------------------------------------------------
# Sync and config tools
# ---------------------------------------------------------------------------


@mcp.tool()
def sync_rules(only: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Regenerate all agent configs from canonical source.

    Args:
        only: Restrict sync to a single agent target (e.g. "cursor", "codex").
        dry_run: Preview changes without writing files.
    """
    args = _mock_args(only=only, dry_run=dry_run)
    return _run_cmd(sync.cmd_sync, args)


@mcp.tool()
def sync_set_config(key: str, value: str) -> dict[str, Any]:
    """Update a manifest configuration value.

    Args:
        key: Dotted key path (agents_md.paths, agents_md.header, agents_md.preamble).
        value: New value (array fields are comma-separated).
    """
    args = _mock_args(key=key, value=value)
    return _run_cmd(sync.cmd_set, args)


@mcp.tool()
def sync_reconfigure(
    rule_targets: list[str],
    skill_targets: list[str],
) -> dict[str, Any]:
    """Change which agents receive rule syncs and skill delivery, then re-sync.

    Preserves existing per-target sync_mode and conflict_strategy settings.
    New targets default to symlink mode with overwrite strategy.

    Args:
        rule_targets: Agent IDs for rule sync (e.g. ["cursor", "codex", "claude"]).
        skill_targets: Agent IDs for skill delivery (e.g. ["cursor", "codex"]).
    """
    manifest = sync.read_manifest()
    manifest["active_targets"]["rules"] = rule_targets
    old_skills = {t["name"]: t for t in manifest["active_targets"]["skills"]}
    new_skills = []
    for name in skill_targets:
        if name in old_skills:
            new_skills.append(old_skills[name])
        else:
            new_skills.append({"name": name, "sync_mode": "symlink",
                               "conflict_strategy": "overwrite"})
    manifest["active_targets"]["skills"] = new_skills
    args = _mock_args()
    sync.write_manifest(manifest, args)
    return _run_cmd(sync.cmd_sync, args)


# ---------------------------------------------------------------------------
# Rule management tools
# ---------------------------------------------------------------------------


@mcp.tool()
def sync_add_rule(
    id: str,
    description: str = "",
    content: str = "",
    always_apply: bool = True,
    exclude: str = "",
) -> dict[str, Any]:
    """Create a new canonical rule, add to manifest, and sync.

    Args:
        id: Rule identifier (becomes filename, e.g. "my-rule" -> rules/my-rule.md).
        description: Short description shown in Cursor's rule picker.
        content: Markdown content for the rule. If empty, a placeholder is created.
        always_apply: Whether the rule is always applied in Cursor.
        exclude: Comma-separated agent targets to skip (e.g. "kiro,gemini").
    """
    tmp_file = None
    file_path = None
    if content:
        tmp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
        tmp_file.write(content)
        tmp_file.close()
        file_path = tmp_file.name

    args = _mock_args(
        id=id,
        description=description,
        file=file_path,
        always_apply=always_apply,
        no_always_apply=not always_apply,
        exclude=exclude,
    )
    result = _run_cmd(sync.cmd_add_rule, args)

    if tmp_file:
        Path(tmp_file.name).unlink(missing_ok=True)

    return result


@mcp.tool()
def sync_remove_rule(id: str) -> dict[str, Any]:
    """Remove a canonical rule, its manifest entry, and sync to clean up.

    Args:
        id: Rule identifier to remove (e.g. "my-rule").
    """
    args = _mock_args(id=id)
    return _run_cmd(sync.cmd_remove_rule, args)


# ---------------------------------------------------------------------------
# Skill lifecycle tools
# ---------------------------------------------------------------------------


@mcp.tool()
def sync_archive_skill(names: list[str], dry_run: bool = False) -> dict[str, Any]:
    """Move skills out of active sync into the archive.

    Args:
        names: Skill names to archive (e.g. ["my-skill"]).
        dry_run: Preview without moving.
    """
    args = _mock_args(names=names, dry_run=dry_run, list_archived=False)
    return _run_cmd(sync.cmd_archive_skill, args)


@mcp.tool()
def sync_restore_skill(names: list[str], dry_run: bool = False) -> dict[str, Any]:
    """Restore archived skills back to active sync.

    Args:
        names: Skill names to restore (e.g. ["my-skill"]).
        dry_run: Preview without moving.
    """
    args = _mock_args(names=names, dry_run=dry_run)
    return _run_cmd(sync.cmd_restore_skill, args)


# ---------------------------------------------------------------------------
# Clean tool
# ---------------------------------------------------------------------------


@mcp.tool()
def sync_clean(dry_run: bool = False) -> dict[str, Any]:
    """Remove generated files and restore originals from backup.

    Args:
        dry_run: Preview without removing.
    """
    args = _mock_args(dry_run=dry_run)
    return _run_cmd(sync.cmd_clean, args)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
