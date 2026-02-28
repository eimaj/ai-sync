## ADDED Requirements

### Requirement: Cursor MCP configuration

The system SHALL document how to register the MCP server with Cursor.

#### Scenario: Project-level configuration

- **WHEN** a user adds the server to `.cursor/mcp.json`
- **THEN** Cursor SHALL discover and connect to the sync tools
- **AND** the agent SHALL be able to call sync tools directly without bash commands

#### Scenario: Global configuration

- **WHEN** a user adds the server to `~/.cursor/mcp.json`
- **THEN** the sync tools SHALL be available in all Cursor workspaces

### Requirement: Claude Code MCP configuration

The system SHALL document how to register the MCP server with Claude Code.

#### Scenario: Add via CLI

- **WHEN** a user runs `claude mcp add sync-ai-rules --transport stdio -- python3 ~/.ai-agent/mcp/server.py`
- **THEN** Claude Code SHALL discover and connect to the sync tools

### Requirement: Codex MCP configuration

The system SHALL document how to register the MCP server with Codex.

#### Scenario: Add via CLI

- **WHEN** a user adds the server via Codex MCP configuration
- **THEN** Codex SHALL discover and connect to the sync tools

### Requirement: Skill documentation update

The existing `sync-ai-rules` skill SHALL be updated to reference MCP tools as the preferred integration path.

#### Scenario: Skill lists both CLI and MCP

- **WHEN** an agent loads the `sync-ai-rules` skill
- **THEN** it SHALL see MCP tools listed as the primary interface
- **AND** CLI commands listed as the fallback for environments without MCP

### Requirement: Setup documentation

The system SHALL provide a `mcp/README.md` with installation and configuration instructions.

#### Scenario: New user setup

- **WHEN** a user reads `mcp/README.md`
- **THEN** they SHALL find:
  - Prerequisites (Python 3.10+, `mcp` SDK)
  - Install command (`pip install mcp`)
  - Configuration snippets for Cursor, Claude Code, and Codex
  - Verification steps to confirm the server is working
  - List of available tools with brief descriptions
