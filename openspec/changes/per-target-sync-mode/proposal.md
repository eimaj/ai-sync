## Why

The sync script currently hardcodes symlinks for all skill targets and generates rule files in-place. Some agents (e.g., Claude Code on remote/sandboxed machines) don't support symlinks -- they need real file copies. Additionally, when the sync overwrites existing agent-native rules or skills, the previous content is lost with no option for a soft transition. Users need per-target control over **how** content is delivered (symlink vs copy) and **how** conflicts are resolved (archive the old content vs overwrite destructively), all managed declaratively from `manifest.json`.

## What Changes

- Add a `sync_mode` option per target in the manifest (`symlink` | `copy`), defaulting to `symlink` for backward compatibility
- Add a `conflict_strategy` option per target in the manifest (`archive` | `overwrite`), defaulting to `overwrite` for current behavior
- Update `sync_skills()` to respect `sync_mode` -- either create symlinks or recursively copy skill directories
- Update rule generators to respect `conflict_strategy` -- either archive existing non-generated files before writing, or overwrite them directly
- Update `clean` to handle both symlinked and copied skills (remove copies that match canonical content, not just symlinks)
- Update `status` to display the per-target sync mode and conflict strategy
- Update `manifest.json` schema to support the new fields under `active_targets`

## Capabilities

### New Capabilities

- `target-sync-config`: Per-target sync mode (symlink vs copy) and conflict strategy (archive vs overwrite), managed declaratively from the manifest

### Modified Capabilities

- `sync-system`: Skill sync and rule generation must respect per-target sync mode and conflict strategy; clean must handle copied skills; status must display config

## Impact

- `scripts/sync_agent_rules.py` -- core sync logic changes in `sync_skills()`, all `gen_*()` functions, `cmd_clean()`, `cmd_status()`
- `manifest.json` -- schema extension for `active_targets` to support object entries with `sync_mode` and `conflict_strategy`
- `mcp/server.py` -- MCP tools that wrap sync/status may need updated return schemas
- Backward compatible: string-only entries in `active_targets` arrays continue to work with defaults
