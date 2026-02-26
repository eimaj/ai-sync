# Tasks: Add Test Suite

## Phase 1: Infrastructure

- [ ] Create `requirements-dev.txt` with `pytest>=7.0`
- [ ] Create `tests/conftest.py` with module loader, `fake_home` fixture, `seed_manifest`, `make_args`
- [ ] Verify `pytest tests/` runs (empty suite, no errors)

## Phase 2: Unit Tests -- Frontmatter

- [ ] `test_parse_valid`: frontmatter with bool, string, quoted values
- [ ] `test_parse_no_frontmatter`: plain text returns empty dict
- [ ] `test_parse_bool_coercion`: true/false strings become Python bools
- [ ] `test_build_frontmatter`: round-trip parse(build(meta)) == meta
- [ ] `test_is_generated_file_positive`: content with generated header
- [ ] `test_is_generated_file_negative`: content without generated header
- [ ] `test_rule_preview`: first non-heading line, truncated

## Phase 3: Unit Tests -- Deduplication

- [ ] `test_dedup_no_duplicates`: all unique rules pass through
- [ ] `test_dedup_exact_match`: second identical rule is dropped
- [ ] `test_dedup_high_similarity`: >80% match is dropped
- [ ] `test_dedup_low_similarity_yes`: <80% match keeps first with --yes

## Phase 4: Generator Tests

- [ ] `test_gen_cursor`: creates .mdc files with frontmatter + generated header
- [ ] `test_gen_cursor_stale_cleanup`: removes orphaned generated .mdc files
- [ ] `test_gen_codex`: creates model-instructions.md with rule sections
- [ ] `test_gen_claude`: creates CLAUDE.md with concatenated rules
- [ ] `test_gen_agents_md`: creates numbered summary at configured paths
- [ ] `test_sync_skills`: creates symlinks to canonical skills

## Phase 5: Backup Tests

- [ ] `test_init_backup`: creates timestamped dir with meta.json
- [ ] `test_backup_file`: copies file to backup dir
- [ ] `test_backup_file_dry_run`: no copy when dry-run
- [ ] `test_backup_file_skips_symlinks`: symlinks not backed up
- [ ] `test_latest_backup`: returns most recent backup dir
- [ ] `test_restore_from_backup`: restores targeted files
- [ ] `test_write_file_backs_up`: existing file backed up before overwrite
- [ ] `test_remove_file_backs_up`: existing file backed up before unlink

## Phase 6: Integration Tests -- Commands

- [ ] `test_cmd_status`: output contains rule names, targets, date
- [ ] `test_cmd_sync`: generates files for active targets
- [ ] `test_cmd_sync_dry_run`: no files created
- [ ] `test_cmd_sync_only`: filters to single agent
- [ ] `test_cmd_add_rule`: creates file + manifest entry
- [ ] `test_cmd_add_rule_dry_run`: no file created, manifest unchanged
- [ ] `test_cmd_add_rule_duplicate`: exits with code 1
- [ ] `test_cmd_add_rule_from_file`: imports content from file
- [ ] `test_cmd_remove_rule`: deletes file + manifest entry
- [ ] `test_cmd_remove_rule_dry_run`: file and manifest unchanged
- [ ] `test_cmd_remove_rule_not_found`: exits with code 1
- [ ] `test_cmd_set_valid`: updates manifest field
- [ ] `test_cmd_set_invalid`: exits with code 1
- [ ] `test_cmd_clean`: removes generated files
- [ ] `test_cmd_clean_dry_run`: no files removed
- [ ] `test_cmd_reconfigure_yes`: preserves defaults, triggers sync

## Phase 7: Run & Validate

- [ ] Run `pytest tests/ -v`, fix failures
- [ ] Verify all tests pass
- [ ] Commit
