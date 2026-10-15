"""political_guardrail.py - gerbang domain politik (HEURISTIK, belum terukur).

Aturan: lolos jika >=1 istilah KUAT atau >=2 istilah LEMAH berbeda.
Akronim ambigu (PAN, MK, PD) hanya dicocokkan jika tertulis HURUF BESAR
('pan' = wajan, tidak dihitung).
Daftar ini AWAL. Ukur pada set berlabel (politik vs non-politik, termasuk yang
menyebut tokoh/lembaga) sebelum menambah/menghapus istilah, dan jangan menyetel
daftar pada kasus uji yang sama.
"""
import re
from typing import List, Tuple

STRONG = {
    "presiden", "wapres", "wakil presiden", "menteri", "kpu", "bawaslu", "dpr",
    "mpr", "dpd", "mahkamah konstitusi", "pemilu", "pilpres", "pilkada",
    "pdi-p", "pdip", "gerindra", "golkar", "nasdem", "pks", "demokrat", "pkb",
    "bansos", "apbn", "kpk", "kejaksaan", "perppu", "undang-undang",
    "gubernur", "bupati", "wali kota", "walikota", "capres", "cawapres",
    "jokowi", "prabowo", "gibran", "megawati", "anies", "ganjar",
}
WEAK = {
    "partai", "korupsi", "polri", "tni", "kebijakan", "kampanye", "debat",
    "koalisi", "oposisi", "pemerintah", "dprd", "suara", "surat suara",
    "anggaran", "legislatif", "eksekutif",
}
CASE_SENSITIVE_ACRONYMS = {"PAN", "MK", "PD"}  # dihitung kuat, hanya huruf besar


def _has(term: str, text: str, flags=0) -> bool:
    return re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, flags) is not None


def check_political_domain(text: str) -> Tuple[bool, List[str]]:
    original = text or ""
    low = original.lower()
    strong = sorted(k for k in STRONG if _has(k, low))
    weak = sorted(k for k in WEAK if _has(k, low))
    acr = sorted(a for a in CASE_SENSITIVE_ACRONYMS if _has(a, original))

    detected = [x.upper() for x in strong + acr + weak]
    is_political = bool(strong or acr or len(weak) >= 2)
    return is_political, detected