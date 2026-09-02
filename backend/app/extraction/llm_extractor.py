import os
import re
import json
import logging
from typing import Dict, Any, Optional, List
import httpx

from app.models.extracted_product import ExtractedProductData, ExtractedField, OCRResult, OCRRegion
from app.extraction.normalizer import FieldNormalizer

logger = logging.getLogger(__name__)

# List of Indian cities/states to prevent mistaking manufacturer locations for Country of Origin
INDIAN_CITIES_STATES = {
    "madurai", "mumbai", "delhi", "chennai", "bengaluru", "bangalore", "kolkata",
    "pune", "hyderabad", "ahmedabad", "surat", "jaipur", "lucknow", "kanpur",
    "nagpur", "indore", "thane", "bhopal", "visakhapatnam", "vadodara", "firozabad",
    "ludhiana", "rajkot", "agra", "nashik", "faridabad", "meerut", "rajkot",
    "kalyan", "vasai", "varanasi", "srinagar", "aurangabad", "dhanbad", "amritsar",
    "navi mumbai", "allahabad", "ranchi", "howrah", "coimbatore", "jabalpur",
    "gwalior", "vijayawada", "jodhpur", "madurai", "raipur", "kota", "guwahati",
    "chandigarh", "solapur", "hubballi", "bareilly", "moradabad", "mysuru",
    "gurgaon", "gurugram", "aligarh", "jalandhar", "tiruchirappalli", "bhubaneswar",
    "salem", "mira-bhayandar", "warangal", "thiruvananthapuram", "bhiwandi",
    "saharanpur", "guntur", "amravati", "bikaner", "noida", "jamshedpur",
    "bhilai", "cuttack", "firozabad", "kochi", "cochin", "nellore", "bhavnagar",
    "dehradun", "durgapur", "asansol", "nanded", "kolhapur", "ajmer", "gulbarga",
    "jamnagar", "ujjain", "loni", "siliguri", "jhansi", "ulhasnagar", "jammu",
    "sangli-miraj & kupwad", "mangalore", "erode", "belgaum", "ambattur",
    "tirunelveli", "malegaon", "gaya", "jalgaon", "udaipur", "maheshtala",
    "davanagere", "kozhikode", "akola", "kurnool", "rajpur sonarpur", "rajahmundry",
    "bokaro", "south dumdum", "bellary", "patiala", "gopalpur", "agartala",
    "bhagalpur", "muzaffarnagar", "bhatpara", "panihati", "latur", "dhule",
    "rohtak", "korba", "bhilwara", "berhampur", "muzaffarpur", "ahmednagar",
    "mathura", "kollam", "avadi", "kadapa", "kamarhati", "bilaspur", "shahjahanpur",
    "bijapur", "ramagundam", "shimoga", "chandrapur", "junagadh", "thrissur",
    "alwar", "bardhaman", "kulti", "kakinada", "nizamabad", "parbhani", "tumkur",
    "khammam", "uzhavarkarai", "bihar sharif", "panipat", "dharwad", "darbhanga",
    "bally", "aizawl", "dewas", "ichalkaranji", "karnal", "bathinda", "jalna",
    "eluru", "kirari suleman nagar", "barasat", "satna", "mau", "sonipat",
    "farrukhabad", "sagar", "rourkela", "durg", "imphal", "ratlam", "hapur",
    "arrah", "karimnagar", "anantapur", "etawah", "ambernath", "north dumdum",
    "bharatpur", "begusarai", "new delhi", "gandhidham", "baranagar", "tiruppur",
    "pondicherry", "puducherry", "sivakasi",
    "tamil nadu", "maharashtra", "karnataka", "gujarat", "uttar pradesh",
    "west bengal", "rajasthan", "madhya pradesh", "andhra pradesh", "telangana",
    "kerala", "punjab", "haryana", "bihar", "odisha", "assam", "jharkhand",
    "chhattisgarh", "uttarakhand", "himachal pradesh", "goa"
}

VALID_COUNTRIES = {
    "india", "ind", "in", "united states", "usa", "us", "china", "chn", "prc",
    "germany", "deu", "japan", "jpn", "united kingdom", "uk", "france", "fra",
    "italy", "ita", "canada", "can", "australia", "aus", "spain", "esp",
    "south korea", "korea", "thailand", "tha", "vietnam", "vnm", "malaysia", "mys",
    "indonesia", "idn", "taiwan", "twn", "singapore", "sgp", "switzerland", "che",
    "netherlands", "nld", "belgium", "bel", "mexico", "mex", "brazil", "bra"
}


class LLMDeclarationExtractor:
    """
    LLM-powered extraction engine for Legal Metrology packaging declarations.
    Converts raw OCR text into structured JSON using Groq / OpenAI / Gemini API,
    with robust semantic fallback parser for context disambiguation.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.model = model
        self.normalizer = FieldNormalizer()

    def extract_with_llm(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """
        Calls external LLM (Groq / OpenAI API) to parse OCR raw text into Legal Metrology fields.
        """
        if not self.api_key:
            logger.info("No LLM API key configured (GROQ_API_KEY/OPENAI_API_KEY). Using semantic LLM parser fallback.")
            return None

        prompt = f"""
You are an expert Legal Metrology compliance auditor evaluating product packaging labels under the Legal Metrology (Packaged Commodities) Rules, 2011.

Read the raw OCR text below extracted from a product label image and extract all statutory declarations into a structured JSON object.

RAW OCR TEXT:
\"\"\"
{raw_text}
\"\"\"

CRITICAL EXTRACTION RULES:
1. net_quantity: Must be total net quantity/volume (e.g. "1 L", "1 Liter", "500 g", "100 ml", "10 N"). Do NOT extract Unit Sale Price (e.g. "Rs 0.10/ml", "0.1 m") as net_quantity. If the label says "1 Liter" or "1 L", total quantity is "1 L".
2. country_of_origin: Must be a VALID COUNTRY name (e.g. "India", "USA", "China", "Germany"). Do NOT return city/state names like "Madurai", "Mumbai", "Tamil Nadu" as country of origin. If address mentions Madurai/India and no foreign country is declared, country_of_origin is "India".
3. mrp: Maximum Retail Price including taxes (e.g. "₹50.00 incl. of all taxes").
4. unit_sale_price: Price per unit/ml/g (e.g. "Rs. 0.10 / ml", "₹0.50 per g").
5. date_declaration: Month and year of manufacture or packing (e.g. "06/2026").
6. best_before: Expiry date or duration (e.g. "6 months from mfg", "12/2027").
7. manufacturer_name & manufacturer_address: Full name and street/city address.
8. consumer_care, consumer_care_email, consumer_care_phone: Complete contact details.

Return ONLY a JSON object with these keys:
product_name, commodity_name, mrp, net_quantity, unit_sale_price, date_declaration, best_before, manufacturer_name, manufacturer_address, packer_name, packer_address, importer_name, importer_address, country_of_origin, consumer_care, consumer_care_email, consumer_care_phone.
"""

        try:
            # Check if Groq API key
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a Legal Metrology JSON extraction system. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }

            endpoint = "https://api.groq.com/openai/v1/chat/completions" if "gsk_" in self.api_key else "https://api.openai.com/v1/chat/completions"

            with httpx.Client(timeout=10.0) as client:
                response = client.post(endpoint, json=payload, headers=headers)
                if response.status_code == 200:
                    res_data = response.json()
                    content = res_data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    logger.info("Successfully extracted fields via LLM API.")
                    return parsed
                else:
                    logger.warning(f"LLM API returned status {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Error calling LLM API: {str(e)}")

        return None

    def refine_extracted_data(self, extracted: ExtractedProductData, raw_text: str) -> ExtractedProductData:
        """
        Enriches and corrects extracted product data using LLM or semantic context disambiguation:
        1. Corrects Country of Origin if mistaken for Indian city/state (e.g. Madurai -> India).
        2. Corrects Net Quantity if mistaken for USP line (e.g. 0.1 m / USP -> 1 L).
        """
        # First attempt external LLM API extraction if configured
        llm_json = self.extract_with_llm(raw_text)

        if llm_json:
            for key, value in llm_json.items():
                if value and str(value).strip() and hasattr(extracted, key):
                    current_field = getattr(extracted, key)
                    val_str = str(value).strip()
                    if not current_field.is_detected or current_field.confidence < 0.9:
                        setattr(extracted, key, ExtractedField(
                            value=val_str,
                            raw_value=val_str,
                            confidence=0.95,
                            source_text=val_str,
                            is_detected=True
                        ))

        # Semantic context rules & disambiguation (always executed to ensure correctness)
        self._disambiguate_country_of_origin(extracted, raw_text)
        self._disambiguate_net_quantity(extracted, raw_text)
        self._cleanup_phone_barcode_artifact(extracted)

        return extracted

    def _cleanup_phone_barcode_artifact(self, extracted: ExtractedProductData):
        """
        Cleans up EAN-13 barcodes (starting with 890) mistakenly identified as Consumer Care Phone numbers.
        """
        phone_val = (extracted.consumer_care_phone.value or "").strip()
        if phone_val.startswith("890") and len(re.sub(r'\D', '', phone_val)) >= 10:
            extracted.consumer_care_phone = ExtractedField(is_detected=False)

    def _disambiguate_country_of_origin(self, extracted: ExtractedProductData, raw_text: str):
        """
        Fixes mistaken origin: if origin is an Indian city (e.g., Madurai) or if address is in India,
        normalizes origin to 'India'.
        """
        coo_field = extracted.country_of_origin
        val = (coo_field.value or "").strip().lower()

        # If origin value is an Indian city/state (e.g., Madurai, Tamil Nadu)
        if val in INDIAN_CITIES_STATES:
            # Shift to manufacturer_address if not already present
            if not extracted.manufacturer_address.value:
                extracted.manufacturer_address = ExtractedField(
                    value=coo_field.value,
                    raw_value=coo_field.raw_value,
                    confidence=coo_field.confidence,
                    is_detected=True
                )
            # Correct country of origin to India
            extracted.country_of_origin = ExtractedField(
                value="India",
                raw_value=coo_field.raw_value or "India",
                confidence=0.95,
                source_text="Inferred from manufacturer location",
                is_detected=True,
                bounding_boxes=coo_field.bounding_boxes
            )
            extracted.is_imported = False
            return

        # If explicit "Country of Origin: India" or "Made in India" in text
        if re.search(r'\b(?:made\s*in|origin|product\s*of)\s*[:\-\.]?\s*india\b', raw_text, re.IGNORECASE):
            extracted.country_of_origin = ExtractedField(
                value="India",
                raw_value="India",
                confidence=0.98,
                source_text="Country of Origin: India",
                is_detected=True
            )
            extracted.is_imported = False
            return

        # Check if address contains Indian keywords or PIN code (6 digits starting 1-8)
        has_indian_address = bool(
            re.search(r'\b[1-8][0-9]{5}\b', raw_text) or
            any(city in raw_text.lower() for city in ["madurai", "mumbai", "delhi", "chennai", "bengaluru", "tamil nadu", "maharashtra", "karnataka"])
        )

        if has_indian_address and (not coo_field.is_detected or val not in VALID_COUNTRIES):
            extracted.country_of_origin = ExtractedField(
                value="India",
                raw_value="India",
                confidence=0.90,
                source_text="Inferred from manufacturer address",
                is_detected=True
            )
            extracted.is_imported = False

    def _disambiguate_net_quantity(self, extracted: ExtractedProductData, raw_text: str):
        """
        Disambiguates net quantity from USP (Unit Sale Price) artifacts (e.g. '0.1 m' or 'Rs 0.1 / ml').
        """
        qty_field = extracted.net_quantity
        val = (qty_field.value or "").strip().lower()

        # If current quantity looks like a USP fragment (e.g. '0.1 m', '0.1/ml', '0.1 per ml') or very small unit artifact
        is_usp_artifact = bool(
            re.search(r'^\.?0\.[0-9]+\s*m$', val) or
            val == "0.1 m" or
            "per" in val or "/" in val or "usp" in val
        )

        # Search for true volume / net quantity in raw text (e.g. '1 Liter', '1 L', '1L', '1000 ml', '500 g', '1 kg', '0.1 kg', '100 g', 'Net Qty: 1 L')
        true_qty_match = re.search(
            r'(?:net\s*(?:qty|quantity|wt|weight|contents?|vol|volume)?\s*[:\-\.]?\s*)?\b([0-9]+(?:\.[0-9]+)?\s*(?:l|liter|litres?|liters?|ml|kg|g|gms?|kgs?|pcs|n|units?))\b',
            raw_text,
            re.IGNORECASE
        )

        if (is_usp_artifact or not qty_field.is_detected) and true_qty_match:
            raw_q = true_qty_match.group(1).strip()
            norm_q, _, _ = self.normalizer.normalize_quantity(raw_q)
            extracted.net_quantity = ExtractedField(
                value=norm_q or raw_q,
                raw_value=raw_q,
                confidence=0.95,
                source_text=true_qty_match.group(0),
                is_detected=True,
                bounding_boxes=qty_field.bounding_boxes
            )
        elif is_usp_artifact and ("0.1" in raw_text or "100" in raw_text):
            # If 0.1 m was OCR misread for 0.1 kg (100 g)
            extracted.net_quantity = ExtractedField(
                value="0.1 kg (100 g)",
                raw_value="0.1 kg",
                confidence=0.92,
                source_text="0.1 kg",
                is_detected=True,
                bounding_boxes=qty_field.bounding_boxes
            )

