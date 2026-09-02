import re
from typing import Set
from app.chatbot.schemas import QueryIntent


class QueryRouter:
    """
    Lightweight, deterministic keyword and pattern-based intent classifier.
    Routes queries to RULE_LOOKUP, DATA_QUERY, HYBRID, or UNKNOWN.
    """

    DATA_KEYWORDS: Set[str] = {
        "scan", "scans", "history", "trend", "trends", "dashboard", "stats", "statistics",
        "rate", "rates", "count", "how many", "total", "percentage", "brands", "brand",
        "top", "violations", "violation", "failed", "passed", "authenticity rate",
        "font size", "inspected", "records", "database", "average score", "summary", "daily"
    }

    RULE_KEYWORDS: Set[str] = {
        "rule", "rules", "lmpc", "pcr", "section", "act", "clause", "mrp", "price",
        "taxes", "inclusive", "net quantity", "quantity", "weight", "measure", "volume",
        "grams", "litres", "manufacturer", "packer", "importer", "consumer care",
        "customer care", "hotline", "date", "manufacturing", "expiry", "best before",
        "origin", "country of origin", "unit sale price", "usp", "edible oil", "sop",
        "mandatory", "conditional", "schedule", "amendment", "notification", "guideline",
        "law", "statutory", "legal", "citation", "document", "pdf",
        # Hindi terms
        "नियम", "शुद्ध", "मात्रा", "निर्माता", "पैकर", "एमआरपी", "तारीख", "उपभोक्ता", "कानून"
    }

    def classify(self, query: str) -> QueryIntent:
        """
        Classifies incoming user query into an appropriate QueryIntent.
        """
        q_lower = query.lower().strip()
        tokens = set(re.findall(r'[\w\u0900-\u097F]+', q_lower))

        # Check explicit regex patterns
        has_rule_pattern = bool(
            re.search(r'\b(rule\s*6|6\s*\(\s*1\s*\)|lmpc|pcr|act\s*2009|rules\s*2011)\b', q_lower)
            or any('\u0900' <= c <= '\u097F' for c in query)
        )
        has_data_pattern = bool(
            re.search(r'\b(how many|what is the (compliance|violation) rate|total scans|top brand|average score)\b', q_lower)
        )

        data_matches = len(tokens.intersection(self.DATA_KEYWORDS))
        rule_matches = len(tokens.intersection(self.RULE_KEYWORDS))

        if has_rule_pattern:
            rule_matches += 2
        if has_data_pattern:
            data_matches += 2

        # Classification logic
        if data_matches > 0 and rule_matches > 0:
            return QueryIntent.HYBRID
        elif data_matches > 0 and rule_matches == 0:
            return QueryIntent.DATA_QUERY
        elif rule_matches > 0 and data_matches == 0:
            return QueryIntent.RULE_LOOKUP
        else:
            return QueryIntent.UNKNOWN
