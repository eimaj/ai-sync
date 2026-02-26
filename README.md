# 🔄 ai-agent

![License: MIT](https://img.shields.io/badge/license-MIT-blue)
![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![Tests](https://img.shields.io/badge/tests-63%20passed-brightgreen)

> ⚠️ **Disclaimer:** This project was written with AI. Review before running -- it writes to agent config directories (`~/.cursor/`, `~/.codex/`, `~/.claude/`, etc.).

Sync AI coding assistant rules and skills from a single canonical source to multiple agents.

Edit rules once in `~/.ai-agent/rules/`, run `sync`, and every agent gets updated in its native format.

## 📑 Table of Contents

- [Supported Agents](#-supported-agents)
- [Quick Start](#-quick-start)
- [Nothing Is Destructive](#️-nothing-is-destructive)
- [Commands](#-commands)
- [AGENTS.md Paths](#-agentsmd-paths)
- [How It Works](#-how-it-works)
- [Directory Structure](#-directory-structure)
- [Reverting / Uninstalling](#-reverting--uninstalling)
- [Testing](#-testing)
- [Verify It Worked](#-verify-it-worked)

## 🤖 Supported Agents

| Agent | Rules Format | Skills |
|-------|-------------|--------|
| Cursor | Individual `.mdc` files with YAML frontmatter | Symlinks |
| Codex | Concatenated `model-instructions.md` | Symlinks |
| Claude Code | `CLAUDE.md` | -- |
| Gemini CLI | `GEMINI.md` | Symlinks |
| Kiro | `steering/conventions.md` | -- |
| Antigravity | -- | Symlinks |
| AGENTS.md | Condensed numbered list | -- |

## 🚀 Quick Start

### Prerequisites

Python 3.8+ is required. Check with `python3 --version`. If not installed:

- **macOS**: `brew install python3` or `xcode-select --install`
- **Ubuntu/Debian**: `sudo apt install python3`
- **Fedora**: `sudo dnf install python3`
- **Windows**: [python.org](https://www.python.org/downloads/) or `winget install Python.Python.3`

No pip, no venv, no dependencies -- the script uses only the Python standard library.

### Install & Setup

```bash
git clone <repo-url> ~/.ai-agent
~/.ai-agent/scripts/sync_agent_rules.py init
```

### 💡 Shell Alias (recommended)

The full path is long. Add this to your `~/.zshrc` or `~/.bashrc`:

```bash
alias sync-ai-rules='~/.ai-agent/scripts/sync_agent_rules.py'
```

All examples below use this alias.

## 🛡️ Nothing Is Destructive

This tool **never permanently deletes your files**. Every time `init` or `sync` overwrites a file in your agent config directories, the original is copied to a timestamped backup first. The same applies when `remove-rule` deletes a canonical rule file.

Backups are stored at `~/.ai-agent/backups/<timestamp>/files/`, mirroring the original path relative to your home directory.

Use `--verbose` with any command to see each backup as it happens.

## 📖 Commands

| Command | Description |
|---------|-------------|
| `init` | Import existing rules, select targets, first sync |
| `sync` | Regenerate all agent configs from canonical source |
| `status` | Show rules, targets, skills, and last sync time |
| `add-rule` | Create rule file + manifest entry + sync |
| `remove-rule` | Delete rule file + manifest entry + sync |
| `set` | Update manifest fields (e.g. `agents_md.paths`) |
| `clean` | Remove generated files and restore originals from backup |
| `reconfigure` | Change which agents to sync to |

### Everyday workflow

```bash
# See what's configured
sync-ai-rules status

# Push canonical rules to all agents
sync-ai-rules sync

# Preview before writing
sync-ai-rules --dry-run sync
```

### ➕ Adding & removing rules

```bash
# Add a rule (creates file + manifest entry + syncs)
sync-ai-rules add-rule my-rule --description "My new rule"

# Add from an existing file
sync-ai-rules add-rule my-rule --file ~/drafts/rule.md

# Advanced: Cursor metadata + agent exclusions
sync-ai-rules add-rule my-rule \
  --description "Short description" \
  --no-always-apply \
  --exclude "kiro,gemini"

# Remove a rule
sync-ai-rules remove-rule my-rule
```

### ⚙️ Configuration

```bash
# Set AGENTS.md output paths
sync-ai-rules set agents_md.paths "~/Code/**/AGENTS.md"

# Change sync targets
sync-ai-rules reconfigure
```

### 🔍 Flags

| Flag | Effect |
|------|--------|
| `--dry-run` | Preview changes without writing |
| `--diff` | Show unified diffs against current files |
| `--verbose` | Detailed logging (includes backup info) |
| `--only <agent>` | Sync a single agent |
| `--yes` | Accept defaults, skip prompts |

## 📋 AGENTS.md Paths

`AGENTS.md` is a cross-tool standard for embedding rules directly in a repository. Some tools read it automatically:

| Tool | Reads AGENTS.md |
|------|----------------|
| Codex | ✅ scans workspace for `AGENTS.md` files |
| Cursor | ✅ reads `AGENTS.md` in workspace root and subdirectories |
| Claude Code | ❌ uses `CLAUDE.md` instead |
| Gemini CLI | ❌ uses `GEMINI.md` instead |
| Kiro | ❌ uses `steering/` directory |

Place `AGENTS.md` files at the root of your workspaces so Codex and Cursor pick them up. Configure paths during `init`, or set them anytime:

```bash
# Single path
sync-ai-rules set agents_md.paths "~/Code/my-project/AGENTS.md"

# Multiple paths
sync-ai-rules set agents_md.paths "~/Code/project-a/AGENTS.md,~/Code/project-b/AGENTS.md"

# Wildcard -- writes to every existing AGENTS.md under ~/Code/
sync-ai-rules set agents_md.paths "~/Code/**/AGENTS.md"
```

Wildcards expand at sync time using Python's `glob`. A pattern like `~/Code/**/AGENTS.md` finds all existing `AGENTS.md` files recursively. If a path points to a directory instead of a file, `/AGENTS.md` is appended automatically. Non-glob paths that don't exist yet are created on sync.

## ⚡ How It Works

**`init`** scans your existing agent configs (Cursor `.mdc`, Codex `model-instructions.md`, etc.), deduplicates across sources, and lets you cherry-pick which rules and skills to import via interactive multi-select. It writes canonical plain-markdown files to `rules/`, copies shared skills to `skills/`, and creates `manifest.json`.

**`sync`** reads `manifest.json` and generates agent-native configs:

| Target | What it does |
|--------|-------------|
| **Cursor** | Wraps each rule in `.mdc` frontmatter, writes individual files |
| **Codex** | Concatenates rules with section headers into one file |
| **Claude/Gemini/Kiro** | Concatenates rules into a single markdown file |
| **AGENTS.md** | Writes a condensed numbered summary to configured paths |
| **Skills** | Creates symlinks from agent dirs to `~/.ai-agent/skills/` |

All generated files include a `# Generated from ~/.ai-agent/` header so the tool can detect and skip them during re-import.

## 📁 Directory Structure

```
~/.ai-agent/
├── scripts/sync_agent_rules.py   # The sync tool (committed)
├── README.md                     # This file (committed)
├── .gitignore                    # (committed)
├── openspec/                     # Planning artifacts (committed)
│
├── manifest.json                 # Your config (gitignored)
├── rules/                        # Your rules (gitignored)
├── skills/                       # Your skills (gitignored)
└── backups/                      # Auto-created backups (gitignored)
```

The script is version-controlled. Your personal rules, skills, config, and backups stay local.

## ⏪ Reverting / Uninstalling

To undo a sync and restore your original agent config files:

```bash
sync-ai-rules clean
```

This does three things:

1. 📋 Lists all generated rule files and skill symlinks it will remove
2. 🗑️ Removes them (identified by the `# Generated from ~/.ai-agent/` header)
3. ♻️ Restores the original files from the most recent backup

Preview first with `--dry-run`:

```bash
sync-ai-rules --dry-run clean
```

Files marked `<- will restore from backup` in the preview will be restored to their pre-sync state.

## 🧪 Testing

Install dev dependencies and run the suite:

```bash
pip install -r requirements-dev.txt
python3 -m pytest tests/ -v
```

Tests run in isolated temp directories -- they never touch your real agent configs.

### Pre-push hook

A git hook runs the full test suite before every push. To enable it after cloning:

```bash
git config core.hooksPath .githooks
```

## ✅ Verify It Worked

After running `init`, paste this into any of your AI coding agents:

> List the rules you can see in your system prompt or context. For each one, give me its name and a one-line summary.

You should see the same rules across every agent you synced to.
