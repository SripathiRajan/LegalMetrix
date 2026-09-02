"""
Rules Knowledge Base for Legal Metrology (Packaged Commodities) Rules grounding.
Provides semantic search over official English and Hindi legal texts from DoCA dataset.
"""

import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except Exception:
    SentenceTransformer = None
    HAS_SENTENCE_TRANSFORMERS = False


class RulesKnowledgeBase:
    """
    Knowledge Base for Legal Metrology rules grounded on the official DoCA dataset.
    Loads enriched rules.json and official_source index, and enables multilingual semantic search.
    """

    def __init__(
        self,
        rules_filepath: Optional[str] = None,
        index_filepath: Optional[str] = None,
        extracted_dir: Optional[str] = None,
        model_name: str = "all-MiniLM-L6-v2"
    ):
        base_dir = Path(__file__).parent
        
        if rules_filepath is None:
            self.rules_filepath = base_dir / "rules.json"
        else:
            self.rules_filepath = Path(rules_filepath)

        if index_filepath is None:
            self.index_filepath = base_dir / "official_source" / "rules_index.json"
        else:
            self.index_filepath = Path(index_filepath)

        if extracted_dir is None:
            self.extracted_dir = base_dir / "official_source" / "extracted"
        else:
            self.extracted_dir = Path(extracted_dir)

        self.model_name = model_name
        self.rules: List[Dict[str, Any]] = []
        self.index_documents: List[Dict[str, Any]] = []
        self.corpus: List[Dict[str, Any]] = []
        self.corpus_embeddings: Optional[np.ndarray] = None
        self.model = None

        # Load rules & index
        self._load_data()

        # Initialize vector embeddings
        self._init_embeddings()

    @property
    def rules_index(self) -> Dict[str, Any]:
        """Returns the structured index metadata dictionary."""
        return {
            "dataset_name": "Official DoCA Legal Metrology (Packaged Commodities) Rules & Amendments",
            "total_documents": len(self.index_documents),
            "documents": self.index_documents
        }

    def _load_data(self):
        """Loads enriched rules.json and official index JSON."""
        if self.rules_filepath.exists():
            with open(self.rules_filepath, "r", encoding="utf-8") as f:
                self.rules = json.load(f)

        if self.index_filepath.exists():
            with open(self.index_filepath, "r", encoding="utf-8") as f:
                idx_data = json.load(f)
                self.index_documents = idx_data.get("documents", [])

        # Build combined corpus for semantic search
        self.corpus = []
        
        # Add enriched rules to search corpus
        for rule in self.rules:
            text_parts = [
                rule.get("declaration_name", ""),
                rule.get("description", ""),
                rule.get("official_legal_reference", rule.get("legal_reference", "")),
                rule.get("english_text", ""),
                rule.get("hindi_text_snippet", ""),
                rule.get("applicability_notes", "")
            ]
            combined_text = "\n".join([p for p in text_parts if p]).strip()
            
            self.corpus.append({
                "type": "rule",
                "rule_id": rule.get("rule_id"),
                "declaration_name": rule.get("declaration_name"),
                "official_legal_reference": rule.get("official_legal_reference", rule.get("legal_reference")),
                "source_pdf": rule.get("source_pdf"),
                "english_text": rule.get("english_text"),
                "hindi_text_snippet": rule.get("hindi_text_snippet"),
                "last_amended_date": rule.get("last_amended_date"),
                "applicability_notes": rule.get("applicability_notes"),
                "search_text": combined_text
            })

        # Add index documents to search corpus
        for doc in self.index_documents:
            filename = doc.get("filename")
            title = doc.get("title", "")
            topics = " ".join(doc.get("key_topics", []))
            
            # Read snippet from extracted txt if available
            extracted_snippet = ""
            if self.extracted_dir.exists():
                txt_path = self.extracted_dir / (Path(filename).stem + ".txt")
                if txt_path.exists():
                    try:
                        with open(txt_path, "r", encoding="utf-8") as tf:
                            extracted_snippet = tf.read(1500)  # First 1500 chars
                    except Exception:
                        pass

            combined_doc_text = f"{title}\nTopics: {topics}\n{extracted_snippet}".strip()

            self.corpus.append({
                "type": "official_document",
                "rule_id": None,
                "declaration_name": title,
                "official_legal_reference": f"Official DoCA Document: {title} ({doc.get('date', '')})",
                "source_pdf": filename,
                "english_text": extracted_snippet[:500] if extracted_snippet else title,
                "hindi_text_snippet": extracted_snippet if any('\u0900' <= c <= '\u097F' for c in extracted_snippet) else None,
                "last_amended_date": doc.get("date"),
                "applicability_notes": f"Topics: {topics}",
                "search_text": combined_doc_text
            })

    def _init_embeddings(self):
        """Initializes sentence-transformer embeddings for semantic search."""
        if HAS_SENTENCE_TRANSFORMERS and self.corpus:
            try:
                self.model = SentenceTransformer(self.model_name)
                texts = [item["search_text"] for item in self.corpus]
                embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
                self.corpus_embeddings = embeddings
            except Exception as e:
                print(f"Warning: Could not initialize sentence transformer embeddings ({e}). Falling back to keyword search.")
                self.model = None

    def semantic_search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Perform semantic search over English and Hindi official texts.
        Returns the top_k most relevant official citations + source PDF info.
        """
        if not self.corpus:
            return []

        # Vector search if model and embeddings are ready
        if self.model is not None and self.corpus_embeddings is not None:
            try:
                query_emb = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
                scores = np.dot(self.corpus_embeddings, query_emb.T).squeeze(axis=1)
                top_indices = np.argsort(scores)[::-1][:top_k]

                results = []
                for idx in top_indices:
                    item = self.corpus[idx].copy()
                    item["score"] = float(round(scores[idx], 4))
                    item.pop("search_text", None)
                    results.append(item)
                return results
            except Exception as e:
                print(f"Vector search error ({e}), falling back to keyword search.")

        # Fallback keyword-based similarity search
        return self._keyword_search(query, top_k=top_k)

    def _keyword_search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Fallback keyword search when embeddings are unavailable."""
        query_words = set(re.findall(r'\w+', query.lower()))
        scores = []

        for item in self.corpus:
            text_words = set(re.findall(r'\w+', item["search_text"].lower()))
            overlap = len(query_words.intersection(text_words))
            score = overlap / (len(query_words) + 1e-5)
            scores.append(score)

        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            item = self.corpus[idx].copy()
            item["score"] = float(round(scores[idx], 4))
            item.pop("search_text", None)
            results.append(item)
        return results


def get_rules_knowledge_base() -> RulesKnowledgeBase:
    """Factory helper to obtain a singleton instance of RulesKnowledgeBase."""
    return RulesKnowledgeBase()
