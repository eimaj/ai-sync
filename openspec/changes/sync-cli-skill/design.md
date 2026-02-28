## Context

The `sync_agent_rules.py` script (~1700 lines) manages a canonical rule/skill store at `~/.ai-agent/` and generates agent-native configs for Cursor, Codex, Claude Code, and others. Today, AI agents interact with it by running bash commands and parsing terminal output. This works but is fragile -- agents must know CLI syntax, global flag ordering, and how to interpret colored terminal output.

The MCP (Model Context Protocol) standard provides structured tool access for AI agents. An MCP server wrapping the sync script would let any MCP-capable tool (Cursor, Claude Code, Codex) call sync operations directly with typed parameters and JSON responses.

The existing `sync-ai-rules` skill provides CLI reference documentation and would be updated to reference MCP tools as the preferred integration path.

## Goals / Non-Goals

**Goals:**
- Expose all sync operations as MCP tools with typed input schemas and structured JSON responses
- Run locally via `stdio` transport -- no network, no auth, no Docker
- Import and call `sync_agent_rules.py` functions directly (same Python process)
- Provide MCP config examples for Cursor, Claude Code, and Codex
- Update the `sync-ai-rules` skill to document MCP alongside CLI

**Non-Goals:**
- HTTP/SSE transport (stdio is sufficient for a local-only tool)
- Rewriting `sync_agent_rules.py` internals (the MCP server is a thin adapter layer)
- GUI or web dashboard
- Interactive prompts via MCP (multi-select UX stays in CLI; MCP tools accept explicit parameters)
- `init` command via MCP (one-time setup stays in CLI)

## Decisions

### 1. Python MCP SDK over custom protocol handling

**Choice**: Use the `mcp` Python SDK (`pip install mcp`)

**Rationale**: The SDK handles protocol framing, tool registration, JSON schema generation, and error formatting. Writing a raw stdio JSON-RPC handler would be ~300 lines of boilerplate with no benefit. The SDK is the standard path for Python MCP servers.

**Alternative considered**: Raw `sys.stdin`/`sys.stdout` JSON-RPC -- rejected because it duplicates what the SDK provides and is harder to maintain.

### 2. stdio transport exclusively

**Choice**: `stdio` only, no HTTP/SSE

**Rationale**: The sync script is a local-only tool managing files in `~/.ai-agent/`. There's no multi-user or remote access scenario. stdio is the simplest transport -- the AI tool spawns the server process, communicates via stdin/stdout, and kills it when done. No ports, no auth, no firewall issues.

### 3. Thin adapter pattern

**Choice**: The MCP server imports `sync_agent_rules.py` and calls its functions, adapting `argparse.Namespace` inputs and terminal output to structured JSON.

**Rationale**: The sync script's functions are already well-factored (`cmd_status`, `cmd_sync`, `cmd_add_rule`, etc.). The MCP server creates a mock `argparse.Namespace`, calls the function, and captures/structures the result. No duplication of logic.

**Key challenge**: The `cmd_*` functions currently print to stdout and call `sys.exit()` on errors. The MCP adapter will need to:
- Redirect stdout/stderr capture via `io.StringIO` for functions that print
- Catch `SystemExit` and convert to MCP error responses
- For `cmd_status`, build structured JSON directly from `read_manifest()` and filesystem state rather than parsing terminal output

### 4. One MCP tool per operation

**Choice**: Map each CLI command to one MCP tool, named with `sync_` prefix.

| MCP Tool | CLI Command | Notes |
|----------|-------------|-------|
| `sync_status` | `status` | Returns structured JSON directly |
| `sync_rules` | `sync` | Returns sync summary |
| `sync_add_rule` | `add-rule` | All args as typed params |
| `sync_remove_rule` | `remove-rule` | |
| `sync_set_config` | `set` | |
| `sync_clean` | `clean` | |
| `sync_reconfigure` | `reconfigure` | Accepts explicit target lists |
| `sync_archive_skill` | `archive-skill` | |
| `sync_restore_skill` | `restore-skill` | |
| `sync_list_archived` | `archive-skill --list` | Separate tool for clarity |

**Excluded**: `init` (interactive, one-time setup -- stays CLI-only)

### 5. Server entry point and packaging

**Choice**: Single file `mcp/server.py` with a `__main__` guard. Self-contained `uv` venv at `mcp/.venv/` with pinned dependencies in `mcp/requirements.txt`. The venv is gitignored; users run a one-liner setup.

**Setup**:
```bash
cd ~/.ai-agent/mcp && uv venv --python 3.13 && uv pip install -r requirements.txt
```

`uv` auto-downloads Python 3.13 if missing. No global Python version management required.

**Invocation**:
```bash
~/.ai-agent/mcp/.venv/bin/python ~/.ai-agent/mcp/server.py
```

**MCP config** (Cursor example):
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

**Alternative considered**: `pip install mcp` into system Python -- rejected because the system Python may be <3.10 and global installs are fragile. A self-contained venv is reproducible and isolated.

## Risks / Trade-offs

**[Risk] `cmd_*` functions print to stdout, conflicting with MCP stdio protocol**
→ Mitigation: Redirect stdout/stderr to `io.StringIO` before calling `cmd_*` functions. The MCP SDK owns the real stdout for protocol messages.

**[Risk] `sys.exit()` calls in error paths would kill the MCP server**
→ Mitigation: Wrap all `cmd_*` calls in try/except `SystemExit`, convert exit code to MCP error response.

**[Risk] `mcp` SDK is an external dependency**
→ Mitigation: The MCP server is optional -- the CLI works without it. Document install step (`pip install mcp`). The sync script itself remains zero-dep.

**[Trade-off] No interactive prompts via MCP**
→ `reconfigure` in CLI uses `multi_select()` for target picking. The MCP version accepts explicit target arrays instead. This is actually better for AI agents -- they don't need TUI prompts.

**[Trade-off] `cmd_status` reimplemented for structured output**
→ Rather than parsing terminal output from `cmd_status`, the MCP tool reads `manifest.json` and filesystem state directly. Minor duplication but much cleaner than parsing ANSI-colored output.
