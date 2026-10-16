"""
src/utils/political_guardrail.py — guardrail domain.

DEFINISI DOMAIN = DEFINISI KORPUS LATIH. Daftar di bawah disalin otomatis (bukan diketik ulang) dari
01b_rebuild_dataset_final.py: SUB_TOPIC_RULES + NOISE dengan pencocokan batas-kata. Sebuah teks dianggap
"dalam cakupan" bila ia akan lolos filter politik saat korpus dibangun. Dengan begitu guardrail tidak
menambah aturan baru yang belum pernah dilihat model.

Catatan: filter korpus diterapkan pada teks PENUH (sebelum dipotong 60 kata); karena itu guardrail dipanggil
pada teks penuh yang sudah disanitasi, bukan pada teks yang sudah dipotong.
Ukur selaras-tidaknya dengan data beku memakai kalibrasi_gerbang_domain.py (khususnya asimetri hoaks vs fakta).
"""
import re
from typing import List, Tuple

SUB_TOPIC_RULES = {'pemilu': ['pemilu',
            'pilpres',
            'pilkada',
            'kpu',
            'bawaslu',
            'surat suara',
            'sirekap',
            'coblos',
            'capres',
            'cawapres',
            'cawagub',
            'caleg',
            'debat',
            'partai',
            'pdip',
            'gerindra',
            'golkar',
            'nasdem',
            'pks',
            'demokrat',
            'kpud',
            'panwaslu',
            'koalisi',
            'oposisi',
            'cawe-cawe',
            'dinasti',
            'legislatif'],
 'kebijakan': ['bansos',
               'subsidi',
               'bbm',
               'ikn',
               'apbn',
               'apbd',
               'pajak',
               'omnibus',
               'undang-undang',
               'perpres',
               'perda',
               'tarif listrik',
               'bpjs',
               'kebijakan pemerintah',
               'asn',
               'bumn',
               'pertamina',
               'bulog',
               'beras bansos',
               'makan siang',
               'kemensos',
               'kemenkeu',
               'kemendagri',
               'reshuffle',
               'kabinet',
               'istana negara',
               'anggaran'],
 'tokoh': ['jokowi',
           'prabowo',
           'gibran',
           'anies',
           'ganjar',
           'megawati',
           'menteri',
           'presiden',
           'pejabat',
           'mahfud',
           'gubernur',
           'bupati',
           'walikota',
           'dpr',
           'mpr',
           'dprd',
           'puan',
           'erick thohir',
           'bahlil',
           'kaesang',
           'ridwan kamil',
           'ahok',
           'khofifah',
           'kades',
           'sri mulyani',
           'luhut',
           'nadiem',
           'basuki',
           'tito karnavian',
           'yasonna',
           'paspampres'],
 'hukum': ['korupsi',
           'kpk',
           'mk',
           'mahkamah',
           'polri',
           'kejaksaan',
           'tangkap',
           'ott',
           'sidang',
           'vonis',
           'hakim',
           'polisi',
           'tni',
           'aparat',
           'kejagung',
           'jaksa',
           'kasasi',
           'mahkamah agung',
           'yudikatif']}

NOISE = ['hujan es',
 'imunitas',
 'kanker',
 'diabetes',
 'ramuan',
 'vaksin hpv',
 'stroke',
 'gempa bumi',
 'tsunami',
 'cuaca ekstrem',
 'pelatih timnas',
 'liga 1',
 'piala aff',
 'frank de boer',
 'ronaldo',
 'messi',
 'shin tae-yong',
 'pesulap',
 'zodiak',
 'air kelapa',
 'janin',
 'kehamilan',
 'rahim',
 'kolesterol',
 'asam urat',
 'lowongan',
 'loker',
 'rekrutmen',
 'pendaftaran kerja',
 'pt pertamina persero loker',
 'seleksi bumn']

DOMAIN_TOPICS = ("pemilu", "kebijakan", "tokoh", "hukum")


def _wb(words):
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(w) for w in words) + r")(?!\w)", re.I)


_RULES = {k: _wb(v) for k, v in SUB_TOPIC_RULES.items()}
_NOISE = _wb(NOISE)


def sub_topik(text: str) -> Tuple[str, List[str]]:
    """Urutan sama dengan topic_wb() di 01b: NOISE dulu, lalu aturan sub-topik, lalu 'umum'."""
    m = _NOISE.search(text)
    if m:
        return "bukan_politik", [m.group(0).lower()]
    for k, rx in _RULES.items():
        m = rx.search(text)
        if m:
            return k, [m.group(0).lower()]
    return "umum", []


def check_political_domain(text: str) -> Tuple[bool, str, List[str]]:
    """(dalam_cakupan, sub_topik, istilah_pemicu)."""
    topik, terms = sub_topik(text)
    return topik in DOMAIN_TOPICS, topik, terms