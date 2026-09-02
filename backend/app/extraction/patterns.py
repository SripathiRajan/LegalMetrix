import re
from typing import Dict, List, Pattern

# Regular expression patterns for Legal Metrology declaration detection

# 1. Maximum Retail Price (MRP) patterns
# Recognizes: MRP ₹50, MRP Rs. 50, M.R.P. Rs 50, Maximum Retail Price: ₹50, MRP: 50.00, Rs. 100.00 (incl. of all taxes)
MRP_PATTERNS: List[Pattern] = [
    re.compile(r'(?:m\.?r\.?p\.?|max(?:imum)?\s*retail\s*price|mrp)\s*[:\-\.]?\s*(?:rs\.?|inr|₹)?\s*([0-9]{1,4}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)', re.IGNORECASE),
    re.compile(r'(?:(?:rs\.?|inr|₹)\s*([0-9]{1,4}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?))\s*(?:incl|inclusive)', re.IGNORECASE),
    re.compile(r'\b(?:rs\.?|inr|₹)\s*([0-9]{1,4}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)\b', re.IGNORECASE),
    re.compile(r'(?:m\.?r\.?p\.?|mrp)\s*[:\-\.]?\s*([0-9]+(?:\.[0-9]{1,2})?)', re.IGNORECASE)
]

# 2. Net Quantity patterns
# Recognizes: 100 g, 100g, 500 g, 1 kg, 1 L, 500 ml, 10 N, Net Qty: 200 g, Net Wt. 500g, Net Contents: 1 Litre
QUANTITY_PATTERNS: List[Pattern] = [
    re.compile(r'(?:net\s*(?:qty|quantity|wt|weight|contents?|volume)?\s*[:\-\.]?\s*)?([0-9]+(?:\.[0-9]+)?|\.[0-9]+)\s*(kg|g|mg|l|ml|cl|cm3|mm|cm|m|sq\s*cm|sq\s*m|cm2|m2|gms?\.?|kgs?\.?|ltrs?\.?|litres?|liters?|mls?\.?|n|u|units?|pieces?|pcs|nos?|count)\b', re.IGNORECASE),
    re.compile(r'\b([0-9]+(?:\.[0-9]+)?)\s*(kg|g|mg|l|ml|cl|n|u|pcs|gms|kgs|ltrs)\b', re.IGNORECASE)
]

# 3. Unit Sale Price (USP) patterns
USP_PATTERNS: List[Pattern] = [
    re.compile(r'(?:unit\s*sale\s*price|usp)\s*[:\-\.]?\s*(?:rs\.?|inr|₹)?\s*([0-9]+(?:\.[0-9]{1,2})?)\s*(?:/|per)\s*([a-zA-Z0-9]+)', re.IGNORECASE),
    re.compile(r'(?:rs\.?|inr|₹)\s*([0-9]+(?:\.[0-9]{1,2})?)\s*(?:/|per)\s*(?:g|kg|ml|l|m|piece|n|u|count)', re.IGNORECASE)
]

# 4. Date patterns (Manufacturing, Packaging, Import, Expiry)
# Recognizes: 06/2026, 06-2026, June 2026, Packed: 06/2026, Mfd: 06/2026, Mfg Date: 12/2025, PKD 01/26
DATE_PATTERNS: List[Pattern] = [
    re.compile(r'(?:mfd|mfg|manufactured|pkd|packed|pkg|imported|date\s*of\s*mfg|date\s*of\s*pkg|date\s*of\s*packing)\s*[:\-\.]?\s*([0-9]{1,2}[/\-\.][0-9]{2,4}|[a-zA-Z]{3,9}\s*[/\-\.\s]\s*[0-9]{2,4})', re.IGNORECASE),
    re.compile(r'\b(0?[1-9]|1[0-2])[/\-\.](20\d{2}|\d{2})\b'),
    re.compile(r'\b([a-zA-Z]{3,9})\s*[/\-\.\s]\s*(20\d{2}|\d{2})\b')
]

BEST_BEFORE_PATTERNS: List[Pattern] = [
    re.compile(r'(?:best\s*before|use\s*by|expiry\s*date|exp\.?\s*date|exp)\s*[:\-\.]?\s*([0-9]{1,2}[/\-\.][0-9]{2,4}|[a-zA-Z]{3,9}\s*[/\-\.\s]\s*[0-9]{2,4}|[0-9]+\s*months?(?:\s*from\s*(?:mfg|pkg|packaging|manufacture))?)', re.IGNORECASE),
    re.compile(r'best\s*before\s*([0-9]+\s*months?(?:\s*from\s*(?:mfg|pkg|packaging|manufacture))?)', re.IGNORECASE)
]

# 5. Manufacturer / Packer / Importer keywords and regex
MANUFACTURER_KEYWORDS: List[str] = [
    "manufactured by",
    "manufactured & marketed by",
    "mfg by",
    "mfd by",
    "produced by",
    "marketed by"
]

PACKER_KEYWORDS: List[str] = [
    "packed by",
    "packed & marketed by",
    "pkd by",
    "re-packed by",
    "packaged by"
]

IMPORTER_KEYWORDS: List[str] = [
    "imported by",
    "importer",
    "imported and marketed by",
    "imported & distributed by"
]

# 6. Consumer Care keywords and patterns
CONSUMER_CARE_KEYWORDS: List[str] = [
    "consumer care",
    "customer care",
    "customer service",
    "toll free",
    "helpline",
    "contact us",
    "for feedback",
    "for complaints",
    "in case of complaints",
    "grievance officer"
]

EMAIL_PATTERN: Pattern = re.compile(r'\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b')
PHONE_PATTERN: Pattern = re.compile(r'(?:\+?91[\-\s]?)?(?:1800[\-\s]?[0-9]{3,4}[\-\s]?[0-9]{3,4}|[6-9][0-9]{9}|\b\d{3,5}[\-\s]?\d{6,8}\b)')

# 7. Country of Origin patterns
# Recognizes: Country of Origin: India, Made in India, Country of Origin: China, Product of China
ORIGIN_PATTERNS: List[Pattern] = [
    re.compile(r'(?:country\s*of\s*origin|origin|made\s*in|product\s*of)\s*[:\-\.]?\s*([a-zA-Z\s]{2,25})', re.IGNORECASE),
    re.compile(r'\bmade\s*in\s*([a-zA-Z\s]{2,25})\b', re.IGNORECASE)
]
