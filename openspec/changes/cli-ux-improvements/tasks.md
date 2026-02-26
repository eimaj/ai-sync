# Tasks: CLI UX Improvements

All changes in `scripts/sync_agent_rules.py` unless noted.

## Phase 1: Subcommand Infrastructure

- [ ] Add `status`, `add-rule`, `remove-rule`, `set` to `build_parser()`
- [ ] Route new commands in `main()` via if/elif chain
- [ ] Define `SETTABLE_KEYS` dict for `set` command validation

## Phase 2: Status Command

- [ ] Implement `cmd_status()` — read manifest, print formatted sections
- [ ] Format rules table with columns: id, source, cursor metadata, description
- [ ] Display active targets (rules + skills)
- [ ] Display canonical skill count
- [ ] Display AGENTS.md paths
- [ ] Display last synced timestamp

## Phase 2b: Selective Import During Init

- [ ] Add `_rule_preview()` helper -- first non-heading line, truncated to 80 chars
- [ ] Add rule multi-select to `cmd_init()` after deduplication -- show id, source, preview
- [ ] Add skill multi-select to `cmd_init()` after rule selection -- show name, source path
- [ ] Filter `all_rules` and `all_skills` to only selected items before writing
- [ ] Remove old "Import summary" + "Proceed with import?" confirmation (replaced by multi-select)
- [ ] Abort if no rules selected (zero selection = abort)
- [ ] Auto-accept all when `--yes` is active

## Phase 3: Add Rule Command

- [ ] Implement `cmd_add_rule()` — guard duplicate, create file, update manifest, sync
- [ ] Support `--file` for importing existing markdown content
- [ ] Support `--description` and `--always-apply` / `--no-always-apply` for Cursor metadata
- [ ] Support `--exclude` for comma-separated agent exclusions

## Phase 4: Remove Rule Command

- [ ] Implement `cmd_remove_rule()` — guard not-found, delete file, update manifest, sync
- [ ] Verify stale `.mdc` cleanup in Cursor generator handles orphaned files

## Phase 5: Set Command

- [ ] Implement `cmd_set()` — validate key, parse value, update manifest
- [ ] Support array splitting for `agents_md.paths`
- [ ] Support scalar assignment for `agents_md.header`, `agents_md.preamble`
- [ ] Print error with supported keys list for unknown keys

## Phase 6: Wildcard AGENTS.md Paths

- [ ] Add `_expand_agents_md_paths()` using stdlib `glob.glob(recursive=True)`
- [ ] Integrate into `gen_agents_md()` — replace direct path iteration with expanded paths
- [ ] Log warning when a glob pattern matches zero files

## Phase 7: Interactive Multi-Select

- [ ] Implement `_curses_multi_select()` with arrow keys, space toggle, `a` all, enter confirm, `q` abort
- [ ] Update `multi_select()` with fallback chain: auto_accept → curses → comma-separated
- [ ] Detect TTY and curses availability before attempting curses mode
- [ ] Preserve existing comma-separated logic as fallback

## Phase 8: Output Formatting

- [ ] Add `section_header()` and `summary_line()` helper functions
- [ ] Refactor `cmd_sync()` to use section headers and per-agent summary lines
- [ ] Move per-file write/symlink logs behind `--verbose`
- [ ] Update `cmd_init()` output to use consistent formatting

## Phase 9: Documentation & Validation

- [ ] Update README.md with new commands and examples
- [ ] Run `--dry-run --yes init` to verify no regressions
- [ ] Run `status` against existing manifest
- [ ] Run `add-rule test-rule --description "test"` + `remove-rule test-rule` roundtrip
- [ ] Run `set agents_md.paths "~/Code/**/AGENTS.md"` + `sync` with wildcard
- [ ] Verify curses multi-select works in real terminal
- [ ] Verify fallback works when stdin is piped
