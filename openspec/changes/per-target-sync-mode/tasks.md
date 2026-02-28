## 1. Manifest Parsing & Normalization

- [x] 1.1 Add `_normalize_targets(manifest)` function that converts string entries in `active_targets.skills` and `active_targets.rules` to object form with `name`, `sync_mode`, `conflict_strategy` defaults
- [x] 1.2 Add validation — reject unknown `sync_mode` or `conflict_strategy` values with a clear error message naming the invalid entry
- [x] 1.3 Update `read_manifest()` (or callers) to run normalization after loading JSON
- [x] 1.4 Add `_get_target_config(manifest, target_name, category)` helper that returns the normalized config object for a given target name and category (`"skills"` or `"rules"`)

## 2. Copy Mode Implementation

- [x] 2.1 Add `_sync_skills_copy(target_dir, conflict_strategy, args)` — recursively copy each canonical skill to the target dir, write `.sync-meta` marker, remove stale managed copies
- [x] 2.2 Define `.sync-meta` JSON structure: `{ "source": "<abs path>", "synced_at": "<ISO>", "sync_mode": "copy" }`
- [x] 2.3 Add `_is_managed_copy(path)` helper — checks for `.sync-meta` file and validates `source` points into `~/.ai-agent/skills/`
- [x] 2.4 Handle stale copy removal: if a copied skill's canonical source no longer exists, remove the copy

## 3. Refactor `sync_skills()`

- [x] 3.1 Extract current symlink logic into `_sync_skills_symlink(target_dir, conflict_strategy, args)`
- [x] 3.2 Update `sync_skills()` signature to accept `target_config` dict (with `sync_mode`, `conflict_strategy`)
- [x] 3.3 Add dispatch logic: call `_sync_skills_symlink` or `_sync_skills_copy` based on `target_config["sync_mode"]`
- [x] 3.4 Implement `conflict_strategy` in both modes: `archive` moves non-managed directories to `~/.ai-agent/skills-archived/{target}-{name}/`; `overwrite` removes them directly

## 4. Update Generators

- [x] 4.1 Update `gen_cursor()` to pass normalized target config to `sync_skills()`
- [x] 4.2 Update `gen_codex()` to pass normalized target config to `sync_skills()`
- [x] 4.3 Update `gen_claude()` to pass normalized target config to `sync_skills()`
- [x] 4.4 Update `gen_gemini()` to pass normalized target config to `sync_skills()`
- [x] 4.5 Update `gen_antigravity()` to pass normalized target config to `sync_skills()`

## 5. Update `cmd_clean()`

- [x] 5.1 Update clean to detect and remove managed copies (directories with `.sync-meta` pointing into canonical)
- [x] 5.2 Preserve existing symlink cleanup logic alongside copy cleanup

## 6. Update `cmd_status()`

- [x] 6.1 Display `sync_mode` and `conflict_strategy` for each skills target in the status output
- [x] 6.2 Distinguish between symlinked and copied skills in target summaries

## 7. Update MCP Server

- [x] 7.1 Update `sync_status` MCP tool return value to include per-target config
- [x] 7.2 Verify other MCP tools work with the manifest schema change (sync, clean)

## 8. Documentation & Help Text

- [x] 8.1 Update argparse help strings for `sync`, `init`, and `reconfigure` to mention `sync_mode` and `conflict_strategy` options
- [x] 8.2 Update `README.md` — Supported Agents table (Skills column: "Symlinks" → "Symlinks / Copy"), manifest schema section, How It Works section, Commands table
- [x] 8.3 Update `mcp/README.md` — document that `sync_status` now returns per-target config; note new manifest fields
- [x] 8.4 Update `skills/sync-ai-rules/SKILL.md` — add `sync_mode` and `conflict_strategy` to manifest documentation and common tasks examples
- [x] 8.5 Update `README.md` Directory Structure section to mention `.sync-meta` marker files and `skills-archived/` for conflict archiving

## 9. Testing & Verification

- [x] 9.1 Test backward compatibility: existing manifest with string-only arrays works unchanged
- [x] 9.2 Test copy mode: skills copied to target, `.sync-meta` written, re-sync updates copies
- [x] 9.3 Test archive conflict strategy: non-managed directories moved to archive before write
- [x] 9.4 Test clean: removes both symlinks and managed copies correctly
- [x] 9.5 Test mixed manifest: some targets symlink, some copy — all sync correctly
- [x] 9.6 Update `manifest.json` with a real copy target (e.g., claude) and run full sync
