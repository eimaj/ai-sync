# ai-agent

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

# Change which agents to sync to
sync_agent_rules.py reconfigure

# Preview changes without writing
sync_agent_rules.py sync --dry-run

# Show diffs against current files
sync_agent_rules.py sync --diff

# Sync a single agent
sync_agent_rules.py sync --only cursor
```

## Adding a Rule

1. Create `~/.ai-agent/rules/my-rule.md` with plain markdown content
2. Add an entry to `manifest.json`:

```json
{
  "id": "my-rule",
  "file": "my-rule.md",
  "imported_from": "manual",
  "cursor": {
    "alwaysApply": true,
    "description": "Short description for Cursor"
  }
}
```

3. Run `sync_agent_rules.py sync`

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

## How It Works

`init` imports rules from existing agent configs (Cursor `.mdc`, Codex `model-instructions.md`, etc.), deduplicates across sources, and writes canonical plain-markdown files to `rules/`. It also copies shared skills to `skills/` and creates `manifest.json` with metadata and target selection.

`sync` reads `manifest.json` and generates agent-native configs:
- **Cursor**: wraps each rule in `.mdc` frontmatter, writes individual files
- **Codex**: concatenates rules with section headers into one file
- **Claude/Gemini/Kiro**: concatenates rules into a single markdown file
- **AGENTS.md**: writes a condensed numbered summary
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

## Shell Alias

```bash
alias sync-ai-rules='~/.ai-agent/scripts/sync_agent_rules.py'
```
