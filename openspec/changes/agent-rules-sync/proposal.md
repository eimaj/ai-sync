# Proposal: Agent-Agnostic Rules Sync

## Problem

AI agent rules and skills are scattered across agent-specific directories with no canonical source. One agent (typically Cursor) becomes the de facto source of truth, but sharing with other agents is manual, incomplete, and drift-prone:

- Rules exist in different formats per agent (`.mdc`, `CLAUDE.md`, `GEMINI.md`, etc.)
- Skills are manually symlinked or copied between agents
- Agents that lack file-based config (or that the user hasn't set up yet) get nothing
- `AGENTS.md` files drift independently from the actual rules

Adding or editing a rule requires manually updating each agent's config format. In practice, only one or two agents stay current; the rest are neglected.

## Solution

A Python CLI tool (`sync_agent_rules.py`) that:

1. **Imports** rules and skills from existing agent configs into a single canonical source at `~/.ai-agent/`
2. **Deduplicates** rules across sources (exact match skips, similar flags for review)
3. **Generates** agent-native formats for user-selected targets (Cursor `.mdc`, Codex `model-instructions.md`, Claude `CLAUDE.md`, Gemini `GEMINI.md`, Kiro `steering/conventions.md`, AGENTS.md)
4. **Symlinks** shared skills from `~/.ai-agent/skills/` into each agent's skills directory

The script itself is version-controlled and pushed to GitHub. It has zero external dependencies -- just Python 3.10+ stdlib. Personal rules, skills, and configuration (`manifest.json`) are gitignored and stay local. Anyone can clone the repo and run `init` immediately.

## Scope

### In scope

- **User-level (global) rules only** -- rules in `~/.cursor/rules/`, `~/.codex/model-instructions.md`, etc. Workspace-level rules (e.g., `<project>/.cursor/rules/`) are not managed by this tool.
- `init` mode: interactive wizard to import from existing agents, select targets, write manifest
- `sync` mode: idempotent generation of all active targets from canonical source
- `reconfigure` mode: change target selection without re-importing
- Per-agent importers: Cursor, Codex, Claude Code, Gemini CLI, Kiro, Antigravity
- Per-agent generators: all 6 agents plus AGENTS.md
- Manifest (`manifest.json`) tracking rules, metadata, active targets, and provenance
- Skill symlink management for Cursor, Codex, Gemini CLI, Antigravity
- CLI flags: `--dry-run`, `--diff`, `--verbose`, `--only <agent>`, `--yes`
- `.gitignore` separating tool (committed) from personal content (local only)

### Out of scope

- IDE-specific skills (e.g., agent-native skills managed by that agent alone) -- these stay in their native agent directories and are not imported or synced
- Agent system directories (e.g., `~/.codex/skills/.system/`) -- not touched
- Workspace-level rules (e.g., `<project>/.cursor/rules/`) -- per-project, not global
- ChatGPT -- no file-based global config; covered via AGENTS.md
- Automatic sync on rule edit (future: file watcher or git hook)
- Incremental import after init (future: `import` subcommand to add new rules without re-running `init`)
- Web UI or GUI
- Team collaboration features (though the tool can be forked/reused by others)

## Success Criteria

- Single `sync` command updates all active agent configs from canonical rules
- Adding a new rule means: create one `.md` file + add entry to `manifest.json` + run `sync`
- Existing rules round-trip correctly (import -> canonical -> re-export matches original)
- Skill symlinks resolve for all skill-capable agents
- `--dry-run` previews all changes without writing
- The repo can be cloned by anyone; personal content is never committed
