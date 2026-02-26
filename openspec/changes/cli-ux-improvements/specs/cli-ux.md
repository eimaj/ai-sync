# Delta for CLI UX

## ADDED Requirements

### Requirement: Status Command

The system SHALL provide a `status` subcommand that displays a read-only summary:

- List of rules with ID, source, and Cursor metadata (alwaysApply, description)
- Active rule targets and skill targets
- Count of skills in the canonical directory
- Configured AGENTS.md paths
- Last sync timestamp

#### Scenario: Status with configured manifest

- GIVEN a manifest with rules, targets, and skills
- WHEN the user runs `status`
- THEN a formatted summary is printed to stdout
- AND no files are modified

#### Scenario: Status without manifest

- GIVEN no `manifest.json` exists
- WHEN the user runs `status`
- THEN the script exits with an error directing the user to run `init`

### Requirement: Add Rule Command

The system SHALL provide an `add-rule` subcommand that creates a rule in one step:

- Accepts positional `id` argument
- Optional `--description` for Cursor metadata
- Optional `--always-apply` flag (defaults to true)
- Optional `--file` to import content from an existing file
- Optional `--exclude` for comma-separated agent exclusions
- Creates `rules/{id}.md` with content (from `--file`, stdin, or empty placeholder)
- Adds entry to `manifest.json` rules array
- Runs sync automatically

#### Scenario: Add rule with description

- GIVEN a configured manifest
- WHEN the user runs `add-rule my-rule --description "My rule" --always-apply`
- THEN `rules/my-rule.md` is created
- AND `manifest.json` gains a new rule entry with cursor metadata
- AND sync runs to propagate to all active targets

#### Scenario: Add rule from file

- GIVEN a markdown file at `/tmp/rule.md`
- WHEN the user runs `add-rule my-rule --file /tmp/rule.md`
- THEN `rules/my-rule.md` is created with the content from `/tmp/rule.md`

#### Scenario: Add duplicate rule

- GIVEN `rules/my-rule.md` already exists
- WHEN the user runs `add-rule my-rule`
- THEN the script exits with an error indicating the rule already exists

### Requirement: Remove Rule Command

The system SHALL provide a `remove-rule` subcommand that deletes a rule in one step:

- Accepts positional `id` argument
- Removes `rules/{id}.md`
- Removes the matching entry from `manifest.json` rules array
- Runs sync automatically (Cursor stale-file cleanup removes the orphaned `.mdc`)

#### Scenario: Remove existing rule

- GIVEN a rule `my-rule` exists in the manifest and rules directory
- WHEN the user runs `remove-rule my-rule`
- THEN `rules/my-rule.md` is deleted
- AND the manifest entry is removed
- AND sync runs to update all active targets

#### Scenario: Remove nonexistent rule

- GIVEN no rule with id `fake-rule` exists
- WHEN the user runs `remove-rule fake-rule`
- THEN the script exits with an error

### Requirement: Set Command

The system SHALL provide a `set` subcommand for updating manifest fields:

- Accepts positional `key` (dotted path) and `value` arguments
- Supported keys: `agents_md.paths`, `agents_md.header`, `agents_md.preamble`
- Array fields (paths) are split on commas
- Scalar fields are set directly
- Writes updated manifest

#### Scenario: Set AGENTS.md paths

- GIVEN a configured manifest
- WHEN the user runs `set agents_md.paths "~/Code/AGENTS.md,~/projects/AGENTS.md"`
- THEN `manifest.json` `agents_md.paths` is updated to the two-element array
- AND the manifest is written to disk

#### Scenario: Set unsupported key

- GIVEN any manifest
- WHEN the user runs `set foo.bar "value"`
- THEN the script exits with an error listing supported keys

### Requirement: Wildcard AGENTS.md Paths

The system SHALL support glob patterns in `agents_md.paths`:

- Patterns containing `*`, `?`, or `[` are expanded using filesystem glob
- Non-glob paths are written directly (existing behavior)
- If a glob pattern matches zero files, a warning is logged

#### Scenario: Recursive wildcard

- GIVEN `agents_md.paths` contains `~/Code/**/AGENTS.md`
- AND `~/Code/project-a/AGENTS.md` and `~/Code/project-b/AGENTS.md` exist
- WHEN sync runs
- THEN both files are written with the condensed rules summary

#### Scenario: No matches

- GIVEN `agents_md.paths` contains `~/empty/**/AGENTS.md`
- AND no matching files exist
- WHEN sync runs
- THEN a warning is logged and no files are written for that pattern

### Requirement: Interactive Multi-Select

The system SHALL provide an interactive terminal UI for multi-select prompts:

- Arrow keys (up/down) move the cursor
- Space toggles selection on the current item
- `a` toggles all items
- Enter confirms the selection
- `q` or Ctrl-C aborts
- Defaults from the `defaults` parameter are pre-selected
- Uses stdlib `curses` (no external dependencies)

#### Scenario: Interactive mode

- GIVEN stdin is a TTY and `--yes` is not set
- WHEN a multi-select prompt is displayed
- THEN the user can navigate with arrow keys and toggle with space

#### Scenario: Non-interactive fallback

- GIVEN stdin is not a TTY, or `curses` is unavailable, or `--yes` is set
- WHEN a multi-select prompt is triggered
- THEN the existing comma-separated number input is used (or defaults auto-accepted)

## MODIFIED Requirements

### Requirement: Output Formatting

Output SHALL be structured with clear sections and summary counts.
(Previously: per-file logging with `[verbose]` prefix for all symlink operations)

- Section headers with horizontal rules separate rule sync, skill sync, and summary
- Per-agent output shows agent name and rule/skill count on one line
- Per-file detail (individual writes, symlink operations) only shown under `--verbose`
- `[dry-run]` shows a single summary line per agent, not per file
- Summary line at end shows total targets synced
