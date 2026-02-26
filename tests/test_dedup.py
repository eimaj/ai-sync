"""Tests for rule deduplication."""

import sys

from tests.conftest import make_args

mod = sys.modules["sync_agent_rules"]


class TestDeduplicateRules:
    def test_no_duplicates(self):
        rules = [
            mod.ImportedRule(id="a", content="Content A", source="cursor"),
            mod.ImportedRule(id="b", content="Content B", source="codex"),
        ]
        result = mod.deduplicate_rules(rules, make_args())
        assert len(result) == 2
        assert [r.id for r in result] == ["a", "b"]

    def test_exact_match_keeps_first(self):
        rules = [
            mod.ImportedRule(id="a", content="Same content", source="cursor"),
            mod.ImportedRule(id="a", content="Same content", source="codex"),
        ]
        result = mod.deduplicate_rules(rules, make_args())
        assert len(result) == 1
        assert result[0].source == "cursor"

    def test_high_similarity_skips(self):
        base = "This is a long rule with lots of content.\n" * 10
        rules = [
            mod.ImportedRule(id="a", content=base, source="cursor"),
            mod.ImportedRule(id="a", content=base + "\nMinor addition.", source="codex"),
        ]
        result = mod.deduplicate_rules(rules, make_args())
        assert len(result) == 1
        assert result[0].source == "cursor"

    def test_low_similarity_keeps_first_with_yes(self):
        rules = [
            mod.ImportedRule(id="a", content="Completely different content A", source="cursor"),
            mod.ImportedRule(id="a", content="Totally unrelated content B", source="codex"),
        ]
        result = mod.deduplicate_rules(rules, make_args(yes=True))
        assert len(result) == 1
        assert result[0].source == "cursor"
