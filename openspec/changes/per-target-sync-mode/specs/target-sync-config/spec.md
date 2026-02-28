## ADDED Requirements

### Requirement: Per-Target Sync Mode

Each entry in `active_targets.rules` and `active_targets.skills` SHALL support an optional object form that specifies a `sync_mode`:

- **String form** (backward compatible): `"cursor"` — uses default `sync_mode: "symlink"` for skills
- **Object form**: `{ "name": "claude", "sync_mode": "copy" }`

Valid `sync_mode` values:

- `symlink` (default) — create symlinks from the target skills directory to `~/.ai-agent/skills/`
- `copy` — recursively copy skill directories from `~/.ai-agent/skills/` to the target skills directory

The `sync_mode` applies to **skills only**. Rules are always generated in the agent-native format (no change).

#### Scenario: String entry defaults to symlink

- **WHEN** `active_targets.skills` contains `"codex"`
- **THEN** skills are synced to `~/.codex/skills/` using symlinks (current behavior)

#### Scenario: Object entry with copy mode

- **WHEN** `active_targets.skills` contains `{ "name": "claude", "sync_mode": "copy" }`
- **THEN** skills are synced to `~/.claude/skills/` by recursively copying each skill directory
- **AND** no symlinks are created

#### Scenario: Object entry defaults to symlink

- **WHEN** `active_targets.skills` contains `{ "name": "cursor" }` (no `sync_mode` specified)
- **THEN** skills are synced to `~/.cursor/skills/` using symlinks

### Requirement: Per-Target Conflict Strategy

Each entry in `active_targets.skills` SHALL support an optional `conflict_strategy`:

- `overwrite` (default) — replace existing non-managed content directly
- `archive` — move existing non-managed content to `~/.ai-agent/skills-archived/` before writing

The conflict strategy applies when a target skills directory contains a **real directory** (not a symlink) with the same name as a canonical skill. It does NOT apply to files already managed by sync (existing symlinks or previously-copied content).

#### Scenario: Overwrite replaces existing content

- **WHEN** `conflict_strategy` is `overwrite` (or not specified)
- **AND** the target skills directory contains a real directory `my-skill/` that is not a symlink
- **THEN** the existing directory is removed and replaced with the synced content (symlink or copy, per `sync_mode`)

#### Scenario: Archive preserves existing content

- **WHEN** `conflict_strategy` is `archive`
- **AND** the target skills directory contains a real directory `my-skill/` that is not a symlink and is not a previously-synced copy
- **THEN** the existing directory is moved to `~/.ai-agent/skills-archived/{target}-{name}/`
- **AND** the synced content is written in its place

#### Scenario: Managed content is always replaced

- **WHEN** the target skills directory contains a symlink or a previously-copied skill (identified by a `.sync-meta` marker file)
- **THEN** the content is replaced regardless of `conflict_strategy`
- **AND** no archiving occurs

### Requirement: Manifest Schema for Target Configuration

The manifest SHALL accept `active_targets.skills` and `active_targets.rules` as arrays of either strings or objects:

```json
{
  "active_targets": {
    "rules": ["cursor", "codex", "claude", "agents-md"],
    "skills": [
      "cursor",
      { "name": "codex", "sync_mode": "symlink" },
      { "name": "claude", "sync_mode": "copy", "conflict_strategy": "archive" }
    ]
  }
}
```

The system SHALL normalize all entries internally so that downstream logic always works with the object form.

#### Scenario: Mixed array entries

- **WHEN** `active_targets.skills` contains both string and object entries
- **THEN** string entries are normalized to `{ "name": "<value>", "sync_mode": "symlink", "conflict_strategy": "overwrite" }`
- **AND** object entries have missing fields filled with defaults

#### Scenario: Invalid sync_mode rejected

- **WHEN** an entry has `sync_mode: "hardlink"` (unsupported value)
- **THEN** the script exits with an error naming the invalid entry and listing valid values

### Requirement: Sync Meta Marker for Copied Skills

When skills are synced via `copy` mode, the system SHALL write a `.sync-meta` JSON file inside each copied skill directory containing:

- `source` — absolute path to the canonical skill directory
- `synced_at` — ISO timestamp of the copy
- `sync_mode` — `"copy"`

This marker is used to distinguish managed copies from user-created directories.

#### Scenario: Marker written on copy

- **WHEN** `sync_mode` is `copy` and a skill is synced
- **THEN** a `.sync-meta` file is created inside the copied skill directory

#### Scenario: Marker used for staleness detection

- **WHEN** `clean` runs and finds a skill directory with a `.sync-meta` file whose `source` points into `~/.ai-agent/skills/`
- **THEN** the directory is treated as managed and eligible for removal

#### Scenario: No marker for symlinks

- **WHEN** `sync_mode` is `symlink`
- **THEN** no `.sync-meta` file is created (symlinks are self-evident)
