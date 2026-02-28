## ADDED Requirements

### Requirement: MCP server entry point

The system SHALL provide an MCP server at `mcp/server.py` that communicates via `stdio` transport using the MCP Python SDK.

#### Scenario: Server starts and registers tools

- **WHEN** the server process is started via `python3 ~/.ai-agent/mcp/server.py`
- **THEN** it SHALL register all sync tools with the MCP runtime
- **AND** respond to MCP tool listing requests with typed schemas

#### Scenario: Server handles concurrent tool calls

- **WHEN** multiple tool calls arrive in sequence
- **THEN** each SHALL execute independently against the current manifest state
- **AND** no shared mutable state SHALL persist between calls

### Requirement: sync_status tool

The system SHALL expose a `sync_status` tool that returns the current sync state as structured JSON.

#### Scenario: Status with active rules and skills

- **WHEN** `sync_status` is called with no parameters
- **THEN** the response SHALL include:
  - `rules`: array of rule objects with `id`, `file`, `imported_from`, `alwaysApply`, `description`
  - `active_targets`: object with `rules` and `skills` arrays
  - `skills`: array of active skill names
  - `archived_skills`: array of archived skill names
  - `agents_md_paths`: array of configured AGENTS.md paths
  - `last_synced`: ISO timestamp string

### Requirement: sync_rules tool

The system SHALL expose a `sync_rules` tool that regenerates all agent configs.

#### Scenario: Full sync

- **WHEN** `sync_rules` is called with no parameters
- **THEN** the system SHALL run a full sync across all active targets
- **AND** return a summary with rule counts and skill counts per target

#### Scenario: Targeted sync

- **WHEN** `sync_rules` is called with `only: "codex"`
- **THEN** the system SHALL sync only the Codex target
- **AND** return counts for that target only

#### Scenario: Dry-run sync

- **WHEN** `sync_rules` is called with `dry_run: true`
- **THEN** no files SHALL be written
- **AND** the response SHALL indicate it was a dry run

### Requirement: sync_add_rule tool

The system SHALL expose a `sync_add_rule` tool that creates a new canonical rule.

#### Scenario: Add rule with description

- **WHEN** `sync_add_rule` is called with `id: "my-rule"` and `description: "My rule"`
- **THEN** a placeholder file SHALL be created at `rules/my-rule.md`
- **AND** a manifest entry SHALL be added
- **AND** sync SHALL run to propagate

#### Scenario: Add rule from file content

- **WHEN** `sync_add_rule` is called with `id: "my-rule"` and `content: "# My Rule\n\nRule content here"`
- **THEN** the provided content SHALL be written to `rules/my-rule.md`
- **AND** a manifest entry SHALL be added

#### Scenario: Add rule that already exists

- **WHEN** `sync_add_rule` is called with an `id` that already exists in the manifest
- **THEN** the tool SHALL return an error with a descriptive message

### Requirement: sync_remove_rule tool

The system SHALL expose a `sync_remove_rule` tool that removes a canonical rule.

#### Scenario: Remove existing rule

- **WHEN** `sync_remove_rule` is called with `id: "my-rule"`
- **THEN** the rule file SHALL be backed up and deleted
- **AND** the manifest entry SHALL be removed
- **AND** sync SHALL run to clean up generated files

#### Scenario: Remove non-existent rule

- **WHEN** `sync_remove_rule` is called with an `id` not in the manifest
- **THEN** the tool SHALL return an error

### Requirement: sync_set_config tool

The system SHALL expose a `sync_set_config` tool that updates manifest configuration.

#### Scenario: Set a config value

- **WHEN** `sync_set_config` is called with `key: "agents_md.paths"` and `value: "~/Code/**/AGENTS.md"`
- **THEN** the manifest SHALL be updated with the new value

#### Scenario: Set invalid key

- **WHEN** `sync_set_config` is called with an unsupported key
- **THEN** the tool SHALL return an error listing supported keys

### Requirement: sync_clean tool

The system SHALL expose a `sync_clean` tool that removes generated files and restores originals.

#### Scenario: Clean with backup restore

- **WHEN** `sync_clean` is called
- **THEN** generated rule files and skill symlinks SHALL be removed
- **AND** originals SHALL be restored from the most recent backup if available
- **AND** the response SHALL report counts of removed and restored items

### Requirement: sync_reconfigure tool

The system SHALL expose a `sync_reconfigure` tool that changes active sync targets.

#### Scenario: Update targets

- **WHEN** `sync_reconfigure` is called with `rule_targets: ["cursor", "codex"]` and `skill_targets: ["cursor"]`
- **THEN** the manifest SHALL be updated with the new targets
- **AND** sync SHALL run with the new configuration

### Requirement: sync_archive_skill tool

The system SHALL expose a `sync_archive_skill` tool that moves skills out of active sync.

#### Scenario: Archive one or more skills

- **WHEN** `sync_archive_skill` is called with `names: ["skill-a", "skill-b"]`
- **THEN** the skill directories SHALL be moved to `skills-archived/`
- **AND** sync SHALL run to remove stale symlinks
- **AND** the response SHALL list archived skills

#### Scenario: Archive non-existent skill

- **WHEN** `sync_archive_skill` is called with a name not in `skills/`
- **THEN** the tool SHALL return an error

### Requirement: sync_restore_skill tool

The system SHALL expose a `sync_restore_skill` tool that re-activates archived skills.

#### Scenario: Restore one or more skills

- **WHEN** `sync_restore_skill` is called with `names: ["skill-a"]`
- **THEN** the skill directory SHALL be moved from `skills-archived/` back to `skills/`
- **AND** sync SHALL run to create symlinks
- **AND** the response SHALL list restored skills

### Requirement: sync_list_archived tool

The system SHALL expose a `sync_list_archived` tool that lists archived skills.

#### Scenario: List with archived skills

- **WHEN** `sync_list_archived` is called
- **THEN** the response SHALL include an array of archived skill names

#### Scenario: List with no archived skills

- **WHEN** `sync_list_archived` is called and no skills are archived
- **THEN** the response SHALL include an empty array

### Requirement: Error handling

All tools SHALL return structured errors when operations fail.

#### Scenario: Operation error

- **WHEN** any tool encounters an error (missing rule, invalid parameter, filesystem error)
- **THEN** the response SHALL include an `error` field with a human-readable message
- **AND** the MCP error code SHALL be set appropriately

#### Scenario: stdout/stderr isolation

- **WHEN** any tool calls a `cmd_*` function that prints to stdout
- **THEN** the print output SHALL NOT interfere with the MCP stdio protocol
- **AND** captured output MAY be included in the response for debugging
