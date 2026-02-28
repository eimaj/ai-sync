## Context

`sync_agent_rules.py` currently manages skills via symlinks exclusively. The `sync_skills()` function creates symlinks from each target's skills directory back to `~/.ai-agent/skills/<name>/`. This works well for local agents (Cursor, Codex) but fails for agents running in sandboxed, remote, or containerized environments where symlinks don't resolve or aren't supported. The manifest currently stores `active_targets.skills` and `active_targets.rules` as flat string arrays, with no per-target configuration.

The script is ~1700 lines of Python with zero external dependencies. All changes must preserve that constraint.

## Goals / Non-Goals

**Goals:**

- Allow each target to independently choose symlink or copy mode for skills
- Allow each target to choose archive or overwrite when encountering existing non-managed content
- Manage all configuration declaratively from `manifest.json`
- Maintain full backward compatibility — existing manifests continue to work without changes
- Keep the script dependency-free (stdlib only)

**Non-Goals:**

- Per-target config for **rules** (rules are always generated in agent-native format; copy vs symlink doesn't apply)
- Partial/selective skill sync (e.g., only sync certain skills to certain targets)
- Real-time file watching or auto-sync
- Conflict resolution beyond archive/overwrite (no merge, no interactive diff)

## Decisions

### 1. Manifest schema: mixed arrays with normalization

**Choice**: Allow `active_targets.skills` (and `active_targets.rules`) to contain either strings or objects, normalized at parse time.

**Alternatives considered**:
- Separate `target_config` section — adds indirection, harder to scan visually
- Always-object form — breaks backward compatibility

**Rationale**: Mixed arrays are the simplest migration path. A `_normalize_targets()` helper runs at manifest load time, converting `"cursor"` to `{"name": "cursor", "sync_mode": "symlink", "conflict_strategy": "overwrite"}`. Downstream code always sees the normalized form.

### 2. Sync mode: symlink vs copy

**Choice**: `sync_mode` field on skill target entries (`"symlink"` | `"copy"`).

Symlink mode is unchanged from today. Copy mode uses `shutil.copytree()` with `dirs_exist_ok=True` and writes a `.sync-meta` JSON marker inside each copied directory.

**Rationale**: `shutil.copytree` is stdlib, handles recursive copy including nested files, and `dirs_exist_ok` (Python 3.8+) avoids needing to pre-delete.

### 3. `.sync-meta` marker file

**Choice**: A JSON file placed inside each copied skill directory.

```json
{
  "source": "/Users/user/.ai-agent/skills/my-skill",
  "synced_at": "2026-02-28T12:00:00Z",
  "sync_mode": "copy"
}
```

**Alternatives considered**:
- Central tracking file in `~/.ai-agent/` — harder to detect during clean, doesn't survive if the tracking file is deleted
- Filename-based convention — fragile, clutters the skill directory listing

**Rationale**: Co-located markers are self-describing. `clean` can scan any target dir, find `.sync-meta` files, and determine whether a directory is managed. The marker is small and hidden by convention (dotfile).

### 4. Conflict strategy: archive vs overwrite

**Choice**: `conflict_strategy` field (`"archive"` | `"overwrite"`).

- `overwrite` (default): Remove and replace. Current behavior.
- `archive`: Move existing non-managed, non-symlink directories to `~/.ai-agent/skills-archived/{target}-{name}/` before writing.

Only applies to content that is **not** already managed (no `.sync-meta`, not a symlink pointing to canonical). Managed content is always replaced silently.

**Rationale**: Archive reuses the existing `skills-archived/` infrastructure. The `{target}-{name}` naming prevents collisions when archiving the same skill name from different targets.

### 5. `sync_skills()` refactor

**Choice**: Split `sync_skills()` into:
- `_sync_skills_symlink(target_dir, args)` — current logic, extracted
- `_sync_skills_copy(target_dir, args)` — new copy logic
- `sync_skills(target_dir, target_config, args)` — dispatcher that reads `sync_mode` and `conflict_strategy` from `target_config`

**Rationale**: Clean separation. Each mode has distinct cleanup and creation logic. The dispatcher keeps call sites simple — generators pass `target_config` from the normalized manifest.

### 6. Rules targets: no sync_mode

**Choice**: `active_targets.rules` entries can be objects with `name` (for future extension) but `sync_mode` and `conflict_strategy` are ignored. Rules are always generated in the agent-native format.

**Rationale**: Rules are never symlinked — Cursor needs `.mdc` with frontmatter, Codex needs concatenated markdown, etc. Copy vs symlink doesn't apply.

## Risks / Trade-offs

- **[Risk] Copy drift**: Copied skills can be edited in-place at the target, diverging from canonical. **Mitigation**: `sync` always replaces managed copies (detected via `.sync-meta`). Users editing copies will lose changes on next sync — this is by design and matches symlink behavior where edits to the link target affect all links.

- **[Risk] `.sync-meta` deletion**: If a user deletes `.sync-meta` from a copied skill, `clean` won't recognize it as managed. **Mitigation**: Acceptable edge case. The directory becomes "user-owned" and won't be touched — same as any other non-managed directory.

- **[Risk] Large skill directories**: Copy mode is slower than symlinks for large skill trees. **Mitigation**: Skills are small (markdown + a few files). Not a practical concern for current use cases.

- **[Trade-off] Archive naming with target prefix**: `{target}-{name}` in archive dir means restoring requires knowing the target. **Mitigation**: Archive is a safety net, not a primary workflow. `restore-skill` continues to work for canonically archived skills.
