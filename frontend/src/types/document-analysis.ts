export const DOCUMENT_SEGMENT_WORD_LIMIT = 60;
const DOCUMENT_SEGMENT_TOKEN_LIMIT = 128;

export interface DocumentPage {
    page_number: number;
    text: string | null;
}

export type DocumentAnalysisRequest = { text: string; pages?: never } | { pages: DocumentPage[]; text?: never };

const documentStatuses = ["lengkap", "parsial", "gagal", "ditolak"] as const;
const segmentStatuses = ["dinilai", "ambigu", "ditolak", "gagal", "belum_dinilai"] as const;

export type DocumentStatus = typeof documentStatuses[number];
export type DocumentSegmentStatus = typeof segmentStatuses[number];

export interface DocumentSegment {
    start_char: number;
    end_char: number;
    start_word: number;
    end_word: number;
    text: string;
    token_count: number | null;
    status: DocumentSegmentStatus;
    label: string | null;
    votes_hoax: string | null;
    reason: string | null;
    page_numbers: number[];
}

export interface DocumentAnalysisResult {
    status: DocumentStatus;
    total_words: number;
    analyzed_words: number;
    missing_pages: number[];
    segments: DocumentSegment[];
    reason: string | null;
}

// Match Python str.split whitespace in the document API, including its Unicode separators.
const whitespace = /[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]/u;

export function documentWordCount(text: string): number {
    return text.split(whitespace).filter(Boolean).length;
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isCount(value: unknown): value is number {
    return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}

function isMessage(value: unknown): value is string {
    return typeof value === "string" && value.trim().length > 0;
}

function matchesNumbers(value: unknown, expected: number[]): boolean {
    return Array.isArray(value) && value.length === expected.length && expected.every((number, index) => number === value[index]);
}

export function isUsableDocumentResult(value: unknown, request: DocumentAnalysisRequest): value is DocumentAnalysisResult {
    if (!isRecord(value) || !documentStatuses.some(status => status === value.status) || !Array.isArray(value.segments)) return false;

    const suppliedPages = request.pages?.filter(page => page.text !== null) ?? [];
    const expectedMissing = request.pages?.filter(page => page.text === null).map(page => page.page_number) ?? [];
    const source = request.text ?? suppliedPages.map(page => page.text).join("\n\n");
    const characters = Array.from(source);
    const words: { start: number; end: number }[] = [];
    for (let index = 0; index < characters.length; index++) {
        if (whitespace.test(characters[index])) continue;
        const start = index;
        while (index + 1 < characters.length && !whitespace.test(characters[index + 1])) index++;
        words.push({ start, end: index + 1 });
    }
    const total = words.length;
    if (value.total_words !== total || !matchesNumbers(value.missing_pages, expectedMissing) || !isCount(value.analyzed_words)) return false;
    if (value.status === "ditolak") {
        return value.segments.length === 0 && value.analyzed_words === 0 && isMessage(value.reason);
    }

    let nextPageStart = 0;
    const pageSpans = suppliedPages.map(page => {
        const start = nextPageStart;
        const end = start + Array.from(page.text ?? "").length;
        nextPageStart = end + 2;
        return { start, end, number: page.page_number };
    });
    let expectedWord = 1;
    let analyzed = 0;
    for (const segment of value.segments) {
        if (!isRecord(segment) || !segmentStatuses.some(status => status === segment.status) ||
            segment.start_word !== expectedWord || !isCount(segment.end_word) ||
            segment.end_word < expectedWord || segment.end_word > total) return false;

        const start = words[expectedWord - 1].start;
        const end = words[segment.end_word - 1].end;
        if (segment.start_char !== start || segment.end_char !== end ||
            segment.text !== characters.slice(start, end).join("")) return false;
        const wordCount = segment.end_word - expectedWord + 1;
        const expectedPages = pageSpans.filter(page => page.start < end && page.end > start)
            .map(page => page.number);
        if (!matchesNumbers(segment.page_numbers, expectedPages) ||
            expectedPages.some((page, index) => index > 0 && page !== expectedPages[index - 1] + 1) ||
            (segment.token_count !== null && !isCount(segment.token_count))) return false;

        if (segment.status === "dinilai" || segment.status === "ambigu") {
            const label = segment.status === "ambigu" ? segment.label === "PERLU VERIFIKASI (SEED TIDAK SEPAKAT)"
                : segment.label === "BERPOLA HOAKS" || segment.label === "TIDAK BERPOLA HOAKS";
            if (!label || wordCount > DOCUMENT_SEGMENT_WORD_LIMIT || !isCount(segment.token_count) ||
                segment.token_count === 0 || segment.token_count > DOCUMENT_SEGMENT_TOKEN_LIMIT || segment.reason !== null ||
                typeof segment.votes_hoax !== "string" || !/^[0-3]\/3$/.test(segment.votes_hoax)) return false;
            analyzed += wordCount;
        } else if (!isMessage(segment.reason) || segment.label !== null || segment.votes_hoax !== null ||
            (segment.status !== "belum_dinilai" && wordCount > DOCUMENT_SEGMENT_WORD_LIMIT)) return false;

        expectedWord = segment.end_word + 1;
    }

    if (expectedWord !== total + 1 || analyzed !== value.analyzed_words) return false;
    if (analyzed === 0) return value.status === "gagal" && isMessage(value.reason);
    if (analyzed < total || expectedMissing.length > 0) return value.status === "parsial" && isMessage(value.reason);
    return value.status === "lengkap" && value.reason === null;
}
