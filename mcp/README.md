# sync-ai-rules MCP Server

An MCP (Model Context Protocol) server that exposes `sync-ai-rules` operations as structured tools. Any MCP-capable AI tool (Cursor, Claude Code, Codex) can manage rules and skills without constructing bash commands.

## Prerequisites

- Python 3.10+ (auto-installed by `uv` if missing)
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) package manager

## Setup

```bash
cd ~/.ai-agent/mcp
uv venv --python 3.13
uv pip install -r requirements.txt
```

## Configuration

### Cursor

Add to `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project):

```json
{
  "mcpServers": {
    "sync-ai-rules": {
      "command": "/Users/<you>/.ai-agent/mcp/.venv/bin/python",
      "args": ["/Users/<you>/.ai-agent/mcp/server.py"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add sync-ai-rules \
  --transport stdio \
  -- ~/.ai-agent/mcp/.venv/bin/python ~/.ai-agent/mcp/server.py
```

### Codex

```bash
codex mcp add sync-ai-rules \
  --transport stdio \
  -- ~/.ai-agent/mcp/.venv/bin/python ~/.ai-agent/mcp/server.py
```

## Verification

After configuring, ask your AI tool:

> "Use the sync_status tool to show my current sync configuration."

You should get a structured JSON response with rules, targets, skills, and paths.

## Available Tools

| Tool | Description |
|------|-------------|
| `sync_status` | Current configuration and state (rules, targets, skills, paths) |
| `sync_list_archived` | List archived (inactive) skills |
| `sync_rules` | Regenerate all agent configs (optional: `only`, `dry_run`) |
| `sync_set_config` | Update a manifest config value (`key`, `value`) |
| `sync_reconfigure` | Change active sync targets (`rule_targets`, `skill_targets`) |
| `sync_add_rule` | Create a new rule (`id`, `description`, `content`, `always_apply`, `exclude`) |
| `sync_remove_rule` | Remove a rule and clean up (`id`) |
| `sync_archive_skill` | Move skills to archive (`names`, `dry_run`) |
| `sync_restore_skill` | Restore archived skills (`names`, `dry_run`) |
| `sync_clean` | Remove generated files, restore from backup (`dry_run`) |

## Per-Target Config

The `sync_status` tool returns the full normalized `active_targets` configuration, including per-target `sync_mode` (`symlink` or `copy`) and `conflict_strategy` (`overwrite` or `archive`) for each skill target. String entries in the manifest are automatically normalized to their object form with defaults.

The `sync_reconfigure` tool preserves existing per-target settings when reselecting targets.

## How It Works

The MCP server imports `sync_agent_rules.py` directly and calls its functions. It adapts `argparse.Namespace` inputs and captures terminal output into structured JSON responses. The server runs locally via `stdio` -- no network, no auth.
