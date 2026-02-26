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

## Install

```bash
git clone <repo-url> ~/.ai-agent
~/.ai-agent/scripts/sync_agent_rules.py init
```

No pip, no venv, no package manager. Requires Python 3.8+.

## Usage

```bash
# First-time setup: import existing rules and select targets
sync_agent_rules.py init

# Regenerate all agent configs from canonical source
sync_agent_rules.py sync

# Show current configuration and sync state
sync_agent_rules.py status

# Add a rule (creates file + manifest entry + syncs)
sync_agent_rules.py add-rule my-rule --description "My new rule"

# Add a rule from an existing file
sync_agent_rules.py add-rule my-rule --file ~/drafts/rule.md

# Remove a rule (deletes file + manifest entry + syncs)
sync_agent_rules.py remove-rule my-rule

# Update manifest fields from the CLI
sync_agent_rules.py set agents_md.paths "~/Code/**/AGENTS.md"
sync_agent_rules.py set agents_md.header "# My AGENTS Rules"

# Change which agents to sync to
sync_agent_rules.py reconfigure

# Preview changes without writing
sync_agent_rules.py sync --dry-run

# Show diffs against current files
sync_agent_rules.py sync --diff

# Sync a single agent
sync_agent_rules.py sync --only cursor
```

## Managing Rules

Add a rule in one step:

```bash
sync_agent_rules.py add-rule commit-strategy --description "Commit early and often"
```

This creates `rules/commit-strategy.md`, adds it to `manifest.json`, and runs sync.

Remove just as easily:

```bash
sync_agent_rules.py remove-rule commit-strategy
```

For advanced Cursor metadata, use flags:

```bash
sync_agent_rules.py add-rule my-rule \
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

## Flags

| Flag | Effect |
|------|--------|
| `--dry-run` | Preview changes without writing |
| `--diff` | Show unified diffs against current files |
| `--verbose` | Detailed logging |
| `--only <agent>` | Sync a single agent |
| `--yes` | Accept defaults, skip prompts |

## Verify It Worked

After running `init`, paste this prompt into any of your AI coding agents to confirm the sync is working:

> List the rules you can see in your system prompt or context. For each one, tell me its name and a one-line summary. I want to verify my synced rules are loaded.

You should see the same rules across every agent you synced to.

## Shell Alias

```bash
alias sync-ai-rules='~/.ai-agent/scripts/sync_agent_rules.py'
```
