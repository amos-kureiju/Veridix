import type { LimeTopWords, UserSettings } from "@/types/user";

export const SETTINGS_KEY = "veridix_user_settings";

export const DEFAULT_SETTINGS: UserSettings = {
    show_lime_chart: true,
    lime_top_words: 3,

    // Nilai tetap untuk kompatibilitas dengan tipe yang sekarang.
    auto_ocr_preview: true,
    notify_on_feedback: false,
    default_export_format: "CSV",
    language: "id",
};

function isTopWords(value: unknown): value is LimeTopWords {
    return value === 3 || value === 5 || value === 7;
}

export function normalizeUserSettings(
    value: unknown,
    legacyTopWords?: unknown,
): UserSettings {
    const data: Record<string, unknown> =
        typeof value === "object" &&
            value !== null &&
            !Array.isArray(value)
            ? (value as Record<string, unknown>)
            : {};

    return {
        ...DEFAULT_SETTINGS,

        show_lime_chart:
            typeof data.show_lime_chart === "boolean"
                ? data.show_lime_chart
                : DEFAULT_SETTINGS.show_lime_chart,

        lime_top_words: isTopWords(data.lime_top_words)
            ? data.lime_top_words
            : isTopWords(legacyTopWords)
                ? legacyTopWords
                : 3,
    };
}

export function readUserSettings(): UserSettings {
    if (typeof window === "undefined") {
        return { ...DEFAULT_SETTINGS };
    }

    try {
        let stored: unknown = null;
        const raw = localStorage.getItem(SETTINGS_KEY);

        try {
            stored = raw === null ? null : JSON.parse(raw);
        } catch {
            // JSON rusak akan menggunakan nilai bawaan.
        }

        // Pertahankan pilihan jumlah kata dari penyimpanan versi lama.
        const legacyRaw = localStorage.getItem("veridix_lime_top_words");
        const legacyTopWords = legacyRaw !== null ? Number(legacyRaw) : undefined;

        return normalizeUserSettings(stored, legacyTopWords);
    } catch {
        // Menangani kondisi saat akses localStorage dibatasi oleh browser.
        return { ...DEFAULT_SETTINGS };
    }
}