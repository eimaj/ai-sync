## 1. Server Scaffold

- [x] 1.1 Create `mcp/server.py` with MCP SDK imports, server instance, and `__main__` guard
- [x] 1.2 Add stdout/stderr redirection helper (`_capture_output` context manager) for wrapping `cmd_*` calls
- [x] 1.3 Add `sys.exit()` interception helper (catch `SystemExit`, convert to error response)
- [x] 1.4 Add `_mock_args()` helper to build `argparse.Namespace` objects from MCP tool parameters

## 2. Read-Only Tools

- [x] 2.1 Implement `sync_status` tool -- read manifest + filesystem, return structured JSON
- [x] 2.2 Implement `sync_list_archived` tool -- list `skills-archived/` directory contents

## 3. Sync and Config Tools

- [x] 3.1 Implement `sync_rules` tool -- call `cmd_sync` with optional `only` and `dry_run` params
- [x] 3.2 Implement `sync_set_config` tool -- call `cmd_set` with `key` and `value` params
- [x] 3.3 Implement `sync_reconfigure` tool -- accept explicit `rule_targets` and `skill_targets` arrays, update manifest, call `cmd_sync`

## 4. Rule Management Tools

- [x] 4.1 Implement `sync_add_rule` tool -- accept `id`, `description`, `content`, `always_apply`, `exclude` params
- [x] 4.2 Implement `sync_remove_rule` tool -- accept `id` param

## 5. Skill Lifecycle Tools

- [x] 5.1 Implement `sync_archive_skill` tool -- accept `names` array, `dry_run` flag
- [x] 5.2 Implement `sync_restore_skill` tool -- accept `names` array, `dry_run` flag

## 6. Clean Tool

- [x] 6.1 Implement `sync_clean` tool -- call `cmd_clean`, return removal and restore counts

## 7. Documentation and Skill Update

- [x] 7.1 Create `mcp/README.md` with prerequisites, install, and config snippets for Cursor, Claude Code, and Codex
- [x] 7.2 Update `skills/sync-ai-rules/SKILL.md` to list MCP tools as primary interface, CLI as fallback
- [x] 7.3 Add `archive-skill` and `restore-skill` to the existing CLI reference in the skill

## 8. README Update

- [x] 8.1 Update `~/.ai-agent/README.md` with MCP server section: what it is, how to install, how to configure per tool

## 9. Verification

- [x] 9.1 Start MCP server, verify tool listing returns all 10 tools with typed schemas
- [x] 9.2 Call `sync_status` and verify structured JSON response matches `status` CLI output
- [x] 9.3 Call `sync_add_rule` + `sync_remove_rule` round-trip and verify manifest state
- [x] 9.4 Call `sync_archive_skill` + `sync_restore_skill` round-trip and verify skill directories
