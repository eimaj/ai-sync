## MODIFIED Requirements

### Requirement: Skill Symlinks

The system SHALL manage skill delivery for agents that support them (Cursor, Codex, Claude Code, Gemini CLI, Antigravity). Delivery mode is determined by the target's `sync_mode` configuration:

- **`symlink`** (default): Remove existing managed symlinks in the agent's skills dir that point into `~/.ai-agent/skills/`, then create fresh symlinks. Leave non-symlink entries (agent-native skills) untouched unless `conflict_strategy` is `overwrite`.
- **`copy`**: Remove existing managed copies (identified by `.sync-meta` marker), then recursively copy each canonical skill directory. Write a `.sync-meta` file inside each copy. Leave non-managed entries untouched unless `conflict_strategy` is `overwrite`.

#### Scenario: Symlink mode (default, unchanged behavior)

- **WHEN** a target has `sync_mode: "symlink"` (or no mode specified)
- **THEN** symlinks are created from the target skills directory to `~/.ai-agent/skills/<name>/`
- **AND** stale symlinks pointing into `~/.ai-agent/skills/` are removed
- **AND** non-symlink directories are left untouched

#### Scenario: Copy mode delivers real files

- **WHEN** a target has `sync_mode: "copy"`
- **THEN** each canonical skill directory is recursively copied to the target skills directory
- **AND** a `.sync-meta` marker file is written inside each copied directory
- **AND** stale copies (with `.sync-meta` pointing to removed canonical skills) are removed

#### Scenario: Copy mode updates changed content

- **WHEN** a target has `sync_mode: "copy"` and canonical skill content has changed since the last sync
- **THEN** the existing copy is removed and replaced with the updated content
- **AND** the `.sync-meta` timestamp is updated

### Requirement: Clean Mode

The system SHALL provide a `clean` subcommand that:

1. Find all generated rule files, skill symlinks, **and managed skill copies** across active targets
2. Remove generated rule files (identified by the generated header)
3. Remove skill symlinks pointing into `~/.ai-agent/skills/`
4. Remove skill copies containing a `.sync-meta` file whose `source` points into `~/.ai-agent/skills/`
5. Restore originals from the most recent backup (if available)
6. Leave canonical source in `~/.ai-agent/` untouched

#### Scenario: Clean removes symlinked skills

- **WHEN** `clean` runs and a target has symlinked skills
- **THEN** symlinks pointing into `~/.ai-agent/skills/` are removed

#### Scenario: Clean removes copied skills

- **WHEN** `clean` runs and a target has copied skills with `.sync-meta` markers
- **THEN** the copied skill directories are removed
- **AND** the `.sync-meta` markers are used to identify managed copies

### Requirement: Status Mode

The system SHALL provide a `status` subcommand that displays a read-only summary:

- All rules with their source, flags (`alwaysApply`, `globs`), and description
- Active targets for rules and skills, **including sync mode and conflict strategy for each target**
- Canonical skills count and names
- Configured AGENTS.md paths
- Last sync timestamp
- Archived skills

#### Scenario: Status shows per-target config

- **WHEN** the user runs `status`
- **THEN** each skills target is displayed with its sync mode and conflict strategy
- **AND** the format distinguishes between symlink and copy targets
