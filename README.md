# ai-agent

> **Disclaimer:** This project was written with AI. It may contain bugs, incomplete logic, or assumptions that don't hold on your machine. Review before running -- it writes to agent config directories (`~/.cursor/`, `~/.codex/`, `~/.claude/`, etc.).

Sync AI coding assistant rules and skills from a single canonical source to multiple agents.

Edit rules once in `~/.ai-agent/rules/`, run `sync`, and every agent gets updated in its native format.

## Supported Agents

| Agent | Rules Format | Skills |
|-------|-------------|--------|
| Cursor | Individual `.mdc` files with YAML frontmatter | Symlinks |
| Codex | Concatenated `model-instructions.md` | Symlinks |
| Claude Code | `CLAUDE.md` | -- |
| Gemini CLI | `GEMINI.md` | Symlinks |
| Kiro | `steering/conventions.md` | -- |
| Antigravity | -- | Symlinks |
| AGENTS.md | Condensed numbered list | -- |

## Prerequisites

Python 3.8+ is required. Check with `python3 --version`. If not installed:

- **macOS**: `brew install python3` or `xcode-select --install` (includes Python)
- **Ubuntu/Debian**: `sudo apt install python3`
- **Fedora**: `sudo dnf install python3`
- **Windows**: Download from [python.org](https://www.python.org/downloads/) or `winget install Python.Python.3`

No pip, no venv, no package manager needed -- the script uses only the Python standard library.

## Install

```bash
git clone <repo-url> ~/.ai-agent
~/.ai-agent/scripts/sync_agent_rules.py init
```

## Usage

```bash
# First-time setup: import existing rules and select targets
~/.ai-agent/scripts/sync_agent_rules.py init

# Regenerate all agent configs from canonical source
~/.ai-agent/scripts/sync_agent_rules.py sync

# Show current configuration and sync state
~/.ai-agent/scripts/sync_agent_rules.py status

# Add a rule (creates file + manifest entry + syncs)
~/.ai-agent/scripts/sync_agent_rules.py add-rule my-rule --description "My new rule"

# Add a rule from an existing file
~/.ai-agent/scripts/sync_agent_rules.py add-rule my-rule --file ~/drafts/rule.md

# Remove a rule (deletes file + manifest entry + syncs)
~/.ai-agent/scripts/sync_agent_rules.py remove-rule my-rule

# Update manifest fields from the CLI
~/.ai-agent/scripts/sync_agent_rules.py set agents_md.paths "~/Code/**/AGENTS.md"
~/.ai-agent/scripts/sync_agent_rules.py set agents_md.header "# My AGENTS Rules"

# Change which agents to sync to
~/.ai-agent/scripts/sync_agent_rules.py reconfigure

# Preview changes without writing
~/.ai-agent/scripts/sync_agent_rules.py --dry-run sync

# Show diffs against current files
~/.ai-agent/scripts/sync_agent_rules.py --diff sync

# Sync a single agent
~/.ai-agent/scripts/sync_agent_rules.py --only cursor sync
```

## Managing Rules

Add a rule in one step:

```bash
~/.ai-agent/scripts/sync_agent_rules.py add-rule commit-strategy --description "Commit early and often"
```

This creates `rules/commit-strategy.md`, adds it to `manifest.json`, and runs sync.

Remove just as easily:

```bash
~/.ai-agent/scripts/sync_agent_rules.py remove-rule commit-strategy
```

For advanced Cursor metadata, use flags:

```bash
~/.ai-agent/scripts/sync_agent_rules.py add-rule my-rule \
  --description "Short description" \
  --no-always-apply \
  --exclude "kiro,gemini"
```

## Directory Structure

```
~/.ai-agent/
├── scripts/sync_agent_rules.py   # The sync tool (committed)
├── README.md                     # This file (committed)
├── .gitignore                    # (committed)
├── openspec/                     # Planning artifacts (committed)
│
├── manifest.json                 # Your config (gitignored)
├── rules/                        # Your rules (gitignored)
└── skills/                       # Your skills (gitignored)
```

The script is version-controlled. Your personal rules, skills, and config stay local.

## Commands

| Command | Description |
|---------|-------------|
| `init` | Import existing rules, select targets, first sync |
| `sync` | Regenerate all agent configs from canonical source |
| `status` | Show rules, targets, skills, and last sync time |
| `add-rule` | Create rule file + manifest entry + sync |
| `remove-rule` | Delete rule file + manifest entry + sync |
| `set` | Update manifest fields (e.g. `agents_md.paths`) |
| `clean` | Remove all generated files and skill symlinks |
| `reconfigure` | Change which agents to sync to |

## How It Works

`init` imports rules from existing agent configs (Cursor `.mdc`, Codex `model-instructions.md`, etc.), deduplicates across sources, and lets you cherry-pick which rules and skills to import via interactive multi-select. It writes canonical plain-markdown files to `rules/`, copies shared skills to `skills/`, and creates `manifest.json`.

`sync` reads `manifest.json` and generates agent-native configs:
- **Cursor**: wraps each rule in `.mdc` frontmatter, writes individual files
- **Codex**: concatenates rules with section headers into one file
- **Claude/Gemini/Kiro**: concatenates rules into a single markdown file
- **AGENTS.md**: writes a condensed numbered summary (supports `~/Code/**/AGENTS.md` globs)
- **Skills**: creates symlinks from agent dirs to `~/.ai-agent/skills/`

All generated files include a header so the tool can detect and skip them during re-import.

## AGENTS.md Paths

`AGENTS.md` is a cross-tool standard for embedding rules directly in a repository. Some tools read it automatically:

| Tool | Reads AGENTS.md |
|------|----------------|
| Codex | Yes -- scans workspace for `AGENTS.md` files |
| Cursor | Yes -- reads `AGENTS.md` in workspace root and subdirectories |
| Claude Code | No -- uses `CLAUDE.md` instead |
| Gemini CLI | No -- uses `GEMINI.md` instead |
| Kiro | No -- uses `steering/` directory |

Place `AGENTS.md` files at the root of your workspaces so Codex and Cursor pick them up. Configure paths during `init`, or set them anytime:

```bash
# Single path
~/.ai-agent/scripts/sync_agent_rules.py set agents_md.paths "~/Code/my-project/AGENTS.md"

# Multiple paths
~/.ai-agent/scripts/sync_agent_rules.py set agents_md.paths "~/Code/project-a/AGENTS.md,~/Code/project-b/AGENTS.md"

# Wildcard -- writes to every existing AGENTS.md under ~/Code/
~/.ai-agent/scripts/sync_agent_rules.py set agents_md.paths "~/Code/**/AGENTS.md"
```

Wildcards use Python's `glob` and expand at sync time. A pattern like `~/Code/**/AGENTS.md` finds all existing `AGENTS.md` files recursively under `~/Code/`. If a path points to a directory instead of a file, `/AGENTS.md` is appended automatically. Non-glob paths that don't exist yet are created on sync.

## Flags

| Flag | Effect |
|------|--------|
| `--dry-run` | Preview changes without writing |
| `--diff` | Show unified diffs against current files |
| `--verbose` | Detailed logging |
| `--only <agent>` | Sync a single agent |
| `--yes` | Accept defaults, skip prompts |

## Nothing Is Destructive

This tool never permanently deletes your files. Every time `init` or `sync` overwrites a file in your agent config directories (`~/.cursor/rules/`, `~/.codex/`, `~/.claude/`, etc.), the original is copied to a timestamped backup first. The same applies when `remove-rule` deletes a canonical rule file.

Backups are stored at:

```
~/.ai-agent/backups/<timestamp>/files/
```

Each backup mirrors the original path relative to your home directory. For example, `~/.cursor/rules/my-rule.mdc` is backed up to `~/.ai-agent/backups/20260226T120000Z/files/.cursor/rules/my-rule.mdc`.

Use `--verbose` with any command to see each backup as it happens.

## Reverting / Uninstalling

To undo a sync and restore your original agent config files:

```bash
~/.ai-agent/scripts/sync_agent_rules.py clean
```

This does three things:
1. Lists all generated rule files and skill symlinks it will remove
2. Removes them (generated files are identified by their `# Generated from ~/.ai-agent/` header)
3. Restores the original files from the most recent backup

Preview first with `--dry-run`:

```bash
~/.ai-agent/scripts/sync_agent_rules.py --dry-run clean
```

Files marked `<- will restore from backup` in the preview will be restored to their pre-sync state.

## Verify It Worked

After running `init`, paste this prompt into any of your AI coding agents to confirm the sync is working:

> List the rules you can see in your system prompt or context. For each one, tell me its name and a one-line summary. I want to verify my synced rules are loaded.

You should see the same rules across every agent you synced to.

## Shell Alias

Add to your `~/.zshrc` or `~/.bashrc` to skip the full path:

```bash
alias sync-ai-rules='~/.ai-agent/scripts/sync_agent_rules.py'
```

Then use `sync-ai-rules sync`, `sync-ai-rules status`, etc.
