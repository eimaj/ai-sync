# Tasks: Agent-Agnostic Rules Sync

## Phase 1: Scaffold and Repo Setup

- [x] Create directory structure: `~/.ai-agent/scripts/`
- [x] Create `.gitignore` (exclude `manifest.json`, `rules/`, `skills/`, `docs/`, `__pycache__/`)
- [x] Initialize git repo: `git init`

## Phase 2: Script Core

- [x] Create `scripts/sync_agent_rules.py` with shebang (`#!/usr/bin/env python3`), imports (stdlib only: `json`, `pathlib`, `argparse`, `shutil`, `difflib`, `dataclasses`), and constants (`AGENT_DIR`, `MANIFEST_PATH`, agent path mappings)
- [x] Implement `argparse` CLI: `init`, `sync`, `reconfigure` subcommands with shared flags (`--dry-run`, `--diff`, `--verbose`, `--only`, `--yes`)
- [x] Implement `multi_select()` prompt helper: numbered options, comma-separated input, returns list of selected IDs
- [x] Implement `read_manifest()` and `write_manifest()` using stdlib `json`
- [x] Implement `write_file()` utility that respects `--dry-run` and `--diff` flags
- [x] Implement `parse_frontmatter()` for Cursor `.mdc` YAML frontmatter (minimal parser, flat key-value only, no external deps)

## Phase 3: Importers

- [x] Implement `is_generated_file()`: check if file content starts with `# Generated from ~/.ai-agent/` header
- [x] Implement `import_cursor()`: glob `~/.cursor/rules/*.mdc`, skip generated files, parse frontmatter, extract content and metadata, return `ImportedRule` list
- [x] Implement `import_codex()`: read `~/.codex/model-instructions.md`, skip if generated, split on `## Source:` headers, return rules
- [x] Implement `import_claude()`: read `~/.claude/CLAUDE.md`, skip if generated, split on `# ` headers, return rules
- [x] Implement `import_gemini()`: read `~/.gemini/GEMINI.md`, skip if generated, split on `# ` headers, return rules
- [x] Implement `import_kiro()`: glob `~/.kiro/steering/*.md`, skip generated files, one rule per file, return rules
- [x] Implement `import_skills()`: scan source skills dir, skip symlinks and system dirs, copy real skill dirs to `~/.ai-agent/skills/`
- [x] Implement `deduplicate_rules()`: compare by heading + `SequenceMatcher` ratio, exact match skips, similar flags for review, unique imports

## Phase 4: Generators

- [x] Implement `gen_cursor()`: wrap each rule in `.mdc` frontmatter from manifest metadata, write individual files to `~/.cursor/rules/`, clean up stale generated `.mdc` files (have generated header but rule ID not in manifest), manage skill symlinks
- [x] Implement `gen_codex()`: concatenate rules with `## Rule: {id}` headers, write `~/.codex/model-instructions.md`, manage skill symlinks (preserve `.system/`)
- [x] Implement `gen_claude()`: concatenate rules, write `~/.claude/CLAUDE.md`
- [x] Implement `gen_gemini()`: concatenate rules, write `~/.gemini/GEMINI.md`, manage skill symlinks
- [x] Implement `gen_kiro()`: concatenate rules, write `~/.kiro/steering/conventions.md`
- [x] Implement `gen_antigravity()`: manage skill symlinks in `~/.gemini/antigravity/skills/`
- [x] Implement `gen_agents_md()`: write numbered list (`N. **{id}** -- {summary}`) to each path in `agents_md.paths`, deriving summary from `cursor.description` or first line of content (truncated to 120 chars)
- [x] Implement `sync_skills()`: shared symlink logic used by all skill generators -- remove symlinks pointing into `~/.ai-agent/skills/`, create fresh ones, preserve non-symlink entries and symlinks pointing elsewhere

## Phase 5: Wire Up Modes

- [x] Implement `cmd_init()`: source selection -> import -> dedup -> target selection -> write canonical files + manifest.json -> call `cmd_sync()`
- [x] Implement `cmd_sync()`: read manifest.json -> resolve active targets -> run generators for each active target -> print summary
- [x] Implement `cmd_reconfigure()`: re-prompt target selection -> update manifest.json `active_targets` -> call `cmd_sync()`

## Phase 6: Unit Tests (future)

> Not blocking v1 launch. Tracked here for follow-up.

- [ ] Add test harness using `tempfile.TemporaryDirectory` to isolate from real agent paths
- [ ] Test `parse_frontmatter()`: valid frontmatter, missing fields, empty content, no frontmatter
- [ ] Test `is_generated_file()`: positive match, partial match, no header
- [ ] Test `deduplicate_rules()`: exact match, similar match, unique
- [ ] Test each importer's parsing logic with fixture files

## Phase 7: Run Init and Validate

- [x] Run `sync_agent_rules.py init`: select import sources and sync targets
- [x] Verify rules imported to `~/.ai-agent/rules/` match source content
- [x] Verify skills copied to `~/.ai-agent/skills/`
- [x] Verify `manifest.json` has correct structure and metadata
- [x] Verify Cursor `.mdc` files round-trip correctly (import -> canonical -> re-export)
- [x] Verify Codex `model-instructions.md` content is correct
- [x] Verify Claude, Gemini, Kiro target files created with all rules
- [x] Verify skill symlinks resolve for all skill-capable agents
- [x] Verify AGENTS.md files updated with condensed rules
- [x] Verify `--dry-run` mode shows changes without writing

## Phase 8: Documentation and Initial Commit

- [x] Write `~/.ai-agent/README.md` with architecture overview, install instructions, how to add/edit rules, how to run sync
- [x] Verify `.gitignore` excludes personal content: `git status` should only show committed files
- [x] Initial commit with script, README, .gitignore, and openspec artifacts
- [x] Suggest shell alias: `alias sync-ai-rules='~/.ai-agent/scripts/sync_agent_rules.py'`

## Phase 9: Cleanup and New Features

- [ ] Remove `SKIP_SKILL_DIRS` and `SKIP_SKILL_PREFIXES` constants (set to empty)
- [ ] Add `archive-skill` command: accept multiple names, `--dry-run`, `--list`
- [ ] Add `restore-skill` command: accept multiple names, `--dry-run`
- [ ] Update `status` to show archived skill count
