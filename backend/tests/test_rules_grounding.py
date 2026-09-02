"""
Unit tests for Legal Metrology DoCA official dataset grounding, enriched rules.json,
and RulesKnowledgeBase multilingual semantic search.
"""

import os
import pytest
from pathlib import Path

from app.rules.rule_loader import RuleLoader
from app.rules.knowledge_base import RulesKnowledgeBase
from app.models.product import RuleDefinition


def test_enriched_rules_loader():
    """Verify that rules.json loads cleanly with all official DoCA grounding fields."""
    loader = RuleLoader()
    rules = loader.load_rules()

    assert len(rules) == 10, f"Expected 10 rules, got {len(rules)}"

    for rule in rules:
        assert isinstance(rule, RuleDefinition)
        assert rule.rule_id is not None
        assert rule.declaration_name is not None
        assert rule.legal_reference is not None

        # Verify enrichment fields
        assert rule.official_legal_reference is not None, f"Rule {rule.rule_id} missing official_legal_reference"
        assert rule.source_pdf is not None, f"Rule {rule.rule_id} missing source_pdf"
        assert rule.english_text is not None, f"Rule {rule.rule_id} missing english_text"
        assert rule.hindi_text_snippet is not None, f"Rule {rule.rule_id} missing hindi_text_snippet"
        assert rule.last_amended_date is not None, f"Rule {rule.rule_id} missing last_amended_date"
        assert rule.applicability_notes is not None, f"Rule {rule.rule_id} missing applicability_notes"


def test_rules_knowledge_base_semantic_search():
    """Verify RulesKnowledgeBase multilingual semantic search in English and Hindi."""
    kb = RulesKnowledgeBase()
    assert len(kb.rules) == 10
    assert len(kb.corpus) >= 10

    # 1. English query search
    en_results = kb.semantic_search("country of origin for imported goods on e-commerce websites", top_k=3)
    assert len(en_results) > 0
    top_en = en_results[0]
    assert top_en["official_legal_reference"] is not None
    assert top_en["source_pdf"] is not None

    # 2. Hindi query search
    hi_results = kb.semantic_search("निर्माता और पैकर का नाम एवं पता", top_k=3)
    assert len(hi_results) > 0
    top_hi = hi_results[0]
    assert top_hi["official_legal_reference"] is not None
    assert top_hi["source_pdf"] is not None


def test_rules_knowledge_base_edible_oil_sop():
    """Verify semantic search retrieves edible oil SOP document."""
    kb = RulesKnowledgeBase()
    results = kb.semantic_search("edible oil net quantity measurement SOP", top_k=3)
    assert len(results) > 0
    match_pdfs = [res.get("source_pdf") for res in results if res.get("source_pdf")]
    assert any("Edible oil" in pdf or "edible" in pdf.lower() for pdf in match_pdfs if pdf)
