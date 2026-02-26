"""Tests for frontmatter parsing, building, and generated-file detection."""

import sys

mod = sys.modules["sync_agent_rules"]


class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        text = "---\nalwaysApply: true\ndescription: My rule\n---\n# Body\nContent here."
        meta, body = mod.parse_frontmatter(text)
        assert meta["alwaysApply"] is True
        assert meta["description"] == "My rule"
        assert body == "# Body\nContent here."

    def test_no_frontmatter(self):
        text = "# Just a heading\nSome content."
        meta, body = mod.parse_frontmatter(text)
        assert meta == {}
        assert body == text

    def test_bool_coercion(self):
        text = "---\nalwaysApply: true\nglobs: false\n---\nBody"
        meta, _ = mod.parse_frontmatter(text)
        assert meta["alwaysApply"] is True
        assert meta["globs"] is False

    def test_quoted_values(self):
        text = '---\ndescription: "A value: with colons"\n---\nBody'
        meta, _ = mod.parse_frontmatter(text)
        assert meta["description"] == "A value: with colons"

    def test_single_quoted_values(self):
        text = "---\ndescription: 'single quoted'\n---\nBody"
        meta, _ = mod.parse_frontmatter(text)
        assert meta["description"] == "single quoted"

    def test_missing_closing_delimiter(self):
        text = "---\nalwaysApply: true\nNo closing delimiter"
        meta, body = mod.parse_frontmatter(text)
        assert meta == {}
        assert body == text


class TestBuildFrontmatter:
    def test_round_trip(self):
        original = {"alwaysApply": True, "description": "Test rule"}
        fm = mod.build_frontmatter(original)
        parsed, _ = mod.parse_frontmatter(fm + "\nBody")
        assert parsed["alwaysApply"] is True
        assert parsed["description"] == "Test rule"

    def test_bool_formatting(self):
        fm = mod.build_frontmatter({"alwaysApply": False})
        assert "alwaysApply: false" in fm

    def test_string_with_spaces(self):
        fm = mod.build_frontmatter({"description": "has spaces"})
        assert 'description: "has spaces"' in fm

    def test_simple_string(self):
        fm = mod.build_frontmatter({"description": "simple"})
        assert "description: simple" in fm


class TestIsGeneratedFile:
    def test_positive(self):
        content = mod.GENERATED_HEADER + "\nSome content"
        assert mod.is_generated_file(content) is True

    def test_positive_with_leading_whitespace(self):
        content = "\n  " + mod.GENERATED_HEADER + "\nContent"
        assert mod.is_generated_file(content) is True

    def test_negative(self):
        assert mod.is_generated_file("# Regular heading\nContent") is False

    def test_empty(self):
        assert mod.is_generated_file("") is False


class TestRulePreview:
    def test_normal_content(self):
        rule = mod.ImportedRule(id="r", content="# Heading\n\nFirst real line.", source="test")
        assert mod._rule_preview(rule) == "First real line."

    def test_heading_only(self):
        rule = mod.ImportedRule(id="r", content="# Just a heading", source="test")
        assert mod._rule_preview(rule) == "(empty)"

    def test_truncation(self):
        long_line = "x" * 200
        rule = mod.ImportedRule(id="r", content=f"# H\n{long_line}", source="test")
        assert len(mod._rule_preview(rule)) == 80

    def test_empty_content(self):
        rule = mod.ImportedRule(id="r", content="", source="test")
        assert mod._rule_preview(rule) == "(empty)"
