# Tasks: CLI UX Improvements

All changes in `scripts/sync_agent_rules.py` unless noted.

## Phase 1: Subcommand Infrastructure

- [x] Add `status`, `add-rule`, `remove-rule`, `set` to `build_parser()`
- [x] Route new commands in `main()` via if/elif chain
- [x] Define `SETTABLE_KEYS` dict for `set` command validation

## Phase 2: Status Command

- [x] Implement `cmd_status()` — read manifest, print formatted sections
- [x] Format rules table with columns: id, source, cursor metadata, description
- [x] Display active targets (rules + skills)
- [x] Display canonical skill count
- [x] Display AGENTS.md paths
- [x] Display last synced timestamp

## Phase 2b: Selective Import During Init

- [x] Add `_rule_preview()` helper -- first non-heading line, truncated to 80 chars
- [x] Add rule multi-select to `cmd_init()` after deduplication -- show id, source, preview
- [x] Add skill multi-select to `cmd_init()` after rule selection -- show name, source path
- [x] Filter `all_rules` and `all_skills` to only selected items before writing
- [x] Remove old "Import summary" + "Proceed with import?" confirmation (replaced by multi-select)
- [x] Abort if no rules selected (zero selection = abort)
- [x] Auto-accept all when `--yes` is active

## Phase 3: Add Rule Command

- [x] Implement `cmd_add_rule()` — guard duplicate, create file, update manifest, sync
- [x] Support `--file` for importing existing markdown content
- [x] Support `--description` and `--always-apply` / `--no-always-apply` for Cursor metadata
- [x] Support `--exclude` for comma-separated agent exclusions

## Phase 4: Remove Rule Command

- [x] Implement `cmd_remove_rule()` — guard not-found, delete file, update manifest, sync
- [x] Verify stale `.mdc` cleanup in Cursor generator handles orphaned files

## Phase 5: Set Command

- [x] Implement `cmd_set()` — validate key, parse value, update manifest
- [x] Support array splitting for `agents_md.paths`
- [x] Support scalar assignment for `agents_md.header`, `agents_md.preamble`
- [x] Print error with supported keys list for unknown keys

## Phase 6: Wildcard AGENTS.md Paths

- [x] Add `_expand_agents_md_paths()` using stdlib `glob.glob(recursive=True)`
- [x] Integrate into `gen_agents_md()` — replace direct path iteration with expanded paths
- [x] Log warning when a glob pattern matches zero files
- [x] Auto-append `AGENTS.md` to directory paths

## Phase 7: Interactive Multi-Select

- [x] Implement `_curses_multi_select()` with arrow keys, space toggle, `a` all, enter confirm, `q` abort
- [x] Update `multi_select()` with fallback chain: auto_accept → curses → comma-separated
- [x] Detect TTY and curses availability before attempting curses mode
- [x] Preserve existing comma-separated logic as fallback
- [x] Handle empty options list without hanging

## Phase 8: Output Formatting

- [x] Add `section_header()` and `summary_line()` helper functions
- [x] Refactor `cmd_sync()` to use section headers and per-agent summary lines
- [x] Move per-file write/symlink logs behind `--verbose`
- [x] Update `cmd_init()` output to use consistent formatting

## Phase 9: Documentation & Validation

- [x] Update README.md with new commands and examples
- [x] Run `--dry-run --yes init` to verify no regressions
- [x] Run `status` against existing manifest
- [x] Run `add-rule test-rule --description "test"` + `remove-rule test-rule` roundtrip
- [x] Run `set agents_md.header` to verify scalar set
- [x] Verify fallback works when stdin is piped
- [x] Guard `cmd_add_rule` against duplicate manifest entries
