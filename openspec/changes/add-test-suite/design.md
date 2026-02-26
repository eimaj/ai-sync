# Design: Add Test Suite

## 1. Dev Dependency

Single file, no extras:

```
# requirements-dev.txt
pytest>=7.0
```

Runtime remains zero-dependency. `requirements-dev.txt` is committed.

## 2. Import Strategy

The script lives at `scripts/sync_agent_rules.py`, not in a Python package. Tests import
it as a module using `importlib`:

```python
import importlib.util

spec = importlib.util.spec_from_file_location(
    "sync_agent_rules",
    Path(__file__).parent.parent / "scripts" / "sync_agent_rules.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
```

This avoids needing `__init__.py` files or a `setup.py`. The loaded module object is
stored in `conftest.py` and made available as a fixture.

## 3. Filesystem Isolation (`fake_home` fixture)

The core fixture creates a temp directory tree that mirrors `$HOME`, then monkeypatches
every module-level path constant:

```python
@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    agent_dir = home / ".ai-agent"

    monkeypatch.setattr(mod, "AGENT_DIR", agent_dir)
    monkeypatch.setattr(mod, "MANIFEST_PATH", agent_dir / "manifest.json")
    monkeypatch.setattr(mod, "RULES_DIR", agent_dir / "rules")
    monkeypatch.setattr(mod, "SKILLS_DIR", agent_dir / "skills")
    monkeypatch.setattr(mod, "BACKUPS_DIR", agent_dir / "backups")
    monkeypatch.setattr(mod, "_current_backup", None)

    # Remap every entry in AGENT_PATHS
    for key, info in mod.AGENT_PATHS.items():
        patched = dict(info)
        for path_key in ("rules_dir", "rules_file", "skills_dir"):
            if path_key in patched:
                orig = patched[path_key]
                patched[path_key] = home / orig.relative_to(Path.home())
        monkeypatch.setitem(mod.AGENT_PATHS, key, patched)

    return home
```

## 4. Helper Factories

### `seed_manifest(fake_home, rules, targets)`

Creates `manifest.json` and `rules/*.md` files under the fake home. Returns the
manifest dict. Used by most integration tests.

```python
def seed_manifest(home, rules=None, rule_targets=None, skill_targets=None):
    agent_dir = home / ".ai-agent"
    rules_dir = agent_dir / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    rule_entries = []
    for rid, content in (rules or [("test-rule", "# Test Rule\nTest content.\n")]):
        (rules_dir / f"{rid}.md").write_text(content)
        rule_entries.append({
            "id": rid, "file": f"{rid}.md", "imported_from": "test",
            "cursor": {"alwaysApply": True, "description": f"Test {rid}"},
        })

    manifest = {
        "version": "1.0", "updated": "2026-01-01",
        "imported_from": ["test"],
        "active_targets": {
            "rules": rule_targets or ["cursor", "codex"],
            "skills": skill_targets or [],
        },
        "rules": rule_entries,
        "skills": {"shared_dir": "skills"},
        "agents_md": {"paths": [], "header": "# AGENTS Rules", "preamble": ""},
    }
    (agent_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest
```

### `make_args(**overrides)`

Creates an `argparse.Namespace` with sensible defaults for test invocations:

```python
def make_args(**overrides):
    defaults = {
        "dry_run": False, "diff": False, "verbose": False,
        "only": None, "yes": True, "command": "sync",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)
```

## 5. Test File Organization

```
tests/
├── conftest.py           # mod fixture, fake_home, seed_manifest, make_args
├── test_frontmatter.py   # parse_frontmatter, build_frontmatter, is_generated_file
├── test_dedup.py          # deduplicate_rules, _rule_preview
├── test_generators.py     # gen_cursor, gen_codex, gen_claude, gen_agents_md, sync_skills
├── test_backup.py         # init_backup, backup_file, backup_directory, restore, write_file
└── test_commands.py       # cmd_status, cmd_sync, cmd_add_rule, cmd_remove_rule, cmd_set,
                           # cmd_clean, cmd_init, cmd_reconfigure + error cases
```

## 6. Command Invocation Pattern

Tests call `cmd_*` functions directly with a constructed `Namespace`, not through
`main()` / `sys.argv`. This avoids `SystemExit` from argparse and gives direct access
to the args object.

For commands that call `sys.exit(1)` on error, tests use `pytest.raises(SystemExit)`:

```python
def test_remove_rule_not_found(fake_home):
    seed_manifest(fake_home)
    args = make_args(command="remove-rule", id="nonexistent")
    with pytest.raises(SystemExit):
        mod.cmd_remove_rule(args)
```

## 7. Output Capture

Tests use `capsys` (pytest built-in) to capture stdout and assert on output content:

```python
def test_status_shows_rules(fake_home, capsys):
    seed_manifest(fake_home, rules=[("my-rule", "# My Rule\nContent.\n")])
    mod.cmd_status(make_args(command="status"))
    out = capsys.readouterr().out
    assert "my-rule" in out
```
