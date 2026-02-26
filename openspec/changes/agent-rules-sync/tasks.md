# Tasks: Agent-Agnostic Rules Sync

## Phase 1: Scaffold and Repo Setup

- [ ] Create directory structure: `~/.ai-agent/scripts/`
- [ ] Create `.gitignore` (exclude `manifest.json`, `rules/`, `skills/`, `docs/`, `__pycache__/`)
- [ ] Initialize git repo: `git init`

## Phase 2: Script Core

- [ ] Create `scripts/sync_agent_rules.py` with shebang (`#!/usr/bin/env python3`), imports (stdlib only: `json`, `pathlib`, `argparse`, `shutil`, `difflib`, `dataclasses`), and constants (`AGENT_DIR`, `MANIFEST_PATH`, agent path mappings)
- [ ] Implement `argparse` CLI: `init`, `sync`, `reconfigure` subcommands with shared flags (`--dry-run`, `--diff`, `--verbose`, `--only`, `--yes`)
- [ ] Implement `multi_select()` prompt helper: numbered options, comma-separated input, returns list of selected IDs
- [ ] Implement `read_manifest()` and `write_manifest()` using stdlib `json`
- [ ] Implement `write_file()` utility that respects `--dry-run` and `--diff` flags
- [ ] Implement `parse_frontmatter()` for Cursor `.mdc` YAML frontmatter (minimal parser, flat key-value only, no external deps)

## Phase 3: Importers

- [ ] Implement `is_generated_file()`: check if file content starts with `# Generated from ~/.ai-agent/` header
- [ ] Implement `import_cursor()`: glob `~/.cursor/rules/*.mdc`, skip generated files, parse frontmatter, extract content and metadata, return `ImportedRule` list
- [ ] Implement `import_codex()`: read `~/.codex/model-instructions.md`, skip if generated, split on `## Source:` headers, return rules
- [ ] Implement `import_claude()`: read `~/.claude/CLAUDE.md`, skip if generated, split on `# ` headers, return rules
- [ ] Implement `import_gemini()`: read `~/.gemini/GEMINI.md`, skip if generated, split on `# ` headers, return rules
- [ ] Implement `import_kiro()`: glob `~/.kiro/steering/*.md`, skip generated files, one rule per file, return rules
- [ ] Implement `import_skills()`: scan source skills dir, skip symlinks and system dirs, copy real skill dirs to `~/.ai-agent/skills/`
- [ ] Implement `deduplicate_rules()`: compare by heading + `SequenceMatcher` ratio, exact match skips, similar flags for review, unique imports

## Phase 4: Generators

- [ ] Implement `gen_cursor()`: wrap each rule in `.mdc` frontmatter from manifest metadata, write individual files to `~/.cursor/rules/`, clean up stale generated `.mdc` files (have generated header but rule ID not in manifest), manage skill symlinks
- [ ] Implement `gen_codex()`: concatenate rules with `## Rule: {id}` headers, write `~/.codex/model-instructions.md`, manage skill symlinks (preserve `.system/`)
- [ ] Implement `gen_claude()`: concatenate rules, write `~/.claude/CLAUDE.md`
- [ ] Implement `gen_gemini()`: concatenate rules, write `~/.gemini/GEMINI.md`, manage skill symlinks
- [ ] Implement `gen_kiro()`: concatenate rules, write `~/.kiro/steering/conventions.md`
- [ ] Implement `gen_antigravity()`: manage skill symlinks in `~/.gemini/antigravity/skills/`
- [ ] Implement `gen_agents_md()`: write numbered list (`N. **{id}** -- {summary}`) to each path in `agents_md.paths`, deriving summary from `cursor.description` or first line of content (truncated to 120 chars)
- [ ] Implement `sync_skills()`: shared symlink logic used by all skill generators -- remove symlinks pointing into `~/.ai-agent/skills/`, create fresh ones, preserve non-symlink entries and symlinks pointing elsewhere

## Phase 5: Wire Up Modes

- [ ] Implement `cmd_init()`: source selection -> import -> dedup -> target selection -> write canonical files + manifest.json -> call `cmd_sync()`
- [ ] Implement `cmd_sync()`: read manifest.json -> resolve active targets -> run generators for each active target -> print summary
- [ ] Implement `cmd_reconfigure()`: re-prompt target selection -> update manifest.json `active_targets` -> call `cmd_sync()`

## Phase 6: Unit Tests (future)

> Not blocking v1 launch. Tracked here for follow-up.

- [ ] Add test harness using `tempfile.TemporaryDirectory` to isolate from real agent paths
- [ ] Test `parse_frontmatter()`: valid frontmatter, missing fields, empty content, no frontmatter
- [ ] Test `is_generated_file()`: positive match, partial match, no header
- [ ] Test `deduplicate_rules()`: exact match, similar match, unique
- [ ] Test each importer's parsing logic with fixture files

## Phase 7: Run Init and Validate

- [ ] Run `sync_agent_rules.py init`: select import sources and sync targets
- [ ] Verify rules imported to `~/.ai-agent/rules/` match source content
- [ ] Verify skills copied to `~/.ai-agent/skills/`
- [ ] Verify `manifest.json` has correct structure and metadata
- [ ] Verify Cursor `.mdc` files round-trip correctly (import -> canonical -> re-export)
- [ ] Verify Codex `model-instructions.md` content is correct
- [ ] Verify Claude, Gemini, Kiro target files created with all rules
- [ ] Verify skill symlinks resolve for all skill-capable agents
- [ ] Verify AGENTS.md files updated with condensed rules
- [ ] Verify `--dry-run` mode shows changes without writing

## Phase 8: Documentation and Initial Commit

- [ ] Write `~/.ai-agent/README.md` with architecture overview, install instructions, how to add/edit rules, how to run sync
- [ ] Verify `.gitignore` excludes personal content: `git status` should only show committed files
- [ ] Initial commit with script, README, .gitignore, and openspec artifacts
- [ ] Suggest shell alias: `alias sync-ai-rules='~/.ai-agent/scripts/sync_agent_rules.py'`
