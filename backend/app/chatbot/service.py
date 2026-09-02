import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.rules.knowledge_base import RulesKnowledgeBase, get_rules_knowledge_base
from app.services.stats_service import StatsService
from app.chatbot.query_router import QueryRouter
from app.chatbot.schemas import QueryIntent, ChatResponse, Citation

logger = logging.getLogger(__name__)

STANDARD_REFUSAL_MESSAGE = (
    "I don't have that information. I am an official Legal Metrology assistant and can "
    "only answer questions grounded in the Legal Metrology (Packaged Commodities) Rules, 2011, "
    "official DoCA gazette notifications, and system inspection scan records."
)


class GroundedChatbotService:
    """
    Conversational assistant strictly grounded on official DoCA Legal Metrology documents
    and system database audit statistics without hallucination or SQL generation.
    """

    def __init__(
        self,
        rules_kb: Optional[RulesKnowledgeBase] = None,
        stats_service: Optional[StatsService] = None,
        router: Optional[QueryRouter] = None
    ):
        self.rules_kb = rules_kb or get_rules_knowledge_base()
        self.stats_service = stats_service or StatsService()
        self.router = router or QueryRouter()

    def process_query(
        self,
        message: str,
        db: Session,
        context: Optional[Dict[str, Any]] = None
    ) -> ChatResponse:
        """
        Processes a user message, performs deterministic routing, retrieves grounded evidence,
        and constructs an explainable, fact-checked response.
        """
        cleaned_msg = message.strip()
        if not cleaned_msg:
            return ChatResponse(
                query=message,
                intent=QueryIntent.UNKNOWN,
                reply=STANDARD_REFUSAL_MESSAGE,
                citations=[],
                confidence=0.0
            )

        intent = self.router.classify(cleaned_msg)

        if intent == QueryIntent.RULE_LOOKUP:
            return self._handle_rule_lookup(cleaned_msg)
        elif intent == QueryIntent.DATA_QUERY:
            return self._handle_data_query(cleaned_msg, db)
        elif intent == QueryIntent.HYBRID:
            return self._handle_hybrid_query(cleaned_msg, db)
        else:
            return self._handle_unknown_query(cleaned_msg)

    def _handle_rule_lookup(self, query: str) -> ChatResponse:
        """Answers legal questions strictly using RulesKnowledgeBase."""
        results = self.rules_kb.semantic_search(query, top_k=2)

        if not results or results[0].get("score", 0.0) <= 0.05:
            return ChatResponse(
                query=query,
                intent=QueryIntent.RULE_LOOKUP,
                reply=STANDARD_REFUSAL_MESSAGE,
                citations=[],
                confidence=0.0
            )

        top_match = results[0]
        citations = [
            Citation(
                rule_id=r.get("rule_id"),
                declaration_name=r.get("declaration_name", "Official Legal Citation"),
                official_legal_reference=r.get("official_legal_reference", ""),
                source_pdf=r.get("source_pdf"),
                english_text=r.get("english_text"),
                hindi_text_snippet=r.get("hindi_text_snippet"),
                last_amended_date=r.get("last_amended_date"),
                score=r.get("score")
            )
            for r in results
        ]

        # Detect Hindi query
        is_hindi = any('\u0900' <= c <= '\u097F' for c in query)

        decl_name = top_match.get("declaration_name", "Declaration")
        legal_ref = top_match.get("official_legal_reference", "")
        source_pdf = top_match.get("source_pdf", "Official DoCA Gazette")
        eng_text = top_match.get("english_text", "")
        hindi_text = top_match.get("hindi_text_snippet", "")
        amended = top_match.get("last_amended_date", "Gazetted")

        if is_hindi and hindi_text:
            reply_text = (
                f"विधिक मापविज्ञान (पैकेज्ड कमोडिटीज) नियम, 2011 के अनुसार:\n\n"
                f"• **प्रावधान**: {decl_name}\n"
                f"• **कानूनी संदर्भ**: {legal_ref}\n"
                f"• **विवरण**: {hindi_text}\n"
                f"• **स्रोत दस्तावेज**: `{source_pdf}` (संशोधन तिथि: {amended})"
            )
        else:
            reply_text = (
                f"According to the **Legal Metrology (Packaged Commodities) Rules, 2011**:\n\n"
                f"• **Declaration**: {decl_name}\n"
                f"• **Statutory Citation**: {legal_ref}\n"
                f"• **Official Requirement**: {eng_text}\n"
                f"• **Official Source Document**: `{source_pdf}` (Last amended: {amended})"
            )

        return ChatResponse(
            query=query,
            intent=QueryIntent.RULE_LOOKUP,
            reply=reply_text,
            citations=citations,
            confidence=min(1.0, float(top_match.get("score", 0.8) + 0.1))
        )

    def _handle_data_query(self, query: str, db: Session) -> ChatResponse:
        """Answers system statistics queries strictly from StatsService metrics without raw SQL."""
        stats = self.stats_service.get_dashboard_statistics(db=db)
        summary = stats.get("summary", {})
        total_scans = summary.get("total_scans", 0)
        comp_rate = summary.get("compliance_rate", 0.0)
        compliant_scans = summary.get("compliant_scans", 0)
        non_compliant_scans = summary.get("non_compliant_scans", 0)
        avg_score = summary.get("average_compliance_score", 0.0)
        top_brands = stats.get("top_non_compliant_brands", [])
        violation_fields = stats.get("violation_rate_by_field", [])

        if total_scans == 0:
            reply_text = (
                "The Legal Metrology inspection repository currently has **0 scan records**. "
                "No compliance analytics or violation statistics are available yet."
            )
        else:
            q_lower = query.lower()
            if "top" in q_lower or "brand" in q_lower:
                if top_brands:
                    brand_lines = [
                        f"1. **{top_brands[0]['brand_name']}**: {top_brands[0]['non_compliant_scans']} violations ({top_brands[0]['non_compliance_rate']}% non-compliance, most common issue: {top_brands[0]['most_common_violation']})"
                    ]
                    if len(top_brands) > 1:
                        brand_lines.append(f"2. **{top_brands[1]['brand_name']}**: {top_brands[1]['non_compliant_scans']} violations")
                    reply_text = (
                        f"Based on {total_scans} persistent audit scans, the top non-compliant brands are:\n"
                        + "\n".join(brand_lines)
                    )
                else:
                    reply_text = f"All {total_scans} scanned brands are currently fully compliant."
            elif "violation" in q_lower or "field" in q_lower:
                top_viols = [v for v in violation_fields if v.get("violation_count", 0) > 0]
                if top_viols:
                    v_str = ", ".join([f"**{v['declaration_name']}** ({v['violation_count']} violations, {v['violation_rate']}%)" for v in top_viols[:3]])
                    reply_text = f"The most frequently violated statutory declarations are: {v_str}."
                else:
                    reply_text = f"No statutory violations recorded across the {total_scans} audits."
            else:
                reply_text = (
                    f"**Legal Metrology Inspection Analytics Summary**:\n\n"
                    f"• **Total Scans Recorded**: {total_scans}\n"
                    f"• **Overall Compliance Rate**: {comp_rate:.1f}%\n"
                    f"• **Compliant Packages**: {compliant_scans}\n"
                    f"• **Non-Compliant / Violations**: {non_compliant_scans}\n"
                    f"• **Average Compliance Score**: {avg_score:.1f}%"
                )

        return ChatResponse(
            query=query,
            intent=QueryIntent.DATA_QUERY,
            reply=reply_text,
            citations=[],
            data_summary=summary,
            confidence=1.0
        )

    def _handle_hybrid_query(self, query: str, db: Session) -> ChatResponse:
        """Answers queries requiring both statutory rule requirements and empirical audit metrics."""
        rule_res = self._handle_rule_lookup(query)
        stats = self.stats_service.get_dashboard_statistics(db=db)
        summary = stats.get("summary", {})
        total_scans = summary.get("total_scans", 0)

        # Check violation rate for the matched rule
        matched_rule_id = rule_res.citations[0].rule_id if rule_res.citations else None
        v_fields = stats.get("violation_rate_by_field", [])
        field_stat = next((v for v in v_fields if v.get("rule_id") == matched_rule_id), None)

        if field_stat and total_scans > 0:
            data_clause = (
                f"\n\n**Empirical Repository Statistics**:\n"
                f"• **Field Violation Rate**: {field_stat['violation_rate']}%\n"
                f"• **Total Evaluations**: {field_stat['total_evaluations']} scans ({field_stat['violation_count']} violations observed)."
            )
        else:
            data_clause = f"\n\n**Repository Metrics**: Total {total_scans} scans recorded in the database."

        combined_reply = rule_res.reply + data_clause

        return ChatResponse(
            query=query,
            intent=QueryIntent.HYBRID,
            reply=combined_reply,
            citations=rule_res.citations,
            data_summary=summary,
            confidence=0.95
        )

    def _handle_unknown_query(self, query: str) -> ChatResponse:
        """Handles unclassified queries, attempting soft search or returning strict refusal."""
        results = self.rules_kb.semantic_search(query, top_k=1)
        if results and results[0].get("score", 0.0) >= 0.35:
            return self._handle_rule_lookup(query)

        return ChatResponse(
            query=query,
            intent=QueryIntent.UNKNOWN,
            reply=STANDARD_REFUSAL_MESSAGE,
            citations=[],
            data_summary=None,
            confidence=0.0
        )
