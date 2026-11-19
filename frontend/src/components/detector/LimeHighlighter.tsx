"use client";

import { useMemo } from "react";
import AIAnalysisIcon from "@/components/shared/AIAnalysisIcon";
import type { LimeToken } from "@/types/detector";

interface LimeHighlighterProps {
    tokens?: LimeToken[];
    text?: string;
    topHoax?: Array<{ word: string; score: number }>;
    topFact?: Array<{ word: string; score: number }>;
    showChart?: boolean;
    topWordsCount?: 3 | 5 | 7;
    prediction?: string;
    numSamples?: number;
}

// PERBAIKAN AUDIT: Mengembalikan null jika rusak/hilang (TIDAK dipaksa menjadi 0)
const parseWeightStrict = (raw: any): number | null => {
    if (raw === null || raw === undefined || typeof raw === "boolean") {
        return null;
    }
    if (typeof raw === "number") {
        return Number.isFinite(raw) ? raw : null;
    }
    if (typeof raw === "string" && raw.trim() !== "") {
        const num = Number(raw.trim());
        return Number.isFinite(num) ? num : null;
    }
    return null;
};

export default function LimeHighlighter({
    tokens = [],
    text,
    topHoax = [],
    topFact = [],
    prediction,
    numSamples,
    showChart = true,
    topWordsCount = 3
}: LimeHighlighterProps) {
    const wordLimit = topWordsCount === 5 || topWordsCount === 7 ? topWordsCount : 3;

    // ── 1. SANITASI TOKEN DENGAN PEMBEDAAN BOBOT NULL VS NOL ──
    const validTokens = useMemo(() => {
        if (!Array.isArray(tokens)) return [];
        return tokens
            .filter((t) => t && typeof t === "object" && typeof t.word === "string" && t.word.trim() !== "")
            .map((t: any) => {
                const safeWeight = parseWeightStrict(t.weight !== undefined ? t.weight : t.score);
                // Arah pengaruh mengikuti tanda bobot, bukan label metadata yang bisa bertentangan.
                let infType: "hoax" | "fact" | "neutral" = "neutral";
                if (safeWeight !== null) {
                    if (safeWeight < 0) {
                        infType = "fact";
                    } else if (safeWeight > 0) {
                        infType = "hoax";
                    }
                }

                return {
                    word: String(t.word),
                    weight: safeWeight, // bernilai number ATAU null
                    influence: infType
                };
            });
    }, [tokens]);

    // Deteksi apakah ada token yang bobotnya tidak tersedia
    const hasUnavailableWeights = useMemo(() => {
        return validTokens.some((t) => t.weight === null);
    }, [validTokens]);

    // Peta kata untuk penyorotan inline pada teks asli/OCR (pertahankan kapitalisasi)
    const tokenMap = useMemo(() => {
        const map = new Map<string, { weight: number | null; influence: "hoax" | "fact" | "neutral" }>();
        for (const t of validTokens) {
            const key = t.word.trim();
            if (key && !map.has(key)) {
                map.set(key, { weight: t.weight, influence: t.influence });
            }
        }
        return map;
    }, [validTokens]);

    const displayTextTokens = useMemo(() => {
        if (typeof text === "string" && text.trim().length > 0) {
            const segments = text.split(/([\p{L}\p{N}_]+)/u);
            return segments.map((part, idx) => {
                if (!part) return null;
                const cleanWord = part.trim();
                const matched = cleanWord ? tokenMap.get(cleanWord) : undefined;
                if (!matched) {
                    return <span key={idx}>{part}</span>;
                }
                let badgeStyle = "";
                if (matched.weight !== null) {
                    if (matched.influence === "hoax" && matched.weight > 0) {
                        badgeStyle = "bg-rose-100 text-rose-800 font-bold px-1 py-0.5 rounded border border-rose-200 mx-0.5 shadow-2xs inline-block";
                    } else if (matched.influence === "fact" && matched.weight < 0) {
                        badgeStyle = "bg-emerald-100 text-emerald-800 font-bold px-1 py-0.5 rounded border border-emerald-200 mx-0.5 shadow-2xs inline-block";
                    }
                }
                const tooltipTitle = matched.weight !== null
                    ? `Bobot Pengaruh: ${matched.weight > 0 ? "+" : ""}${matched.weight.toFixed(4)}`
                    : "Bobot Pengaruh: Tidak tersedia";
                return (
                    <span key={idx} className={badgeStyle} title={tooltipTitle}>
                        {part}
                    </span>
                );
            });
        }

        return validTokens.map((item, idx) => {
            let badgeStyle = "";
            if (item.weight !== null) {
                if (item.influence === "hoax" && item.weight > 0) {
                    badgeStyle = "bg-rose-100 text-rose-800 font-bold px-1 py-0.5 rounded border border-rose-200 mx-0.5 shadow-2xs inline-block";
                } else if (item.influence === "fact" && item.weight < 0) {
                    badgeStyle = "bg-emerald-100 text-emerald-800 font-bold px-1 py-0.5 rounded border border-emerald-200 mx-0.5 shadow-2xs inline-block";
                }
            }

            const tooltipTitle = item.weight !== null
                ? `Bobot Pengaruh: ${item.weight > 0 ? "+" : ""}${item.weight.toFixed(4)}`
                : "Bobot Pengaruh: Tidak tersedia";

            return (
                <span
                    key={idx}
                    className={badgeStyle}
                    title={tooltipTitle}
                >
                    {item.word}{" "}
                </span>
            );
        });
    }, [text, tokenMap, validTokens]);

    // Ekstraksi kata pendorong hoaks (hanya yang memiliki bobot numerik valid > 0)
    const computedTopHoax = useMemo(() => {
        if (Array.isArray(topHoax) && topHoax.length > 0) {
            const sanitized = topHoax
                .filter((w) => w && typeof w === "object")
                .map((w) => ({ word: String(w.word || "").trim(), score: parseWeightStrict(w.score) }))
                .filter((w): w is { word: string; score: number } => w.word !== "" && w.score !== null && w.score > 0)
                .sort((a, b) => b.score - a.score);
            if (sanitized.length > 0) return sanitized.slice(0, wordLimit);
        }
        // Fallback: hitung dari validTokens jika prop kosong
        return validTokens
            .filter((t): t is { word: string; weight: number; influence: "hoax" | "fact" | "neutral" } => t.weight !== null && t.weight > 0)
            .sort((a, b) => b.weight - a.weight)
            .slice(0, wordLimit)
            .map((t) => ({ word: t.word, score: t.weight }));
    }, [validTokens, topHoax, wordLimit]);

    // Ekstraksi kata penurun skor hoaks (hanya yang memiliki bobot numerik valid < 0)
    const computedTopFact = useMemo(() => {
        if (Array.isArray(topFact) && topFact.length > 0) {
            const sanitized = topFact
                .filter((w) => w && typeof w === "object")
                .map((w) => {
                    const parsed = parseWeightStrict(w.score);
                    return { word: String(w.word || "").trim(), score: parsed !== null ? Math.abs(parsed) : null };
                })
                .filter((w): w is { word: string; score: number } => w.word !== "" && w.score !== null && w.score > 0)
                .sort((a, b) => b.score - a.score);
            if (sanitized.length > 0) return sanitized.slice(0, wordLimit);
        }
        return validTokens
            .filter((t): t is { word: string; weight: number; influence: "hoax" | "fact" | "neutral" } => t.weight !== null && t.weight < 0)
            .sort((a, b) => a.weight - b.weight)
            .slice(0, wordLimit)
            .map((t) => ({ word: t.word, score: Math.abs(t.weight) }));
    }, [validTokens, topFact, wordLimit]);

    // ── SKALA MAKSIMUM ABSOLUT BERSAMA ──
    const globalMaxAbsScore = useMemo(() => {
        const maxH = computedTopHoax.length > 0 ? Math.max(...computedTopHoax.map((w) => w.score)) : 0;
        const maxF = computedTopFact.length > 0 ? Math.max(...computedTopFact.map((w) => w.score)) : 0;
        return Math.max(maxH, maxF, 0.0001);
    }, [computedTopHoax, computedTopFact]);

    // ── 2. EARLY RETURN JIKA TOKEN KOSONG ──
    if (validTokens.length === 0) {
        return (
            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200/60 text-xs text-slate-400 italic">
                Data penjelasan lokal LIME belum tersedia untuk sampel ini.
            </div>
        );
    }

    const label = prediction?.trim().toUpperCase() ?? "";
    const isAmbiguous = /AMBIGU|VERIFIKASI|KONFIRMASI/.test(label);
    const isHoax = ["BERPOLA HOAKS", "HOAKS", "HOAX"].includes(label);
    const isNonHoax = ["TIDAK BERPOLA HOAKS", "FAKTA", "FACT"].includes(label);
    const decision = isAmbiguous ? "PERLU VERIFIKASI"
        : isHoax ? "BERPOLA HOAKS"
        : isNonHoax ? "TIDAK BERPOLA HOAKS"
        : null;
    const hasSamples = typeof numSamples === "number" && Number.isInteger(numSamples) && numSamples > 0;
    const directions = [
        {
            name: "Menaikkan skor hoaks",
            emptyText: "Tidak ada bobot positif pada ringkasan ini.",
            sign: "+",
            items: computedTopHoax,
            tile: "border-rose-100 bg-rose-50/65",
            accent: "bg-rose-100 text-rose-800",
            fill: "bg-rose-500",
        },
        {
            name: "Menurunkan skor hoaks",
            emptyText: "Tidak ada bobot negatif pada ringkasan ini.",
            sign: "-",
            items: computedTopFact,
            tile: "border-emerald-100 bg-emerald-50/65",
            accent: "bg-emerald-100 text-emerald-800",
            fill: "bg-emerald-600",
        },
    ];

    return (
        <div className="space-y-4">
            <section className="min-w-0 space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <header className="flex flex-wrap items-baseline justify-between gap-2">
                    <h4 className="text-sm font-semibold text-slate-900">Sorotan kata</h4>
                    {hasSamples && (
                        <span className="rounded-full bg-white px-2.5 py-1 text-xs text-slate-600 ring-1 ring-slate-200">
                            {numSamples} variasi teks diuji
                        </span>
                    )}
                </header>

                <div className="max-h-48 overflow-y-auto whitespace-pre-wrap rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm leading-7 text-slate-800 [overflow-wrap:anywhere]">
                    {displayTextTokens}
                </div>

                <div className="flex flex-wrap gap-2 text-xs font-medium">
                    <span className="rounded-lg border border-rose-200 bg-rose-50 px-2.5 py-1 text-rose-800">
                        Merah (+) menaikkan skor hoaks
                    </span>
                    <span className="rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-emerald-800">
                        Hijau (−) menurunkan skor hoaks
                    </span>
                </div>
                {hasUnavailableWeights && (
                    <p className="text-xs text-amber-800">Beberapa kata tidak memiliki atribusi bobot valid.</p>
                )}
            </section>

            <section className="flex min-w-0 items-start gap-3 rounded-2xl bg-gradient-to-br from-slate-950 to-emerald-950 p-4 text-white">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-emerald-300/25 bg-emerald-400/10 text-emerald-200">
                    <AIAnalysisIcon className="h-7 w-7" />
                </span>
                <div className="min-w-0 space-y-2">
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
                        <h4 className="text-sm font-semibold">Mekanisme keputusan model</h4>
                        {decision && (
                            <span className="rounded-md bg-white/10 px-2 py-1 text-[11px] font-semibold text-emerald-100">
                                {decision}
                            </span>
                        )}
                    </div>
                    <p className="text-xs leading-relaxed text-slate-200">
                        {isAmbiguous ? "Seed model menghasilkan keputusan berbeda. Hasil ini perlu diverifikasi."
                            : decision ? "Keputusan model mengikuti voting antar-seed."
                            : "Label keputusan tidak tersedia."}{" "}
                        LIME memperkirakan pengaruh lokal kata dengan menguji variasi dari teks ini.
                    </p>
                </div>
            </section>

            <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4">
                <header>
                    <h4 className="text-sm font-semibold text-slate-900">Bobot kata paling berpengaruh</h4>
                    {showChart && (computedTopHoax.length > 0 || computedTopFact.length > 0) && (
                        <p className="mt-1 text-xs leading-relaxed text-slate-600">
                            Panjang batang menunjukkan besar pengaruh relatif. Kedua arah memakai skala yang sama.
                        </p>
                    )}
                </header>
                <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,12rem),1fr))] gap-2.5">
                    {directions.map(direction => (
                        <div key={direction.sign} className={"min-w-0 space-y-2.5 rounded-xl border p-3 " + direction.tile}>
                            <h5 className="flex items-center gap-2 text-xs font-semibold text-slate-900">
                                <span className={"grid h-5 w-5 shrink-0 place-items-center rounded-md text-sm " + direction.accent} aria-hidden="true">
                                    {direction.sign === "-" ? "−" : "+"}
                                </span>
                                {direction.name}
                            </h5>
                            {direction.items.length > 0 ? (
                                <ul className="space-y-2.5">
                                    {direction.items.map((item, index) => (
                                        <li key={index} className="space-y-1">
                                            <div className="flex items-baseline justify-between gap-2 text-xs">
                                                <span className="min-w-0 font-medium text-slate-800 [overflow-wrap:anywhere]">{item.word}</span>
                                                <span className={"shrink-0 rounded px-1.5 py-0.5 font-mono font-semibold tabular-nums " + direction.accent}>
                                                    {direction.sign}{item.score.toFixed(4)}
                                                </span>
                                            </div>
                                            {showChart && (
                                                <div className="h-1.5 overflow-hidden rounded-full bg-white" aria-hidden="true">
                                                    <div
                                                        className={"h-full rounded-full " + direction.fill}
                                                        style={{ width: (item.score / globalMaxAbsScore) * 100 + "%" }}
                                                    />
                                                </div>
                                            )}
                                        </li>
                                    ))}
                                </ul>
                            ) : (
                                <p className="text-xs leading-relaxed text-slate-600">{direction.emptyText}</p>
                            )}
                        </div>
                    ))}
                </div>
            </section>
        </div>
    );
}
