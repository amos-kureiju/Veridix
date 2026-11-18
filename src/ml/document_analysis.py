"""Eksperimen penilaian naskah dengan rentang sumber yang dapat ditelusuri."""

import re
import unicodedata
from typing import Literal, Sequence, TypedDict

import numpy as np

from src.ml.inference import BATCH, MAX_LEN, Penilai, putuskan
from src.utils.praproses import MAX_WORDS

MAX_DOCUMENT_SEGMENTS = 64
_PARAGRAPH_BREAK = re.compile(r"\n[^\S\n]*\n")
_SENTENCE_END = re.compile(r"[.!?…][”’\"'»)\]}]*$")


class DocumentBlock(TypedDict):
    text: str
    start_char: int
    pages: list[tuple[int, int, int]]


class DocumentSegment(TypedDict):
    start_char: int
    end_char: int
    start_word: int
    end_word: int
    text: str
    token_count: int | None
    status: Literal["dinilai", "ambigu", "ditolak", "gagal", "belum_dinilai"]
    label: str | None
    votes_hoax: str | None
    reason: str | None
    page_numbers: list[int]


def _only_invisible(word: str) -> bool:
    return all(unicodedata.category(char) in {"Cf", "Cc"} for char in word)


def _count_tokens(backend, text: str) -> int:
    count = backend.count_tokens(text)
    if isinstance(count, bool) or not isinstance(count, (int, np.integer)) or count <= 0:
        raise ValueError("Jumlah token tidak tersedia.")
    return int(count)


def _fit_span(text, words, start, limit, backend):
    def count(end):
        return _count_tokens(backend, text[words[start].start():words[end - 1].end()])

    end = limit
    token_count = count(end)
    if token_count > MAX_LEN and end > start + 1:
        end = start + 1
        token_count = count(end)
        if token_count <= MAX_LEN:
            # Temukan prefiks yang muat; keputusan selalu berdasar hitung persis.
            low, high = end + 1, limit - 1
            while low <= high:
                middle = (low + high) // 2
                candidate_tokens = count(middle)
                if candidate_tokens > MAX_LEN:
                    high = middle - 1
                else:
                    end, token_count = middle, candidate_tokens
                    low = middle + 1

    if end < limit or (end == start + MAX_WORDS and end < len(words)):
        for sentence_end in range(end - 1, start + (end - start + 1) // 2 - 1, -1):
            if _SENTENCE_END.search(words[sentence_end - 1].group()):
                sentence_tokens = count(sentence_end)
                if sentence_tokens <= MAX_LEN:
                    return sentence_end, sentence_tokens
    return end, token_count


def _score_segments(segments: list[DocumentSegment], predictor: Penilai) -> None:
    backend = predictor.backend
    n_seeds = len(backend.seeds)
    for offset in range(0, len(segments), BATCH):
        batch = segments[offset:offset + BATCH]
        try:
            scores = np.asarray(backend.seed_probs_each_untruncated(
                [segment["text"] for segment in batch],
                [segment["token_count"] for segment in batch],
            ))
            if (
                not n_seeds
                or scores.shape != (len(batch), n_seeds)
                or scores.dtype.kind not in "fiu"
            ):
                raise ValueError("Keluaran model tidak sesuai.")
        except Exception:
            for segment in batch:
                segment.update(status="gagal", reason="Model gagal menilai segmen ini.")
            continue
        for segment, row in zip(batch, scores):
            if not np.all(np.isfinite(row) & (row >= 0) & (row <= 1)):
                segment.update(status="gagal", reason="Skor model untuk segmen ini tidak valid.")
                continue
            votes = int(np.count_nonzero(row >= 0.5))
            try:
                status, label = putuskan(votes, n_seeds, rule=predictor.rule)
            except ValueError:
                segment.update(status="gagal", reason="Aturan voting model tidak valid.")
                continue
            segment.update(status=status, label=label, votes_hoax=f"{votes}/{n_seeds}")


def analyze_document(
    blocks: Sequence[DocumentBlock], predictor: Penilai,
) -> list[DocumentSegment]:
    """Nilai setiap rentang tanpa praproses pemotong dan tanpa label gabungan."""
    backend = predictor.backend
    try:
        special_tokens = _count_tokens(backend, "")
    except Exception:
        special_tokens = None

    result: list[DocumentSegment] = []
    pending: list[DocumentSegment] = []
    planned = 0
    words_before_block = 0
    for block in blocks:
        text = block["text"]
        words = list(re.finditer(r"\S+", text))
        start = 0
        while start < len(words):
            token_count = None
            reason = None
            status = "belum_dinilai"
            if planned >= MAX_DOCUMENT_SEGMENTS:
                end = len(words)
                reason = f"Batas {MAX_DOCUMENT_SEGMENTS} segmen per permintaan tercapai."
            else:
                planned += 1
                end = min(start + MAX_WORDS, len(words))
                if _only_invisible(words[start].group()):
                    end = start + 1
                    status = "ditolak"
                    reason = "Bagian ini hanya memuat karakter kontrol atau format tak terlihat."
                else:
                    for boundary in range(start + 1, end):
                        if (
                            _PARAGRAPH_BREAK.search(text, words[boundary - 1].end(), words[boundary].start())
                            or _only_invisible(words[boundary].group())
                        ):
                            end = boundary
                            break
                    try:
                        if special_tokens is None:
                            raise ValueError("Jumlah token khusus tidak tersedia.")
                        end, token_count = _fit_span(text, words, start, end, backend)
                    except Exception:
                        status = "gagal"
                        reason = "Tokenizer gagal memeriksa segmen ini."
                    else:
                        if token_count <= special_tokens:
                            status = "ditolak"
                            reason = "Bagian ini tidak menghasilkan token isi."
                        elif token_count > MAX_LEN:
                            status = "ditolak"
                            reason = f"Satu kata melampaui batas {MAX_LEN} token model."

            local_start, local_end = words[start].start(), words[end - 1].end()
            start_char = block["start_char"] + local_start
            end_char = block["start_char"] + local_end
            segment: DocumentSegment = {
                "start_char": start_char,
                "end_char": end_char,
                "start_word": words_before_block + start + 1,
                "end_word": words_before_block + end,
                "text": text[local_start:local_end],
                "token_count": token_count,
                "status": status,
                "label": None,
                "votes_hoax": None,
                "reason": reason,
                "page_numbers": sorted({
                    page for page, page_start, page_end in block["pages"]
                    if start_char < page_end and page_start < end_char
                }),
            }
            result.append(segment)
            if status == "belum_dinilai" and reason is None:
                pending.append(segment)
            start = end
        words_before_block += len(words)

    if pending:
        _score_segments(pending, predictor)
    return result
