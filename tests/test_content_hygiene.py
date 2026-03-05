"""Repository content hygiene checks for rules and skills."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = ROOT / "rules"
SKILLS_DIR = ROOT / "skills"


def _iter_markdown_files():
    yield from RULES_DIR.glob("*.md")
    yield from SKILLS_DIR.glob("*/SKILL.md")


def test_no_ai_agents_plural_path_reference():
    for path in _iter_markdown_files():
        text = path.read_text(errors="ignore")
        assert ".ai-agents" not in text, f"plural path typo in {path}"


def test_atlassian_skill_uses_current_acli_commands():
    skill = SKILLS_DIR / "atlassian-mcp-cli" / "SKILL.md"
    text = skill.read_text(errors="ignore")

    assert "comment-create" not in text
    assert "acli jira workitem comment create" in text



def test_datadog_rule_is_policy_and_points_to_skill():
    rule = (RULES_DIR / "datadog-monitoring.md").read_text(errors="ignore")

    assert "datadog-monitoring" in rule
    # Keep rule lightweight; detailed reference belongs in the skill.
    assert len(rule.splitlines()) <= 40


def test_all_skills_have_required_frontmatter_fields():
    for skill_file in SKILLS_DIR.glob("*/SKILL.md"):
        text = skill_file.read_text(errors="ignore")
        assert text.startswith("---\n"), f"missing frontmatter: {skill_file}"
        fm_end = text.find("\n---\n", 4)
        assert fm_end != -1, f"unterminated frontmatter: {skill_file}"
        frontmatter = text[4:fm_end]

        assert "name:" in frontmatter, f"missing name in {skill_file}"
        assert "description:" in frontmatter, f"missing description in {skill_file}"
