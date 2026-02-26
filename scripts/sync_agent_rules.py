#!/usr/bin/env python3
"""Sync AI agent rules and skills from a canonical source to multiple agent targets."""

from __future__ import annotations

import argparse
import difflib
import glob as globmod
import json
import os
import re
import shutil
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    import curses

    _HAS_CURSES = True
except ImportError:
    _HAS_CURSES = False

# ---------------------------------------------------------------------------
# Terminal colors (respects NO_COLOR and non-TTY)
# ---------------------------------------------------------------------------

_USE_COLOR = (
    sys.stdout.isatty()
    and os.environ.get("NO_COLOR") is None
    and os.environ.get("TERM") != "dumb"
)


def _ansi(code: str) -> str:
    return f"\033[{code}m" if _USE_COLOR else ""


class C:
    """ANSI escape sequences, empty strings when color is disabled."""
    RESET = _ansi("0")
    BOLD = _ansi("1")
    DIM = _ansi("2")
    RED = _ansi("31")
    GREEN = _ansi("32")
    YELLOW = _ansi("33")
    BLUE = _ansi("34")
    MAGENTA = _ansi("35")
    CYAN = _ansi("36")
    BOLD_RED = _ansi("1;31")
    BOLD_GREEN = _ansi("1;32")
    BOLD_YELLOW = _ansi("1;33")
    BOLD_CYAN = _ansi("1;36")
    BOLD_WHITE = _ansi("1;37")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AGENT_DIR = Path.home() / ".ai-agent"
MANIFEST_PATH = AGENT_DIR / "manifest.json"
RULES_DIR = AGENT_DIR / "rules"
SKILLS_DIR = AGENT_DIR / "skills"
BACKUPS_DIR = AGENT_DIR / "backups"

GENERATED_HEADER = "# Generated from ~/.ai-agent/ -- do not edit directly"
GENERATED_HEADER_TEMPLATE = (
    "{header}\n"
    "# Run: ~/.ai-agent/scripts/sync_agent_rules.py sync\n"
    "# Last synced: {timestamp}\n"
)

AGENT_PATHS: dict[str, dict[str, Any]] = {
    "cursor": {
        "label": "Cursor",
        "rules_dir": Path.home() / ".cursor" / "rules",
        "rules_ext": ".mdc",
        "skills_dir": Path.home() / ".cursor" / "skills",
        "description": "rules as .mdc + skill symlinks",
    },
    "codex": {
        "label": "Codex",
        "rules_file": Path.home() / ".codex" / "model-instructions.md",
        "skills_dir": Path.home() / ".codex" / "skills",
        "description": "rules as model-instructions.md + skill symlinks",
    },
    "claude": {
        "label": "Claude Code",
        "rules_file": Path.home() / ".claude" / "CLAUDE.md",
        "description": "rules as CLAUDE.md",
    },
    "gemini": {
        "label": "Gemini CLI",
        "rules_file": Path.home() / ".gemini" / "GEMINI.md",
        "skills_dir": Path.home() / ".gemini" / "skills",
        "description": "rules as GEMINI.md + skill symlinks",
    },
    "kiro": {
        "label": "Kiro",
        "rules_file": Path.home() / ".kiro" / "steering" / "conventions.md",
        "description": "rules as steering/conventions.md",
    },
    "antigravity": {
        "label": "Antigravity",
        "skills_dir": Path.home() / ".gemini" / "antigravity" / "skills",
        "description": "skill symlinks only",
    },
    "agents-md": {
        "label": "AGENTS.md",
        "description": "condensed rules for cross-tool standard",
    },
}

RULE_TARGETS = [k for k in AGENT_PATHS if k != "antigravity"]
SKILL_TARGETS = [k for k, v in AGENT_PATHS.items() if "skills_dir" in v]

SKIP_SKILL_DIRS = {".system", "cursor-migration-map"}
SKIP_SKILL_PREFIXES = ("pattern-",)

SETTABLE_KEYS: dict[str, tuple[str, str, str]] = {
    "agents_md.paths": ("agents_md", "paths", "array"),
    "agents_md.header": ("agents_md", "header", "scalar"),
    "agents_md.preamble": ("agents_md", "preamble", "scalar"),
}

# ---------------------------------------------------------------------------
# Backup system
# ---------------------------------------------------------------------------

_current_backup: Optional[Path] = None


def init_backup(command: str) -> Path:
    """Create a timestamped backup directory for this session."""
    global _current_backup
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = BACKUPS_DIR / ts
    backup_dir.mkdir(parents=True, exist_ok=True)
    _current_backup = backup_dir
    meta = {"created": ts, "command": command}
    (backup_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return backup_dir


def _backup_dest(original: Path) -> Optional[Path]:
    """Map an absolute path to its location inside the current backup."""
    if _current_backup is None:
        return None
    try:
        rel = original.relative_to(Path.home())
    except ValueError:
        rel = Path(str(original).lstrip("/"))
    return _current_backup / "files" / rel


def backup_file(path: Path, args: argparse.Namespace) -> None:
    """Copy a file to the current backup directory before it is modified."""
    if not path.exists() or path.is_symlink():
        return
    dest = _backup_dest(path)
    if dest is None:
        return
    if args.dry_run:
        log_verbose(f"{C.MAGENTA}[dry-run]{C.RESET} Would backup {path}", args)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    log_verbose(f"{C.BLUE}Backed up{C.RESET} {path}", args)


def backup_directory(path: Path, args: argparse.Namespace) -> None:
    """Copy a directory tree to the current backup directory."""
    if not path.exists() or not path.is_dir():
        return
    dest = _backup_dest(path)
    if dest is None:
        return
    if args.dry_run:
        log_verbose(f"{C.MAGENTA}[dry-run]{C.RESET} Would backup dir {path}", args)
        return
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(path, dest, symlinks=False)
    log_verbose(f"{C.BLUE}Backed up dir{C.RESET} {path}", args)


def latest_backup() -> Optional[Path]:
    """Return the most recent backup directory, or None."""
    if not BACKUPS_DIR.exists():
        return None
    dirs = sorted(
        (d for d in BACKUPS_DIR.iterdir() if d.is_dir() and (d / "meta.json").exists()),
        reverse=True,
    )
    return dirs[0] if dirs else None


def restore_from_backup(backup_dir: Path, targets: list[Path],
                        args: argparse.Namespace) -> int:
    """Restore backed-up files to their original locations. Returns count."""
    files_root = backup_dir / "files"
    if not files_root.exists():
        return 0
    target_set = {str(t) for t in targets}
    count = 0
    for backed_up in files_root.rglob("*"):
        if not backed_up.is_file():
            continue
        rel = backed_up.relative_to(files_root)
        original = Path.home() / rel
        if str(original) not in target_set:
            continue
        if args.dry_run:
            log_verbose(f"{C.MAGENTA}[dry-run]{C.RESET} Would restore {original}", args)
            count += 1
            continue
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backed_up, original)
        log_verbose(f"{C.GREEN}Restored{C.RESET} {original}", args)
        count += 1
    return count


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ImportedRule:
    id: str
    content: str
    source: str
    cursor_meta: Optional[dict[str, Any]] = None


@dataclass
class RuleEntry:
    id: str
    file: str
    imported_from: str
    cursor: Optional[dict[str, Any]] = None
    exclude: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# CLI setup
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sync_agent_rules.py",
        description="Sync AI agent rules and skills across coding assistants.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--diff", action="store_true", help="Show diffs against current files")
    parser.add_argument("--verbose", action="store_true", help="Detailed output")
    parser.add_argument("--only", metavar="AGENT", help="Sync a single agent")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts")

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("init", help="First-time import and setup")
    sub.add_parser("sync", help="Generate agent configs from canonical source")
    sub.add_parser("reconfigure", help="Change target selection")
    sub.add_parser("status", help="Show current configuration and sync state")
    sub.add_parser("clean", help="Remove all generated files and skill symlinks")

    add_p = sub.add_parser("add-rule", help="Add a new rule")
    add_p.add_argument("id", help="Rule identifier (used as filename)")
    add_p.add_argument("--description", default="", help="Cursor description")
    add_p.add_argument("--always-apply", action="store_true", default=True)
    add_p.add_argument("--no-always-apply", action="store_true")
    add_p.add_argument("--file", type=str, help="Import content from file")
    add_p.add_argument("--exclude", type=str, default="",
                        help="Comma-separated agents to exclude")

    rm_p = sub.add_parser("remove-rule", help="Remove a rule")
    rm_p.add_argument("id", help="Rule identifier to remove")

    set_p = sub.add_parser("set", help="Update a manifest field")
    set_p.add_argument("key", help="Dotted key path (e.g. agents_md.paths)")
    set_p.add_argument("value", help="New value (arrays comma-separated)")

    return parser


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def section_header(title: str) -> None:
    width = 50
    rule = "─" * max(1, width - len(title) - 5)
    print(f"\n{C.BOLD_CYAN}─── {title} {rule}{C.RESET}")


def summary_line(label: str, count: int, detail: str = "") -> None:
    extra = f"  {C.DIM}({detail}){C.RESET}" if detail else ""
    print(f"  {label:15s} {C.BOLD}{count}{C.RESET}{extra}")


def log(msg: str) -> None:
    print(f"  {msg}")


def log_verbose(msg: str, args: argparse.Namespace) -> None:
    if args.verbose:
        print(f"  {C.DIM}[verbose] {msg}{C.RESET}")


def confirm(prompt: str, default: bool = True) -> bool:
    suffix = f"{C.BOLD}[Y/n]{C.RESET}" if default else f"{C.BOLD}[y/N]{C.RESET}"
    answer = input(f"{prompt} {suffix} ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def _curses_multi_select(
    stdscr: Any,
    prompt: str,
    options: list[tuple[str, str]],
    defaults: Optional[list[str]],
) -> list[str]:
    """Interactive multi-select using curses. Called via curses.wrapper."""
    curses.curs_set(0)
    curses.use_default_colors()
    selected = set(defaults or [])
    cursor = 0
    hint = "(↑↓ navigate, Space toggle, a all, Enter confirm, q abort)"

    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()
        stdscr.addnstr(0, 0, prompt, max_x - 1)
        stdscr.addnstr(1, 0, hint, max_x - 1)

        for i, (oid, label) in enumerate(options):
            if i + 3 >= max_y:
                break
            marker = "x" if oid in selected else " "
            prefix = ">" if i == cursor else " "
            line = f"  {prefix} [{marker}] {label}"
            stdscr.addnstr(i + 3, 0, line, max_x - 1)

        stdscr.refresh()
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


def _fallback_multi_select(
    prompt: str,
    options: list[tuple[str, str]],
    defaults: Optional[list[str]],
) -> list[str]:
    """Comma-separated number input fallback for non-TTY environments."""
    print(f"\n{prompt}")
    for i, (oid, label) in enumerate(options, 1):
        marker = "*" if defaults and oid in defaults else " "
        print(f"  {i}. [{marker}] {label}")
    if defaults:
        print(f"\n  (* = detected/suggested, press Enter to accept defaults)")
    raw = input("\n  Select (comma-separated numbers, or 'all'): ").strip()
    if not raw:
        return defaults or []
    if raw.lower() == "all":
        return [oid for oid, _ in options]
    selected = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(options):
                selected.append(options[idx][0])
    return selected


def multi_select(
    prompt: str,
    options: list[tuple[str, str]],
    defaults: Optional[list[str]] = None,
    auto_accept: bool = False,
) -> list[str]:
    """Multi-select with fallback chain: auto_accept -> curses -> comma-separated."""
    if not options:
        return []

    if auto_accept:
        print(f"\n{prompt}")
        for oid in (defaults or []):
            label = next((lbl for o, lbl in options if o == oid), oid)
            print(f"  {C.DIM}[auto]{C.RESET} {label}")
        return defaults or []

    if _HAS_CURSES and sys.stdin.isatty() and sys.stdout.isatty():
        try:
            return curses.wrapper(
                _curses_multi_select, prompt, options, defaults
            )
        except curses.error:
            pass

    return _fallback_multi_select(prompt, options, defaults)


def is_generated_file(content: str) -> bool:
    return content.lstrip().startswith(GENERATED_HEADER)


def generated_header() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return GENERATED_HEADER_TEMPLATE.format(header=GENERATED_HEADER, timestamp=ts)


def write_file(path: Path, content: str, args: argparse.Namespace) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        log_verbose(f"{C.MAGENTA}[dry-run]{C.RESET} Would write {path} ({len(content)} bytes)", args)
        return
    if args.diff and path.exists():
        existing = path.read_text()
        diff = difflib.unified_diff(
            existing.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path) + " (new)",
        )
        diff_text = "".join(diff)
        if diff_text:
            print(diff_text)
        else:
            log_verbose(f"{path} {C.DIM}(unchanged){C.RESET}", args)
            return
    if path.exists():
        backup_file(path, args)
    path.write_text(content)
    log_verbose(f"{C.GREEN}Wrote{C.RESET} {path}", args)


def remove_file(path: Path, args: argparse.Namespace) -> None:
    if args.dry_run:
        log_verbose(f"{C.MAGENTA}[dry-run]{C.RESET} Would remove {path}", args)
        return
    if path.exists() and not path.is_symlink():
        backup_file(path, args)
    path.unlink(missing_ok=True)
    log_verbose(f"{C.YELLOW}Removed{C.RESET} {path}", args)


# ---------------------------------------------------------------------------
# Frontmatter parser (minimal YAML subset for Cursor .mdc)
# ---------------------------------------------------------------------------


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse flat key: value YAML frontmatter between --- delimiters.
    Returns (metadata, body). If no frontmatter, returns ({}, text)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    fm_block = text[3:end].strip()
    body = text[end + 3:].lstrip("\n")
    meta: dict[str, Any] = {}
    for line in fm_block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(\w+)\s*:\s*(.+)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        # Type coercion
        if val.lower() in ("true", "false"):
            meta[key] = val.lower() == "true"
        elif val.startswith('"') and val.endswith('"'):
            meta[key] = val[1:-1]
        elif val.startswith("'") and val.endswith("'"):
            meta[key] = val[1:-1]
        else:
            meta[key] = val
    return meta, body


def build_frontmatter(meta: dict[str, Any]) -> str:
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, str):
            if " " in v or ":" in v or '"' in v:
                lines.append(f'{k}: "{v}"')
            else:
                lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def read_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        print(f"{C.BOLD_RED}Error:{C.RESET} {MANIFEST_PATH} not found. Run 'init' first.")
        sys.exit(1)
    return json.loads(MANIFEST_PATH.read_text())


def write_manifest(data: dict[str, Any], args: argparse.Namespace) -> None:
    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    write_file(MANIFEST_PATH, content, args)


# ---------------------------------------------------------------------------
# Importers
# ---------------------------------------------------------------------------


def import_cursor() -> tuple[list[ImportedRule], list[Path]]:
    rules_dir = AGENT_PATHS["cursor"]["rules_dir"]
    rules: list[ImportedRule] = []
    if not rules_dir.exists():
        log(f"  {C.DIM}Cursor: no rules directory found, skipping{C.RESET}")
        return rules, []
    for f in sorted(rules_dir.glob("*.mdc")):
        text = f.read_text()
        meta, body = parse_frontmatter(text)
        if is_generated_file(body):
            log(f"  {C.DIM}Cursor: skipping generated file {f.name}{C.RESET}")
            continue
        rid = f.stem
        cursor_meta = {}
        if "alwaysApply" in meta:
            cursor_meta["alwaysApply"] = meta["alwaysApply"]
        if "description" in meta:
            cursor_meta["description"] = meta["description"]
        if "globs" in meta:
            cursor_meta["globs"] = meta["globs"]
        rules.append(ImportedRule(
            id=rid, content=body, source="cursor",
            cursor_meta=cursor_meta or None,
        ))
        log(f"  {C.GREEN}Cursor:{C.RESET} imported {f.name} {C.DIM}({len(body.splitlines())} lines){C.RESET}")
    skills = _scan_skills(AGENT_PATHS["cursor"].get("skills_dir"))
    return rules, skills


def import_codex() -> tuple[list[ImportedRule], list[Path]]:
    rules_file = AGENT_PATHS["codex"]["rules_file"]
    rules: list[ImportedRule] = []
    if not rules_file.exists():
        log(f"  {C.DIM}Codex: no model-instructions.md found, skipping{C.RESET}")
        return rules, []
    text = rules_file.read_text()
    if is_generated_file(text):
        log(f"  {C.DIM}Codex: skipping generated model-instructions.md{C.RESET}")
        return rules, []
    sections = re.split(r"^## Source:\s*(.+)$", text, flags=re.MULTILINE)
    # sections[0] is preamble, then alternating (header, content)
    for i in range(1, len(sections), 2):
        header = sections[i].strip()
        content = sections[i + 1].strip() if i + 1 < len(sections) else ""
        rid = re.sub(r"\.mdc$", "", header)
        rules.append(ImportedRule(id=rid, content=content, source="codex"))
        log(f"  {C.GREEN}Codex:{C.RESET} imported section '{header}' {C.DIM}({len(content.splitlines())} lines){C.RESET}")
    skills = _scan_skills(AGENT_PATHS["codex"].get("skills_dir"))
    return rules, skills


def import_claude() -> tuple[list[ImportedRule], list[Path]]:
    return _import_single_file("claude", AGENT_PATHS["claude"]["rules_file"])


def import_gemini() -> tuple[list[ImportedRule], list[Path]]:
    rules, _ = _import_single_file("gemini", AGENT_PATHS["gemini"]["rules_file"])
    skills = _scan_skills(AGENT_PATHS["gemini"].get("skills_dir"))
    return rules, skills


def import_kiro() -> tuple[list[ImportedRule], list[Path]]:
    steering_dir = Path.home() / ".kiro" / "steering"
    rules: list[ImportedRule] = []
    if not steering_dir.exists():
        log(f"  {C.DIM}Kiro: no steering directory found, skipping{C.RESET}")
        return rules, []
    for f in sorted(steering_dir.glob("*.md")):
        text = f.read_text()
        if is_generated_file(text):
            log(f"  {C.DIM}Kiro: skipping generated file {f.name}{C.RESET}")
            continue
        rid = f.stem
        rules.append(ImportedRule(id=rid, content=text.strip(), source="kiro"))
        log(f"  {C.GREEN}Kiro:{C.RESET} imported {f.name} {C.DIM}({len(text.splitlines())} lines){C.RESET}")
    return rules, []


def _import_single_file(agent: str, path: Path) -> tuple[list[ImportedRule], list[Path]]:
    label = AGENT_PATHS[agent]["label"]
    rules: list[ImportedRule] = []
    if not path.exists():
        log(f"  {C.DIM}{label}: no {path.name} found, skipping{C.RESET}")
        return rules, []
    text = path.read_text()
    if is_generated_file(text):
        log(f"  {C.DIM}{label}: skipping generated {path.name}{C.RESET}")
        return rules, []
    sections = re.split(r"^(# .+)$", text, flags=re.MULTILINE)
    for i in range(1, len(sections), 2):
        heading = sections[i].lstrip("# ").strip()
        content = sections[i + 1].strip() if i + 1 < len(sections) else ""
        full_content = sections[i] + "\n" + content
        rid = re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")
        rules.append(ImportedRule(id=rid, content=full_content.strip(), source=agent))
        log(f"  {C.GREEN}{label}:{C.RESET} imported '{heading}' {C.DIM}({len(content.splitlines())} lines){C.RESET}")
    return rules, []


def _scan_skills(skills_dir: Optional[Path]) -> list[Path]:
    if not skills_dir or not skills_dir.exists():
        return []
    result = []
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        if entry.is_symlink():
            continue
        if entry.name in SKIP_SKILL_DIRS:
            continue
        if any(entry.name.startswith(p) for p in SKIP_SKILL_PREFIXES):
            continue
        result.append(entry)
    return result


def import_skills(skill_dirs: list[Path], args: argparse.Namespace) -> int:
    """Copy skill directories to canonical location. Returns count."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for src in skill_dirs:
        dest = SKILLS_DIR / src.name
        if dest.exists():
            log_verbose(f"Skill '{src.name}' already exists, skipping", args)
            continue
        if args.dry_run:
            log(f"{C.MAGENTA}[dry-run]{C.RESET} Would copy skill {src.name}")
            count += 1
            continue
        shutil.copytree(src, dest, symlinks=False)
        log(f"  {C.GREEN}Copied skill:{C.RESET} {src.name}")
        count += 1
    return count


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def _rule_preview(rule: ImportedRule) -> str:
    """First non-heading, non-empty line of a rule, truncated."""
    for line in rule.content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped[:80]
    return "(empty)"


def deduplicate_rules(all_rules: list[ImportedRule], args: argparse.Namespace) -> list[ImportedRule]:
    seen: dict[str, ImportedRule] = {}
    result: list[ImportedRule] = []
    for rule in all_rules:
        if rule.id in seen:
            existing = seen[rule.id]
            ratio = difflib.SequenceMatcher(None, existing.content, rule.content).ratio()
            if ratio > 0.8:
                log(f"  {C.DIM}Duplicate '{rule.id}' from {rule.source} matches {existing.source} ({ratio:.0%}), skipping{C.RESET}")
                continue
            else:
                log(f"  {C.BOLD_YELLOW}Warning:{C.RESET} '{rule.id}' from {rule.source} differs from {existing.source} ({ratio:.0%})")
                if not args.yes:
                    diff = difflib.unified_diff(
                        existing.content.splitlines(keepends=True),
                        rule.content.splitlines(keepends=True),
                        fromfile=f"{existing.source}/{rule.id}",
                        tofile=f"{rule.source}/{rule.id}",
                    )
                    print("".join(diff))
                    if not confirm(f"  Keep version from {existing.source}?"):
                        seen[rule.id] = rule
                        result = [r for r in result if r.id != rule.id]
                        result.append(rule)
                continue
        seen[rule.id] = rule
        result.append(rule)
    return result


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


def _rules_for_target(manifest: dict, target: str) -> list[dict]:
    return [r for r in manifest["rules"] if target not in r.get("exclude", [])]


def gen_cursor(manifest: dict, args: argparse.Namespace) -> None:
    rules_dir = AGENT_PATHS["cursor"]["rules_dir"]
    rules_dir.mkdir(parents=True, exist_ok=True)
    rules = _rules_for_target(manifest, "cursor")
    rule_ids = {r["id"] for r in rules}

    for rule in rules:
        content = (RULES_DIR / rule["file"]).read_text()
        meta = {}
        cursor_meta = rule.get("cursor", {})
        if cursor_meta:
            if "description" in cursor_meta:
                meta["description"] = cursor_meta["description"]
            if "alwaysApply" in cursor_meta:
                meta["alwaysApply"] = cursor_meta["alwaysApply"]
            if "globs" in cursor_meta:
                meta["globs"] = cursor_meta["globs"]
        fm = build_frontmatter(meta) if meta else "---\n---"
        header = generated_header()
        full = f"{fm}\n\n{header}\n{content}"
        write_file(rules_dir / f"{rule['id']}.mdc", full, args)

    # Clean up stale generated files
    for f in rules_dir.glob("*.mdc"):
        if f.stem not in rule_ids:
            text = f.read_text()
            _, body = parse_frontmatter(text)
            if is_generated_file(body):
                remove_file(f, args)

    if "skills_dir" in AGENT_PATHS["cursor"]:
        sync_skills(AGENT_PATHS["cursor"]["skills_dir"], args)


def gen_codex(manifest: dict, args: argparse.Namespace) -> None:
    rules = _rules_for_target(manifest, "codex")
    parts = [generated_header(), ""]
    for rule in rules:
        content = (RULES_DIR / rule["file"]).read_text()
        parts.append(f"## Rule: {rule['id']}\n")
        parts.append(content)
        parts.append("")
    write_file(AGENT_PATHS["codex"]["rules_file"], "\n".join(parts), args)

    if "skills_dir" in AGENT_PATHS["codex"]:
        sync_skills(AGENT_PATHS["codex"]["skills_dir"], args)


def gen_claude(manifest: dict, args: argparse.Namespace) -> None:
    _gen_concat_file(manifest, "claude", args)


def gen_gemini(manifest: dict, args: argparse.Namespace) -> None:
    _gen_concat_file(manifest, "gemini", args)
    if "skills_dir" in AGENT_PATHS["gemini"]:
        sync_skills(AGENT_PATHS["gemini"]["skills_dir"], args)


def gen_kiro(manifest: dict, args: argparse.Namespace) -> None:
    _gen_concat_file(manifest, "kiro", args)


def gen_antigravity(manifest: dict, args: argparse.Namespace) -> None:
    if "skills_dir" in AGENT_PATHS["antigravity"]:
        sync_skills(AGENT_PATHS["antigravity"]["skills_dir"], args)


def _expand_agents_md_paths(paths: list[str]) -> list[Path]:
    """Expand glob patterns and normalize directory paths in AGENTS.md path list."""
    result: list[Path] = []
    for p in paths:
        expanded = os.path.expanduser(p)
        if any(c in expanded for c in ("*", "?", "[")):
            matches = sorted(globmod.glob(expanded, recursive=True))
            if not matches:
                log(f"  {C.BOLD_YELLOW}Warning:{C.RESET} glob '{p}' matched no files")
            for m in matches:
                target = Path(m)
                if target.is_dir():
                    target = target / "AGENTS.md"
                result.append(target)
        else:
            target = Path(expanded)
            if target.is_dir():
                target = target / "AGENTS.md"
            result.append(target)
    return result


def gen_agents_md(manifest: dict, args: argparse.Namespace) -> None:
    agents_md_config = manifest.get("agents_md", {})
    raw_paths = agents_md_config.get("paths", [])
    if not raw_paths:
        log(f"  {C.DIM}AGENTS.md: no paths configured, skipping{C.RESET}")
        return

    targets = _expand_agents_md_paths(raw_paths)
    if not targets:
        return

    header = agents_md_config.get("header", "# AGENTS Rules")
    preamble = agents_md_config.get("preamble", "")
    rules = _rules_for_target(manifest, "agents-md")

    lines = [generated_header(), header, ""]
    if preamble:
        lines.append(preamble)
        lines.append("")
    for i, rule in enumerate(rules, 1):
        summary = _rule_summary(rule)
        lines.append(f"{i}. **{rule['id']}** -- {summary}")
    lines.append("")

    content = "\n".join(lines)
    for target in targets:
        write_file(target, content, args)


def _gen_concat_file(manifest: dict, agent: str, args: argparse.Namespace) -> None:
    rules = _rules_for_target(manifest, agent)
    parts = [generated_header(), ""]
    for rule in rules:
        content = (RULES_DIR / rule["file"]).read_text()
        parts.append(content)
        parts.append("")
    write_file(AGENT_PATHS[agent]["rules_file"], "\n".join(parts), args)


def _rule_summary(rule: dict) -> str:
    cursor = rule.get("cursor", {})
    if cursor and cursor.get("description"):
        return cursor["description"]
    rule_file = RULES_DIR / rule["file"]
    if rule_file.exists():
        for line in rule_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line[:120]
    return rule["id"]


# ---------------------------------------------------------------------------
# Skill symlinks
# ---------------------------------------------------------------------------


def sync_skills(target_dir: Path, args: argparse.Namespace) -> None:
    if not SKILLS_DIR.exists():
        return
    target_dir.mkdir(parents=True, exist_ok=True)
    canonical_skills = {d.name for d in SKILLS_DIR.iterdir() if d.is_dir()}

    # Remove stale symlinks pointing into our skills dir
    for entry in target_dir.iterdir():
        if entry.is_symlink():
            link_target = Path(os.readlink(entry))
            try:
                resolved = link_target.resolve()
            except OSError:
                resolved = link_target
            if str(resolved).startswith(str(SKILLS_DIR)):
                if entry.name not in canonical_skills:
                    remove_file(entry, args)
                else:
                    # Will be re-created below if needed
                    if resolved != (SKILLS_DIR / entry.name).resolve():
                        remove_file(entry, args)

    # Create symlinks
    for skill_name in sorted(canonical_skills):
        link = target_dir / skill_name
        target = SKILLS_DIR / skill_name
        if link.exists() or link.is_symlink():
            if link.is_symlink():
                existing_target = Path(os.readlink(link)).resolve()
                if existing_target == target.resolve():
                    continue
                remove_file(link, args)
            else:
                log_verbose(f"Skipping {link} (not a symlink, preserving)", args)
                continue
        if args.dry_run:
            log(f"{C.MAGENTA}[dry-run]{C.RESET} Would symlink {link} -> {target}")
            continue
        link.symlink_to(target)
        log_verbose(f"Symlinked {link.name}", args)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


IMPORTERS: dict[str, Any] = {
    "cursor": import_cursor,
    "codex": import_codex,
    "claude": import_claude,
    "gemini": import_gemini,
    "kiro": import_kiro,
}

GENERATORS: dict[str, Any] = {
    "cursor": gen_cursor,
    "codex": gen_codex,
    "claude": gen_claude,
    "gemini": gen_gemini,
    "kiro": gen_kiro,
    "antigravity": gen_antigravity,
    "agents-md": gen_agents_md,
}


def cmd_status(args: argparse.Namespace) -> None:
    manifest = read_manifest()

    rules = manifest.get("rules", [])
    section_header(f"Rules ({len(rules)})")
    if rules:
        for r in rules:
            cursor = r.get("cursor", {})
            flags = []
            if cursor.get("alwaysApply"):
                flags.append("alwaysApply")
            if cursor.get("globs"):
                flags.append(f"globs={cursor['globs']}")
            flag_str = ", ".join(flags) if flags else ""
            desc = cursor.get("description", "")
            source = r.get("imported_from", "")
            print(f"  {C.BOLD}{r['id']:30s}{C.RESET} {C.DIM}[{source:6s}]{C.RESET}  {flag_str:20s} {desc}")
    else:
        print(f"  {C.DIM}(none){C.RESET}")

    section_header("Active Targets")
    active = manifest.get("active_targets", {})
    print(f"  {C.BOLD_WHITE}Rules{C.RESET}  -> {C.GREEN}{', '.join(active.get('rules', []))}{C.RESET}")
    print(f"  {C.BOLD_WHITE}Skills{C.RESET} -> {C.GREEN}{', '.join(active.get('skills', []))}{C.RESET}")

    skill_count = 0
    if SKILLS_DIR.exists():
        skill_count = len([d for d in SKILLS_DIR.iterdir() if d.is_dir()])
    section_header(f"Skills ({skill_count})")
    if SKILLS_DIR.exists() and skill_count:
        names = sorted(d.name for d in SKILLS_DIR.iterdir() if d.is_dir())
        for i in range(0, len(names), 4):
            chunk = names[i:i + 4]
            print(f"  {'  '.join(f'{n:20s}' for n in chunk)}")
    else:
        print(f"  {C.DIM}(none){C.RESET}")

    agents_md = manifest.get("agents_md", {})
    paths = agents_md.get("paths", [])
    section_header("AGENTS.md Paths")
    if paths:
        for p in paths:
            print(f"  {p}")
    else:
        print(f"  {C.DIM}(none configured){C.RESET}")

    section_header("Last Synced")
    print(f"  {manifest.get('updated', 'never')}")
    print()


def cmd_init(args: argparse.Namespace) -> None:
    print(f"\n{C.BOLD_CYAN}=== AI Agent Rules - First-Time Setup ==={C.RESET}\n")

    # Warn if canonical content already exists
    existing = [p for p in (MANIFEST_PATH, RULES_DIR, SKILLS_DIR) if p.exists()]
    if existing:
        print(f"  {C.BOLD_YELLOW}Warning:{C.RESET} init will overwrite existing canonical content in ~/.ai-agent/:")
        for p in existing:
            print(f"    {C.YELLOW}-{C.RESET} {p}")
        print(f"\n  Source agent files (e.g., ~/.cursor/rules/) are {C.GREEN}only read, never modified{C.RESET}.\n")
        if not args.yes and not confirm("  Proceed?"):
            print(f"  {C.DIM}Aborted.{C.RESET}")
            return

    # Step 1: Select sources
    source_options = []
    detected = []
    for agent_id, info in AGENT_PATHS.items():
        if agent_id in ("agents-md", "antigravity"):
            continue
        path = info.get("rules_dir") or info.get("rules_file")
        if path and path.exists():
            detected.append(agent_id)
        source_options.append((agent_id, f"{info['label']}  ({path or 'n/a'})"))

    sources = multi_select(
        "Step 1: Which agents do you currently have rules configured in?",
        source_options,
        defaults=detected,
        auto_accept=args.yes,
    )
    if not sources:
        print(f"  {C.DIM}No sources selected. Aborted.{C.RESET}")
        return

    # Step 2: Scan and import
    print(f"\n{C.BOLD}Step 2:{C.RESET} Scanning selected sources...\n")
    all_rules: list[ImportedRule] = []
    all_skills: list[Path] = []
    for src in sources:
        if src in IMPORTERS:
            rules, skills = IMPORTERS[src]()
            all_rules.extend(rules)
            all_skills.extend(skills)

    # Deduplicate
    if len(sources) > 1:
        print("\n  Deduplicating...")
        all_rules = deduplicate_rules(all_rules, args)

    # Step 2b: Select individual rules to import
    rule_options = [
        (rule.id, f"{rule.id:30s} [{rule.source:6s}]  {_rule_preview(rule)}")
        for rule in all_rules
    ]
    all_rule_ids = [r.id for r in all_rules]

    selected_rule_ids = multi_select(
        f"Step 2b: Select rules to import ({len(all_rules)} found):",
        rule_options,
        defaults=all_rule_ids,
        auto_accept=args.yes,
    )
    if not selected_rule_ids:
        print(f"  {C.DIM}No rules selected. Aborted.{C.RESET}")
        return
    all_rules = [r for r in all_rules if r.id in selected_rule_ids]

    # Step 2c: Select individual skills to import
    if all_skills:
        skill_options = [
            (s.name, f"{s.name:30s} [{s.parent}]")
            for s in all_skills
        ]
        all_skill_names = [s.name for s in all_skills]

        selected_skill_names = multi_select(
            f"Step 2c: Select skills to import ({len(all_skills)} found):",
            skill_options,
            defaults=all_skill_names,
            auto_accept=args.yes,
        )
        all_skills = [s for s in all_skills if s.name in selected_skill_names]

    print(f"\n  {C.GREEN}Selected:{C.RESET} {C.BOLD}{len(all_rules)}{C.RESET} rules, {C.BOLD}{len(all_skills)}{C.RESET} skills")

    # Step 3: Select targets
    rule_target_options = [
        (k, f"{AGENT_PATHS[k]['label']}  ({AGENT_PATHS[k]['description']})")
        for k in RULE_TARGETS
    ]
    skill_target_options = [
        (k, f"{AGENT_PATHS[k]['label']}  ({AGENT_PATHS[k]['description']})")
        for k in SKILL_TARGETS
    ]

    rule_targets = multi_select(
        "Step 3a: Which agents do you want to sync RULES to?",
        rule_target_options,
        defaults=RULE_TARGETS,
        auto_accept=args.yes,
    )
    skill_targets = multi_select(
        "Step 3b: Which agents do you want to sync SKILLS to?",
        skill_target_options,
        defaults=SKILL_TARGETS,
        auto_accept=args.yes,
    )

    # Step 4: Prompt for AGENTS.md paths
    agents_md_paths: list[str] = []
    if "agents-md" in rule_targets and not args.yes:
        raw = input("\n  AGENTS.md output paths (comma-separated, e.g. ~/Code/AGENTS.md): ").strip()
        if raw:
            agents_md_paths = [p.strip() for p in raw.split(",") if p.strip()]

    section_header("Writing canonical source")

    init_backup("init")

    if RULES_DIR.exists():
        backup_directory(RULES_DIR, args)
        shutil.rmtree(RULES_DIR)
    RULES_DIR.mkdir(parents=True, exist_ok=True)

    rule_entries: list[dict] = []
    for rule in all_rules:
        filename = f"{rule.id}.md"
        rule_path = RULES_DIR / filename
        rule_path.write_text(rule.content + "\n")
        log(f"{C.GREEN}Created{C.RESET} rules/{filename}")
        entry: dict[str, Any] = {
            "id": rule.id,
            "file": filename,
            "imported_from": rule.source,
        }
        if rule.cursor_meta:
            entry["cursor"] = rule.cursor_meta
        rule_entries.append(entry)

    # Import skills
    skill_count = import_skills(all_skills, args)
    log(f"  {skill_count} skills imported")

    # Write manifest
    manifest = {
        "version": "1.0",
        "updated": "",
        "imported_from": sources,
        "active_targets": {
            "rules": rule_targets,
            "skills": skill_targets,
        },
        "rules": rule_entries,
        "skills": {"shared_dir": "skills"},
        "agents_md": {
            "paths": agents_md_paths,
            "header": "# Workspace AGENTS Rules",
            "preamble": "These rules apply across this workspace unless explicitly overridden.",
        },
    }
    # Always write canonical manifest (internal state, not agent output)
    manifest["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    log(f"Wrote {MANIFEST_PATH}")

    cmd_sync(args, manifest=manifest)
    print(f"{C.BOLD_GREEN}Done!{C.RESET} Edit rules in ~/.ai-agent/rules/ and run 'sync' to propagate.")


def cmd_sync(args: argparse.Namespace, manifest: Optional[dict] = None) -> None:
    if manifest is None:
        manifest = read_manifest()

    if _current_backup is None:
        init_backup("sync")

    active_rules = manifest["active_targets"]["rules"]
    active_skills = manifest["active_targets"]["skills"]

    if args.only:
        if args.only not in GENERATORS:
            print(f"{C.BOLD_RED}Error:{C.RESET} unknown agent '{args.only}'. Options: {', '.join(GENERATORS)}")
            sys.exit(1)
        active_rules = [args.only] if args.only in active_rules else []
        active_skills = [args.only] if args.only in active_skills else []

    section_header("Rules")
    rule_count = 0
    for target in active_rules:
        if target in GENERATORS:
            rules = _rules_for_target(manifest, target)
            summary_line(AGENT_PATHS[target]["label"], len(rules), "rules")
            GENERATORS[target](manifest, args)
            rule_count += 1

    section_header("Skills")
    skill_count = 0
    for target in active_skills:
        skills_dir = AGENT_PATHS.get(target, {}).get("skills_dir")
        if skills_dir:
            n = len(list(SKILLS_DIR.iterdir())) if SKILLS_DIR.exists() else 0
            summary_line(AGENT_PATHS[target]["label"], n, "symlinks")
            if target == "antigravity":
                gen_antigravity(manifest, args)
            skill_count += 1

    if not args.dry_run:
        manifest["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    section_header("Summary")
    dry = f" {C.MAGENTA}(dry-run){C.RESET}" if args.dry_run else ""
    print(f"  {C.BOLD}{rule_count}{C.RESET} rule targets, {C.BOLD}{skill_count}{C.RESET} skill targets synced.{dry}")
    print()


def cmd_add_rule(args: argparse.Namespace) -> None:
    init_backup("add-rule")
    manifest = read_manifest()
    rule_id = args.id
    rule_file = f"{rule_id}.md"
    rule_path = RULES_DIR / rule_file

    existing_ids = {r["id"] for r in manifest.get("rules", [])}
    if rule_id in existing_ids or rule_path.exists():
        print(f"{C.BOLD_RED}Error:{C.RESET} rule '{rule_id}' already exists")
        sys.exit(1)

    if args.file:
        content = Path(args.file).expanduser().read_text()
    else:
        content = f"# {rule_id.replace('-', ' ').title()}\n\nTODO: Add rule content.\n"

    if args.dry_run:
        log(f"{C.MAGENTA}[dry-run]{C.RESET} Would create rules/{rule_file}")
        log(f"{C.MAGENTA}[dry-run]{C.RESET} Would add '{rule_id}' to manifest and sync")
        return

    rule_path.parent.mkdir(parents=True, exist_ok=True)
    rule_path.write_text(content)
    log(f"{C.GREEN}Created{C.RESET} rules/{rule_file}")

    entry: dict[str, Any] = {
        "id": rule_id,
        "file": rule_file,
        "imported_from": "manual",
    }
    always_apply = not args.no_always_apply
    cursor_meta: dict[str, Any] = {"alwaysApply": always_apply}
    if args.description:
        cursor_meta["description"] = args.description
    entry["cursor"] = cursor_meta
    if args.exclude:
        entry["exclude"] = [x.strip() for x in args.exclude.split(",") if x.strip()]

    manifest["rules"].append(entry)
    write_manifest(manifest, args)
    print()
    cmd_sync(args, manifest=manifest)


def cmd_remove_rule(args: argparse.Namespace) -> None:
    manifest = read_manifest()
    rule_id = args.id
    rule_path = RULES_DIR / f"{rule_id}.md"

    matches = [r for r in manifest["rules"] if r["id"] == rule_id]
    if not matches:
        print(f"{C.BOLD_RED}Error:{C.RESET} rule '{rule_id}' not found in manifest")
        sys.exit(1)

    if args.dry_run:
        log(f"{C.MAGENTA}[dry-run]{C.RESET} Would remove rules/{rule_id}.md")
        log(f"{C.MAGENTA}[dry-run]{C.RESET} Would remove '{rule_id}' from manifest and sync")
        return

    init_backup("remove-rule")

    if rule_path.exists():
        backup_file(rule_path, args)
        rule_path.unlink()
        log(f"{C.YELLOW}Removed{C.RESET} rules/{rule_id}.md")

    manifest["rules"] = [r for r in manifest["rules"] if r["id"] != rule_id]
    write_manifest(manifest, args)
    print()
    cmd_sync(args, manifest=manifest)


def cmd_set(args: argparse.Namespace) -> None:
    manifest = read_manifest()
    key = args.key

    if key not in SETTABLE_KEYS:
        supported = ", ".join(sorted(SETTABLE_KEYS))
        print(f"{C.BOLD_RED}Error:{C.RESET} unsupported key '{key}'. Supported: {supported}")
        sys.exit(1)

    section, field, kind = SETTABLE_KEYS[key]
    if kind == "array":
        manifest[section][field] = [v.strip() for v in args.value.split(",") if v.strip()]
    else:
        manifest[section][field] = args.value

    write_manifest(manifest, args)
    print(f"  {C.GREEN}Set{C.RESET} {C.BOLD}{key}{C.RESET} = {manifest[section][field]}")


def _find_generated_rules(manifest: dict) -> list[Path]:
    """Scan active targets and return paths to generated rule files."""
    found: list[Path] = []
    for target in manifest["active_targets"]["rules"]:
        info = AGENT_PATHS.get(target, {})

        if target == "cursor":
            rules_dir = info.get("rules_dir")
            if rules_dir and rules_dir.exists():
                for f in sorted(rules_dir.glob("*.mdc")):
                    text = f.read_text()
                    _, body = parse_frontmatter(text)
                    if is_generated_file(body):
                        found.append(f)

        elif target == "agents-md":
            raw_paths = manifest.get("agents_md", {}).get("paths", [])
            for t in _expand_agents_md_paths(raw_paths):
                if t.exists() and is_generated_file(t.read_text()):
                    found.append(t)

        else:
            rules_file = info.get("rules_file")
            if rules_file and rules_file.exists():
                if is_generated_file(rules_file.read_text()):
                    found.append(rules_file)

    return found


def _find_skill_symlinks(manifest: dict) -> list[Path]:
    """Scan active skill targets and return symlinks pointing into canonical skills."""
    found: list[Path] = []
    for target in manifest["active_targets"]["skills"]:
        skills_dir = AGENT_PATHS.get(target, {}).get("skills_dir")
        if not skills_dir or not skills_dir.exists():
            continue
        for entry in sorted(skills_dir.iterdir()):
            if not entry.is_symlink():
                continue
            try:
                resolved = Path(os.readlink(entry)).resolve()
            except OSError:
                continue
            if str(resolved).startswith(str(SKILLS_DIR)):
                found.append(entry)
    return found


def cmd_clean(args: argparse.Namespace) -> None:
    manifest = read_manifest()

    rule_files = _find_generated_rules(manifest)
    skill_links = _find_skill_symlinks(manifest)
    backup = latest_backup()

    restorable: list[Path] = []
    if backup:
        files_root = backup / "files"
        if files_root.exists():
            for backed_up in files_root.rglob("*"):
                if backed_up.is_file() and backed_up.name != "meta.json":
                    rel = backed_up.relative_to(files_root)
                    original = Path.home() / rel
                    if original in rule_files or original in skill_links:
                        restorable.append(original)

    if not rule_files and not skill_links:
        print(f"\n  {C.GREEN}Nothing to clean{C.RESET} -- no generated files or skill symlinks found.")
        return

    section_header(f"Generated rule files ({len(rule_files)})")
    for f in rule_files:
        has_backup = f in restorable
        tag = f" {C.BLUE}<- will restore from backup{C.RESET}" if has_backup else ""
        print(f"  {f}{tag}")

    section_header(f"Skill symlinks ({len(skill_links)})")
    for s in skill_links:
        print(f"  {s}")

    print(f"\n  Total: {C.BOLD}{len(rule_files)}{C.RESET} generated, {C.BOLD}{len(skill_links)}{C.RESET} symlinks")
    if restorable:
        print(f"  {C.BLUE}{len(restorable)} files will be restored from backup{C.RESET} ({backup.name})")
    print(f"  Your canonical source in ~/.ai-agent/ is {C.GREEN}not affected{C.RESET}.\n")

    if not args.yes and not confirm("  Proceed?"):
        print(f"  {C.DIM}Aborted.{C.RESET}")
        return

    for f in rule_files:
        if args.dry_run:
            log_verbose(f"{C.MAGENTA}[dry-run]{C.RESET} Would remove {f}", args)
        else:
            f.unlink(missing_ok=True)
            log_verbose(f"{C.YELLOW}Removed{C.RESET} {f}", args)

    for s in skill_links:
        if args.dry_run:
            log_verbose(f"{C.MAGENTA}[dry-run]{C.RESET} Would remove symlink {s}", args)
        else:
            s.unlink(missing_ok=True)
            log_verbose(f"{C.YELLOW}Removed symlink{C.RESET} {s}", args)

    restored = 0
    if backup and restorable:
        restored = restore_from_backup(backup, restorable, args)

    section_header("Summary")
    dry = f" {C.MAGENTA}(dry-run){C.RESET}" if args.dry_run else ""
    print(f"  {C.BOLD}{len(rule_files)}{C.RESET} generated removed, {C.BOLD}{len(skill_links)}{C.RESET} symlinks removed")
    if restored:
        print(f"  {C.GREEN}{restored} files restored from backup{C.RESET}")
    print(f"  {dry}" if dry else "")
    print()


def cmd_reconfigure(args: argparse.Namespace) -> None:
    manifest = read_manifest()

    print(f"\n{C.BOLD_CYAN}=== Reconfigure Sync Targets ==={C.RESET}\n")
    print(f"  Current rule targets:  {C.GREEN}{', '.join(manifest['active_targets']['rules'])}{C.RESET}")
    print(f"  Current skill targets: {C.GREEN}{', '.join(manifest['active_targets']['skills'])}{C.RESET}")

    rule_target_options = [
        (k, f"{AGENT_PATHS[k]['label']}  ({AGENT_PATHS[k]['description']})")
        for k in RULE_TARGETS
    ]
    skill_target_options = [
        (k, f"{AGENT_PATHS[k]['label']}  ({AGENT_PATHS[k]['description']})")
        for k in SKILL_TARGETS
    ]

    manifest["active_targets"]["rules"] = multi_select(
        "Select rule targets:",
        rule_target_options,
        defaults=manifest["active_targets"]["rules"],
        auto_accept=args.yes,
    )
    manifest["active_targets"]["skills"] = multi_select(
        "Select skill targets:",
        skill_target_options,
        defaults=manifest["active_targets"]["skills"],
        auto_accept=args.yes,
    )

    write_manifest(manifest, args)
    print()
    cmd_sync(args, manifest=manifest)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "init":
        cmd_init(args)
    elif args.command == "sync":
        cmd_sync(args)
    elif args.command == "reconfigure":
        cmd_reconfigure(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "add-rule":
        cmd_add_rule(args)
    elif args.command == "remove-rule":
        cmd_remove_rule(args)
    elif args.command == "set":
        cmd_set(args)
    elif args.command == "clean":
        cmd_clean(args)


if __name__ == "__main__":
    main()
