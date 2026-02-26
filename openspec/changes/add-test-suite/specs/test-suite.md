# Delta for Test Suite

## ADDED Requirements

### Requirement: Test Isolation

All tests SHALL run against an isolated temporary directory. No test SHALL read from
or write to real agent config directories (`~/.cursor/`, `~/.codex/`, `~/.claude/`, etc.).

- Module-level path constants (`AGENT_DIR`, `RULES_DIR`, `SKILLS_DIR`, `BACKUPS_DIR`,
  `MANIFEST_PATH`) are monkeypatched to point into a pytest `tmp_path`
- Every entry in `AGENT_PATHS` is remapped so `rules_dir`, `rules_file`, and `skills_dir`
  resolve under the temporary home
- The `_current_backup` global is reset between tests

#### Scenario: Isolated filesystem

- GIVEN a test using the `fake_home` fixture
- WHEN any sync or init command runs
- THEN all file operations occur under `tmp_path`
- AND no files outside `tmp_path` are read or written

### Requirement: Unit Test Coverage

The suite SHALL include unit tests for internal functions that can be tested
without filesystem setup.

#### Scenario: parse_frontmatter with valid YAML

- GIVEN a string with `---` delimited frontmatter containing `alwaysApply: true`
- WHEN `parse_frontmatter` is called
- THEN it returns `({"alwaysApply": True}, body)` with correct bool coercion

#### Scenario: parse_frontmatter with no frontmatter

- GIVEN a string that does not start with `---`
- WHEN `parse_frontmatter` is called
- THEN it returns `({}, original_text)`

#### Scenario: build_frontmatter round-trip

- GIVEN metadata dict with bools, strings, and globs
- WHEN `build_frontmatter` is called and the result is parsed back
- THEN the original metadata is recovered

#### Scenario: is_generated_file positive

- GIVEN content starting with the generated header
- WHEN `is_generated_file` is called
- THEN it returns True

#### Scenario: is_generated_file negative

- GIVEN content that does not start with the generated header
- WHEN `is_generated_file` is called
- THEN it returns False

#### Scenario: Deduplicate exact match

- GIVEN two rules with the same ID and identical content from different sources
- WHEN `deduplicate_rules` is called
- THEN only the first rule is kept

#### Scenario: Deduplicate divergent content

- GIVEN two rules with the same ID but different content (similarity < 80%)
- WHEN `deduplicate_rules` is called with `--yes`
- THEN the first rule is kept (no interactive prompt)

### Requirement: Generator Test Coverage

The suite SHALL test each agent generator's output format.

#### Scenario: Cursor generator

- GIVEN a manifest with 2 rules and Cursor as an active target
- WHEN `gen_cursor` runs
- THEN 2 `.mdc` files are created in the Cursor rules directory
- AND each file has YAML frontmatter and the generated header
- AND stale generated `.mdc` files are removed

#### Scenario: Codex generator

- GIVEN a manifest with 2 rules
- WHEN `gen_codex` runs
- THEN `model-instructions.md` is created with the generated header
- AND each rule appears under a `## Rule:` section

#### Scenario: Concatenated generators (Claude, Gemini, Kiro)

- GIVEN a manifest with rules
- WHEN `gen_claude`, `gen_gemini`, or `gen_kiro` runs
- THEN the target file is created with the generated header and all rule content

#### Scenario: AGENTS.md generator

- GIVEN a manifest with rules and configured paths
- WHEN `gen_agents_md` runs
- THEN each configured path gets a file with a numbered rule summary

#### Scenario: Skill symlinks

- GIVEN canonical skills exist in `~/.ai-agent/skills/`
- WHEN `sync_skills` runs for a target directory
- THEN symlinks are created pointing to the canonical skill directories

### Requirement: Backup Test Coverage

The suite SHALL test the non-destructive backup system.

#### Scenario: init_backup creates directory

- WHEN `init_backup("test")` is called
- THEN a timestamped directory is created under `backups/`
- AND it contains a `meta.json` with the command name

#### Scenario: backup_file copies before overwrite

- GIVEN an existing file at a target path
- WHEN `backup_file` is called
- THEN the file is copied into the current backup directory

#### Scenario: backup_file skips in dry-run

- GIVEN `--dry-run` is active
- WHEN `backup_file` is called
- THEN no file is copied

#### Scenario: restore_from_backup

- GIVEN a backup containing files
- WHEN `restore_from_backup` is called with matching targets
- THEN the backed-up files are copied back to their original locations

#### Scenario: write_file triggers backup

- GIVEN an existing file at the target path
- WHEN `write_file` is called with new content
- THEN the original file is backed up before being overwritten

### Requirement: Integration Test Coverage

The suite SHALL test every CLI command end-to-end.

#### Scenario: status command

- GIVEN a seeded manifest with rules and targets
- WHEN `cmd_status` runs
- THEN output contains rule names, target names, and last synced date
- AND exit code is 0

#### Scenario: sync command

- GIVEN a seeded manifest with rules and active targets
- WHEN `cmd_sync` runs
- THEN generated files are created for each active target

#### Scenario: sync --dry-run

- GIVEN a seeded manifest
- WHEN `cmd_sync` runs with `--dry-run`
- THEN no agent config files are created or modified

#### Scenario: sync --only

- GIVEN a seeded manifest with multiple active targets
- WHEN `cmd_sync` runs with `--only cursor`
- THEN only Cursor files are generated

#### Scenario: add-rule

- GIVEN a seeded manifest
- WHEN `cmd_add_rule` runs with id "test-rule"
- THEN `rules/test-rule.md` is created
- AND manifest gains the new entry
- AND sync runs

#### Scenario: add-rule --dry-run

- GIVEN a seeded manifest
- WHEN `cmd_add_rule` runs with `--dry-run`
- THEN no files are created
- AND manifest is not modified

#### Scenario: add-rule duplicate

- GIVEN a rule "existing-rule" already in the manifest
- WHEN `cmd_add_rule` runs with id "existing-rule"
- THEN the script exits with code 1

#### Scenario: remove-rule

- GIVEN a rule "test-rule" exists
- WHEN `cmd_remove_rule` runs with id "test-rule"
- THEN `rules/test-rule.md` is deleted
- AND the manifest entry is removed

#### Scenario: remove-rule --dry-run

- GIVEN a rule "test-rule" exists
- WHEN `cmd_remove_rule` runs with `--dry-run`
- THEN the rule file still exists
- AND the manifest is not modified

#### Scenario: remove-rule nonexistent

- GIVEN no rule "fake" in the manifest
- WHEN `cmd_remove_rule` runs with id "fake"
- THEN the script exits with code 1

#### Scenario: set valid key

- GIVEN a seeded manifest
- WHEN `cmd_set` runs with key "agents_md.header" and value "# Test"
- THEN the manifest field is updated

#### Scenario: set invalid key

- GIVEN any manifest
- WHEN `cmd_set` runs with key "bad.key"
- THEN the script exits with code 1

#### Scenario: clean

- GIVEN generated files exist from a previous sync
- WHEN `cmd_clean` runs with `--yes`
- THEN generated files are removed
- AND backed-up originals are restored

#### Scenario: clean --dry-run

- GIVEN generated files exist
- WHEN `cmd_clean` runs with `--dry-run --yes`
- THEN no files are removed

#### Scenario: init --yes

- GIVEN source agent configs with non-generated rules
- WHEN `cmd_init` runs with `--yes`
- THEN rules are imported to `rules/`
- AND manifest is created
- AND sync runs

#### Scenario: reconfigure --yes

- GIVEN a seeded manifest
- WHEN `cmd_reconfigure` runs with `--yes`
- THEN targets remain unchanged (defaults accepted)
- AND sync runs
