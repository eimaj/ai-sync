## Why

AI agents can only interact with the sync system today by constructing bash commands against the CLI. This requires the agent to know the CLI syntax, parse terminal output, and handle errors by reading stderr. Every AI tool (Cursor, Claude Code, Codex) has to go through the same bash-command-construction path, which is fragile and verbose.

An MCP server wrapping the sync script would give any MCP-capable AI tool structured, typed access to the sync system -- no bash required. The agent discovers available operations via tool listing, calls them with typed parameters, and gets structured JSON responses. This is the standard integration path for AI tooling in 2026.

## What Changes

- New MCP server (`sync-ai-rules-mcp`) that wraps `sync_agent_rules.py` as MCP tools
- Each CLI command becomes an MCP tool with typed input/output schemas
- Structured JSON responses replace terminal output parsing
- The server runs locally via `stdio` transport (no network, no auth)
- Update the existing `sync-ai-rules` skill to reference the MCP tools alongside the CLI
- MCP config examples for Cursor, Claude Code, and Codex so any developer can enable it

## Capabilities

### New Capabilities

- `mcp-server`: MCP server exposing sync operations as structured tools with typed parameters and JSON responses
- `mcp-integration`: Configuration and setup for connecting the MCP server to each supported AI tool

### Modified Capabilities

(none -- no existing spec-level requirements change)

## Impact

- New file: `mcp/server.py` (MCP server, stdlib + `mcp` SDK)
- Modified file: `skills/sync-ai-rules/SKILL.md` (add MCP tool reference alongside CLI)
- New file: `mcp/README.md` (setup instructions per tool)
- Dependencies: `mcp` Python SDK (pip install)
- No changes to `sync_agent_rules.py` itself -- the MCP server imports and calls its functions

