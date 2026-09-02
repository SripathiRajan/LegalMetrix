import re
from typing import Optional, Tuple


class FieldNormalizer:
    """
    Normalizes extracted raw values into standard formats while preserving
    original characters and non-standard symbols for Rule Engine evaluation.
    """

    @staticmethod
    def normalize_mrp(raw_mrp: str) -> Tuple[str, Optional[float]]:
        """
        Normalizes MRP string (e.g., 'MRP Rs. 50.00' -> '₹50.00').
        Extracts numeric float value and preserves 'incl. of all taxes' context.
        """
        if not raw_mrp:
            return "", None

        cleaned = raw_mrp.strip()
        # Find numeric amount
        num_match = re.search(r'([0-9]{1,4}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)', cleaned)
        if not num_match:
            return cleaned, None

        num_str = num_match.group(1).replace(",", "")
        try:
            amount = float(num_str)
            # Preserve original decimal format if present (e.g. 50.00 vs 50)
            has_taxes = bool(re.search(r'incl', cleaned, re.IGNORECASE))
            tax_str = " incl. of all taxes" if has_taxes else ""
            
            if "." in num_match.group(1):
                formatted_num = f"{amount:.2f}"
            else:
                formatted_num = f"{int(amount)}"

            normalized = f"₹{formatted_num}{tax_str}"
            return normalized, amount
        except ValueError:
            return cleaned, None

    @staticmethod
    def normalize_quantity(raw_qty: str) -> Tuple[str, Optional[float], Optional[str]]:
        """
        Normalizes quantity while preserving unit exactly (standard or non-standard).
        DO NOT convert illegal units (e.g. 'gms', 'kgs') so Rule Engine can detect them.
        """
        if not raw_qty:
            return "", None, None

        cleaned = raw_qty.strip()
        match = re.search(r'([0-9]+(?:\.[0-9]+)?|\.[0-9]+)\s*([a-zA-Z0-9\.\^²³]+)', cleaned)
        if not match:
            return cleaned, None, None

        num_str = match.group(1)
        unit_str = match.group(2).strip()

        try:
            num = float(num_str)
            normalized = f"{num:g} {unit_str}"
            return normalized, num, unit_str
        except ValueError:
            return cleaned, None, unit_str

    @staticmethod
    def normalize_date(raw_date: str) -> str:
        """
        Normalizes date strings into standard MM/YYYY where possible.
        """
        if not raw_date:
            return ""

        cleaned = raw_date.strip()
        # Clean common prefixes
        cleaned = re.sub(r'^(?:mfd|mfg|pkd|packed|pkg|imported|best\s*before|use\s*by|date\s*of\s*(?:mfg|pkg|packing))?\s*[:\-\.]?\s*', '', cleaned, flags=re.IGNORECASE).strip()

        # Handle MM/YYYY or MM-YYYY
        m = re.match(r'^(0?[1-9]|1[0-2])[/\-\.](20\d{2}|\d{2})$', cleaned)
        if m:
            month = int(m.group(1))
            year = m.group(2)
            if len(year) == 2:
                year = f"20{year}"
            return f"{month:02d}/{year}"

        # Handle Month YYYY (e.g. June 2026 -> 06/2026)
        months_map = {
            "jan": "01", "january": "01",
            "feb": "02", "february": "02",
            "mar": "03", "march": "03",
            "apr": "04", "april": "04",
            "may": "05",
            "jun": "06", "june": "06",
            "jul": "07", "july": "07",
            "aug": "08", "august": "08",
            "sep": "09", "september": "09",
            "oct": "10", "october": "10",
            "nov": "11", "november": "11",
            "dec": "12", "december": "12"
        }

        m_word = re.match(r'^([a-zA-Z]+)\s*[/\-\.\s]\s*(20\d{2}|\d{2})$', cleaned)
        if m_word:
            mon_str = m_word.group(1).lower()
            year_str = m_word.group(2)
            if len(year_str) == 2:
                year_str = f"20{year_str}"
            if mon_str in months_map:
                return f"{months_map[mon_str]}/{year_str}"

        return cleaned

    @staticmethod
    def normalize_country(raw_origin: str) -> str:
        """
        Normalizes country of origin string.
        """
        if not raw_origin:
            return ""

        cleaned = raw_origin.strip()
        cleaned = re.sub(r'^(?:country\s*of\s*origin|origin|made\s*in|product\s*of)\s*[:\-\.]?\s*', '', cleaned, flags=re.IGNORECASE).strip()
        # Clean any trailing punctuation
        cleaned = cleaned.rstrip(".,;:- ")
        return cleaned.title() if len(cleaned) > 2 else cleaned.upper()
