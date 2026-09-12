import re
from typing import Tuple, List

# Kamus kata kunci isu sosial-politik Indonesia
POLITICAL_KEYWORDS = {
    "presiden", "wapres", "menteri", "kpu", "bawaslu", "dpr", "mpr", "dpd",
    "mahkamah konstitusi", "mk", "pemilu", "pilpres", "pilkada", "partai",
    "pdi-p", "gerindra", "golkar", "nasdem", "pks", "demokrat", "pkb", "pan",
    "bansos", "apbn", "korupsi", "kpk", "kejaksaan", "polri", "tni", "kebijakan",
    "undang-undang", "perppu", "kampanye", "debat", "koalisi", "oposisi"
}

def check_political_domain(text: str) -> Tuple[bool, List[str]]:
    """
    Mengecek apakah naskah berita mengandung minimal 1 kata kunci domain politik.
    """
    clean_text = text.lower()
    detected_entities = []
    
    for keyword in POLITICAL_KEYWORDS:
        # Regex boundary word check
        if re.search(r'\b' + re.escape(keyword) + r'\b', clean_text):
            detected_entities.append(keyword.upper())

    is_political = len(detected_entities) > 0
    return is_political, detected_entities