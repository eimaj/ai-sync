# Proposal: CLI UX Improvements

## Problem

The v1 sync tool works but has friction points that make everyday use cumbersome:

- **Adding/removing rules requires JSON editing.** Users must manually create a rule file, edit `manifest.json` to add the entry, then run sync. Three steps for what should be one command.
- **No visibility without reading JSON.** There is no way to see configured rules, targets, or last sync time without opening `manifest.json`.
- **Multi-select is clunky.** The current prompt asks for comma-separated numbers. Easy to mistype, no visual feedback, no way to toggle individual items.
- **AGENTS.md paths are static.** Users with many workspaces must list each path explicitly. No glob/wildcard support.
- **Output is noisy.** Per-file symlink logs clutter the output. No clear section boundaries. Hard to scan for what matters.
- **Manifest fields require JSON editing.** Changing `agents_md.paths` or `agents_md.header` means opening JSON by hand.

## Solution

Add new subcommands and UX improvements to `sync_agent_rules.py`:

1. `status` -- read-only summary of configuration
2. `add-rule` -- create rule file + manifest entry in one command
3. `remove-rule` -- delete rule file + manifest entry in one command
4. `set` -- update manifest fields from the CLI (dotted key paths)
5. Wildcard glob expansion for `agents_md.paths`
6. Interactive curses-based multi-select with arrow keys and space toggle
7. Cleaner output formatting with section headers and summary counts

## Scope

### In scope

- 4 new subcommands: `status`, `add-rule`, `remove-rule`, `set`
- Interactive multi-select using stdlib `curses` with fallback
- Glob expansion in `gen_agents_md()` for wildcard paths
- Output formatting cleanup (sections, counts, verbose-gated detail)
- README update with new commands

### Out of scope

- External dependencies (everything uses Python stdlib)
- GUI or web interface
- Rule content editing (users edit markdown files directly)
- New agent targets

## Success Criteria

- `add-rule` + `remove-rule` eliminate all JSON editing for rule management
- `status` gives a complete overview in one command
- `set` eliminates JSON editing for common manifest fields
- Multi-select works with arrow keys on macOS/Linux, falls back gracefully
- Wildcard paths like `~/Code/**/AGENTS.md` expand and write correctly
- Output without `--verbose` fits on one screen for typical configs

