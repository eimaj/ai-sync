# Proposal: Add Test Suite

## Problem

All testing of `sync_agent_rules.py` is manual. After each change, every CLI command must be run by hand to verify nothing is broken. This is slow, error-prone, and has already missed bugs (e.g., `add-rule --dry-run` creating files on disk).

The script writes to real agent config directories (`~/.cursor/rules/`, `~/.codex/`, etc.), making ad-hoc testing risky -- a broken sync can overwrite or delete user files.

## Solution

Add a pytest test suite with full filesystem isolation. Every test runs against a temporary directory structure, never touching real agent configs. The suite covers:

1. **Unit tests** for internal functions: frontmatter parsing, deduplication, backup system
2. **Integration tests** for every CLI command: status, sync, add-rule, remove-rule, set, clean, init, reconfigure
3. **Flag coverage**: `--dry-run`, `--verbose`, `--diff`, `--only`, `--yes`
4. **Error cases**: duplicates, missing rules, invalid keys, bad agent names

## Scope

### In scope

- pytest as a dev-only dependency (`requirements-dev.txt`)
- Filesystem isolation via monkeypatched module-level path constants
- Unit tests for `parse_frontmatter`, `build_frontmatter`, `deduplicate_rules`, `is_generated_file`, `_rule_preview`
- Generator tests for each agent output format (Cursor `.mdc`, Codex, Claude, Gemini, Kiro, AGENTS.md)
- Backup system tests (init, backup, restore, write_file/remove_file integration)
- Integration tests for all 8 CLI commands with flag variations
- Error case coverage matching manual testing

### Out of scope

- curses UI testing (requires a real terminal)
- CI/CD pipeline setup
- Performance or load testing
- Test coverage reporting

## Success Criteria

- `pytest tests/ -v` passes with zero failures
- Every CLI command has at least one happy-path and one error-case test
- `--dry-run` tests verify no files are created or modified
- No test touches real agent config directories
- Zero runtime dependencies added (pytest is dev-only)
