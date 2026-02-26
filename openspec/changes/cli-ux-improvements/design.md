# Design: CLI UX Improvements

All changes are in `scripts/sync_agent_rules.py`. No new files. No new dependencies.

## 1. Subcommand Registration

Extend `build_parser()` with four new subparsers:

```python
# status
sub.add_parser("status", help="Show current configuration and sync state")

# add-rule
add_p = sub.add_parser("add-rule", help="Add a new rule")
add_p.add_argument("id", help="Rule identifier (used as filename)")
add_p.add_argument("--description", default="", help="Cursor description")
add_p.add_argument("--always-apply", action="store_true", default=True)
add_p.add_argument("--no-always-apply", action="store_true")
add_p.add_argument("--file", type=str, help="Import content from file")
add_p.add_argument("--exclude", type=str, default="", help="Comma-separated agents to exclude")

# remove-rule
rm_p = sub.add_parser("remove-rule", help="Remove a rule")
rm_p.add_argument("id", help="Rule identifier to remove")

# set
set_p = sub.add_parser("set", help="Update a manifest field")
set_p.add_argument("key", help="Dotted key path (e.g. agents_md.paths)")
set_p.add_argument("value", help="New value (arrays comma-separated)")
```

Route in `main()` via `if/elif` chain (Python 3.9 compat).

## 2. cmd_status

Read manifest. Print formatted sections:

```
─── Rules (N) ───────────────────────────────────
  commit-strategy     cursor   alwaysApply  "Commit early and often..."
  no-rm-rf            cursor   alwaysApply  "Safe deletion"
  ...

─── Active Targets ──────────────────────────────
  Rules → cursor, codex, claude, gemini, kiro, agents-md
  Skills → cursor, codex, gemini, antigravity

─── Skills (N) ──────────────────────────────────
  openspec, create-rule, github-cli, ...

─── AGENTS.md Paths ─────────────────────────────
  ~/Code/AGENTS.md

─── Last Synced ─────────────────────────────────
  2026-02-25
```

Implementation: format strings with fixed-width columns for rules table.

## 2b. Selective Import in cmd_init

After scanning sources and deduplicating, `cmd_init` presents two multi-select prompts
to let the user cherry-pick which rules and skills to import.

### Rule selection

Build options from the deduplicated `all_rules` list. Each option shows the rule id,
source agent, and a truncated content preview (first non-heading, non-empty line).

```python
def _rule_preview(rule: ImportedRule) -> str:
    for line in rule.content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped[:80]
    return "(empty)"

rule_options = [
    (rule.id, f"{rule.id:30s} [{rule.source:6s}]  {_rule_preview(rule)}")
    for rule in all_rules
]
all_rule_ids = [r.id for r in all_rules]

selected_rule_ids = multi_select(
    "Step 2b: Select rules to import:",
    rule_options,
    defaults=all_rule_ids,
    auto_accept=args.yes,
)
if not selected_rule_ids:
    print("  No rules selected. Aborted.")
    return
all_rules = [r for r in all_rules if r.id in selected_rule_ids]
```

### Skill selection

Build options from the deduplicated `all_skills` list. Each option shows the skill
directory name and its parent path.

```python
if all_skills:
    skill_options = [
        (s.name, f"{s.name:30s} [{s.parent}]")
        for s in all_skills
    ]
    all_skill_names = [s.name for s in all_skills]

    selected_skill_names = multi_select(
        "Step 2c: Select skills to import:",
        skill_options,
        defaults=all_skill_names,
        auto_accept=args.yes,
    )
    all_skills = [s for s in all_skills if s.name in selected_skill_names]
```

This replaces the old "Import summary" + "Proceed with import?" confirmation.
The multi-select serves as both review and confirmation -- selecting zero items aborts.

## 3. cmd_add_rule

```python
def cmd_add_rule(args):
    manifest = read_manifest()
    rule_id = args.id
    rule_file = f"{rule_id}.md"
    rule_path = RULES_DIR / rule_file

    # Guard: duplicate
    if rule_path.exists():
        print(f"Error: rule '{rule_id}' already exists at {rule_path}")
        sys.exit(1)

    # Content: from --file, or placeholder
    if args.file:
        content = Path(args.file).expanduser().read_text()
    else:
        content = f"# {rule_id.replace('-', ' ').title()}\n\nTODO: Add rule content.\n"

    rule_path.parent.mkdir(parents=True, exist_ok=True)
    rule_path.write_text(content)

    # Build manifest entry
    entry = {"id": rule_id, "file": rule_file, "imported_from": "manual"}
    always_apply = not args.no_always_apply
    cursor_meta = {"alwaysApply": always_apply}
    if args.description:
        cursor_meta["description"] = args.description
    entry["cursor"] = cursor_meta
    if args.exclude:
        entry["exclude"] = [x.strip() for x in args.exclude.split(",")]

    manifest["rules"].append(entry)
    write_manifest(manifest, args)
    cmd_sync(args, manifest=manifest)
```

## 4. cmd_remove_rule

```python
def cmd_remove_rule(args):
    manifest = read_manifest()
    rule_id = args.id
    rule_path = RULES_DIR / f"{rule_id}.md"

    # Guard: not found
    matches = [r for r in manifest["rules"] if r["id"] == rule_id]
    if not matches:
        print(f"Error: rule '{rule_id}' not found in manifest")
        sys.exit(1)

    # Remove file
    if rule_path.exists():
        rule_path.unlink()

    # Remove from manifest
    manifest["rules"] = [r for r in manifest["rules"] if r["id"] != rule_id]
    write_manifest(manifest, args)
    cmd_sync(args, manifest=manifest)
```

## 5. cmd_set

Supported keys with types:

| Key | Type | Split |
|-----|------|-------|
| `agents_md.paths` | array | `,` |
| `agents_md.header` | string | -- |
| `agents_md.preamble` | string | -- |

```python
SETTABLE_KEYS = {
    "agents_md.paths": ("agents_md", "paths", "array"),
    "agents_md.header": ("agents_md", "header", "scalar"),
    "agents_md.preamble": ("agents_md", "preamble", "scalar"),
}

def cmd_set(args):
    manifest = read_manifest()
    key = args.key
    if key not in SETTABLE_KEYS:
        print(f"Error: unsupported key '{key}'. Supported: {', '.join(SETTABLE_KEYS)}")
        sys.exit(1)
    section, field, kind = SETTABLE_KEYS[key]
    if kind == "array":
        manifest[section][field] = [v.strip() for v in args.value.split(",") if v.strip()]
    else:
        manifest[section][field] = args.value
    write_manifest(manifest, args)
```

## 6. Wildcard AGENTS.md Path Expansion

Modify `gen_agents_md()`:

```python
import glob as globmod

def _expand_agents_md_paths(paths: list[str]) -> list[Path]:
    result = []
    for p in paths:
        expanded = os.path.expanduser(p)
        if any(c in expanded for c in ("*", "?", "[")):
            matches = sorted(globmod.glob(expanded, recursive=True))
            if not matches:
                log(f"  Warning: glob '{p}' matched no files")
            for m in matches:
                result.append(Path(m))
        else:
            result.append(Path(expanded))
    return result
```

For wildcard paths, the glob is evaluated at sync time. Files that don't yet exist from non-glob paths are still created (existing write behavior).

## 7. Interactive Multi-Select (curses)

### Interface

```
Select rule targets: (↑↓ navigate, Space toggle, a toggle all, Enter confirm)

  [x] Cursor         (rules as .mdc + skill symlinks)
  [x] Codex          (rules as model-instructions.md + skill symlinks)
  [ ] Claude Code    (rules as CLAUDE.md)
  [x] Gemini CLI     (rules as GEMINI.md + skill symlinks)
> [ ] Kiro           (rules as steering/conventions.md)
  [x] AGENTS.md      (condensed rules for cross-tool standard)
```

### Implementation Strategy

```python
def _curses_multi_select(stdscr, prompt, options, defaults):
    curses.curs_set(0)
    selected = set(defaults or [])
    cursor = 0
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, prompt)
        stdscr.addstr(1, 0, "(↑↓ navigate, Space toggle, a all, Enter confirm, q abort)")
        for i, (oid, label) in enumerate(options):
            marker = "x" if oid in selected else " "
            prefix = ">" if i == cursor else " "
            stdscr.addstr(i + 3, 0, f"  {prefix} [{marker}] {label}")
        key = stdscr.getch()
        if key == curses.KEY_UP and cursor > 0:
            cursor -= 1
        elif key == curses.KEY_DOWN and cursor < len(options) - 1:
            cursor += 1
        elif key == ord(" "):
            oid = options[cursor][0]
            selected ^= {oid}
        elif key == ord("a"):
            all_ids = {o for o, _ in options}
            selected = set() if selected == all_ids else all_ids
        elif key in (curses.KEY_ENTER, 10, 13):
            return [o for o, _ in options if o in selected]
        elif key == ord("q") or key == 27:
            return list(defaults or [])
```

### Fallback Chain

```
multi_select():
  if auto_accept → return defaults
  if sys.stdin.isatty() and curses available:
    try curses wrapper → return selection
  fall back to comma-separated input (existing logic)
```

The existing comma-separated logic is preserved as the fallback for piped input, CI, or systems where curses is unavailable.

## 8. Output Formatting

Replace `log()` calls in generators and sync with structured output:

```python
def section_header(title: str) -> None:
    width = 50
    print(f"\n─── {title} {'─' * (width - len(title) - 5)}")

def summary_line(label: str, count: int, detail: str = "") -> None:
    extra = f"  ({detail})" if detail else ""
    print(f"  {label:15s} {count}{extra}")
```

In `cmd_sync`, output becomes:

```
─── Rules ──────────────────────────────────────
  Cursor            3 rules
  Codex             3 rules
  Claude Code       3 rules

─── Skills ─────────────────────────────────────
  Cursor           21 symlinks
  Codex            21 symlinks

─── Summary ────────────────────────────────────
  6 rule targets, 2 skill targets synced.
```

Per-file writes (`Wrote ...`, `Symlinked ...`) move behind `--verbose`.
