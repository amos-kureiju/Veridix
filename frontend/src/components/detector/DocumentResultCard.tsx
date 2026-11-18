"use client";

import { useEffect, useState } from "react";
import { AlertCircle, FileText, LoaderCircle } from "lucide-react";
import DisclaimerBanner from "@/components/detector/DisclaimerBanner";
import LimeHighlighter from "@/components/detector/LimeHighlighter";
import { DEFAULT_SETTINGS, SETTINGS_KEY, readUserSettings } from "@/lib/userSettings";
import type { ExplanationData } from "@/types/detector";
import type { DocumentAnalysisResult, DocumentSegment, DocumentStatus } from "@/types/document-analysis";

const documentStatus: Record<DocumentStatus, { label: string; color: string }> = {
    lengkap: { label: "Cakupan lengkap", color: "bg-emerald-50 text-emerald-800" },
    parsial: { label: "Cakupan sebagian", color: "bg-amber-50 text-amber-800" },
    gagal: { label: "Analisis gagal", color: "bg-rose-50 text-rose-800" },
    ditolak: { label: "Naskah ditolak", color: "bg-slate-100 text-slate-800" },
};

function segmentBadge(segment: DocumentSegment) {
    if (segment.status === "dinilai" && segment.label === "BERPOLA HOAKS") {
        return { label: "BERPOLA HOAKS", color: "bg-rose-50 text-rose-800" };
    }
    if (segment.status === "dinilai" && segment.label === "TIDAK BERPOLA HOAKS") {
        return { label: "TIDAK BERPOLA HOAKS", color: "bg-emerald-50 text-emerald-800" };
    }
    if (segment.status === "ambigu") return { label: "PERLU VERIFIKASI", color: "bg-amber-50 text-amber-800" };
    if (segment.status === "ditolak") return { label: "Ditolak", color: "bg-slate-100 text-slate-800" };
    if (segment.status === "gagal") return { label: "Gagal dinilai", color: "bg-rose-50 text-rose-800" };
    return { label: "Belum dinilai", color: "bg-slate-100 text-slate-800" };
}

interface Props {
    result: DocumentAnalysisResult | null;
    explanations?: Partial<Record<number, ExplanationData>>;
    explanationLoadingFor?: number | null;
    explanationError?: { startChar: number; message: string } | null;
    onRequestExplanation?: (segment: DocumentSegment) => void;
}

interface SegmentExplanationProps {
    segment: DocumentSegment;
    explanation?: ExplanationData;
    loadingFor: number | null;
    error?: Props["explanationError"];
    onRequest?: Props["onRequestExplanation"];
    viewSettings: typeof DEFAULT_SETTINGS;
}

function SegmentExplanation({ segment, explanation, loadingFor, error, onRequest, viewSettings }: SegmentExplanationProps) {
    if (segment.status !== "dinilai" && segment.status !== "ambigu") return null;

    const canRequest = Boolean(segment.explanation_token) && Boolean(onRequest);
    const message = error?.startChar === segment.start_char ? error.message : null;
    const usable = explanation?.explanation_available === true && explanation.teks_dijelaskan === segment.text;
    const numSamples = explanation?.num_samples;

    return (
        <div className="rounded-xl border border-emerald-200/70 bg-white p-3">
            {usable ? (
                <details open>
                    <summary className="mb-3 cursor-pointer text-xs font-semibold text-emerald-900">
                        Kata yang memengaruhi hasil segmen ini (LIME)
                    </summary>
                    <LimeHighlighter
                        text={explanation.teks_dijelaskan}
                        tokens={explanation.tokens}
                        prediction={segment.label ?? undefined}
                        numSamples={typeof numSamples === "number" && Number.isInteger(numSamples) && numSamples > 0
                            ? numSamples : undefined}
                        showChart={viewSettings.show_lime_chart}
                        topWordsCount={viewSettings.lime_top_words}
                    />
                </details>
            ) : loadingFor === segment.start_char ? (
                <div role="status" className="flex items-center gap-3 rounded-xl bg-emerald-900 p-3 text-emerald-50">
                    <LoaderCircle size={20} className="shrink-0 motion-safe:animate-spin" aria-hidden="true" />
                    <div>
                        <p className="text-sm font-semibold">AI sedang menyusun penjelasan</p>
                        <p className="text-xs text-emerald-100">Menghitung pengaruh kata untuk segmen ini.</p>
                    </div>
                </div>
            ) : (
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                        <p className="text-xs font-semibold text-emerald-900">Kata yang memengaruhi hasil</p>
                        {message ? (
                            <p role="alert" className="text-xs text-rose-800">{message}</p>
                        ) : (
                            <p className="text-xs text-slate-600">
                                {canRequest ? "LIME menunjukkan pengaruh kata pada segmen ini."
                                    : "Penjelasan LIME belum tersedia untuk segmen ini."}
                            </p>
                        )}
                    </div>
                    {canRequest && (
                        <button
                            type="button"
                            onClick={() => onRequest?.(segment)}
                            disabled={loadingFor !== null}
                            className="rounded-xl bg-emerald-800 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-900 focus-visible:outline-2 focus-visible:outline-emerald-700 disabled:opacity-40"
                        >
                            {message ? "Coba lagi" : "Tampilkan penjelasan"}
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}

export default function DocumentResultCard({
    result, explanations, explanationLoadingFor = null, explanationError, onRequestExplanation,
}: Props) {
    const [viewSettings, setViewSettings] = useState(DEFAULT_SETTINGS);

    useEffect(() => {
        if (typeof window === "undefined") return;
        const sync = () => setViewSettings(readUserSettings());
        const onStorage = (event: StorageEvent) => {
            if (event.key === SETTINGS_KEY || event.key === null) sync();
        };
        sync();
        window.addEventListener("storage", onStorage);
        window.addEventListener("veridix:settings-changed", sync);
        return () => {
            window.removeEventListener("storage", onStorage);
            window.removeEventListener("veridix:settings-changed", sync);
        };
    }, []);

    if (!result) return null;
    const status = documentStatus[result.status];
    const latency = result.latency_seconds;
    const duration = typeof latency === "number" && Number.isFinite(latency) && latency >= 0
        ? latency.toLocaleString("id-ID", { maximumFractionDigits: 3 }) : null;

    return (
        <section aria-labelledby="document-result-title"
            className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <header className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                    <span className="rounded-xl bg-emerald-50 p-2.5 text-emerald-700" aria-hidden="true">
                        <FileText size={20} />
                    </span>
                    <div>
                        <h2 id="document-result-title" className="text-lg font-semibold text-slate-900">Analisis naskah</h2>
                        {result.sub_topik && <p className="text-xs text-slate-600">Topik {result.sub_topik}</p>}
                    </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${status.color}`}>{status.label}</span>
                    {duration !== null && <p className="text-xs text-slate-600">Waktu analisis {duration} detik</p>}
                </div>
            </header>

                <div className="mt-4 space-y-4">
                    <p role="status" className="text-sm text-slate-700">
                        <strong className="text-slate-900">{result.analyzed_words} dari {result.total_words} kata</strong> pada teks yang dikirim telah dinilai.
                    </p>
                    {result.reason && <p className="text-sm text-slate-700">{result.reason}</p>}
                    {result.missing_pages.length > 0 && (
                        <p className="flex items-start gap-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">
                            <AlertCircle size={17} className="mt-0.5 shrink-0" aria-hidden="true" />
                            <span>Halaman {result.missing_pages.join(", ")} belum memiliki teks yang dikonfirmasi. Jumlah katanya belum diketahui.</span>
                        </p>
                    )}
                    {result.segments.length > 0 && (
                        <ol className="space-y-2">
                            {result.segments.map((segment, index) => {
                                const badge = segmentBadge(segment);
                                const assessed = segment.status === "dinilai" || segment.status === "ambigu";
                                const candidate = explanations?.[segment.start_char];
                                const explanation = assessed && candidate?.explanation_available === true &&
                                    candidate.teks_dijelaskan === segment.text ? candidate : null;
                                const explainable = assessed && Boolean(segment.explanation_token);
                                const busy = explanationLoadingFor === segment.start_char;
                                const error = explanationError?.startChar === segment.start_char ? explanationError.message : null;
                                return (
                                    <li key={segment.start_char}>
                                        <details className="rounded-xl border border-slate-200 bg-slate-50">
                                            <summary className="cursor-pointer rounded-xl p-3 text-sm text-slate-800 focus-visible:outline-2 focus-visible:outline-emerald-600">
                                                <span className="ml-1 inline-flex flex-wrap items-center gap-x-2 gap-y-1">
                                                    <span className="font-semibold">Segmen {index + 1}</span>
                                                    <span className="text-slate-600">Kata {segment.start_word}–{segment.end_word}</span>
                                                    {segment.page_numbers.length > 0 && <span className="text-slate-600">Halaman {segment.page_numbers.join(", ")}</span>}
                                                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${badge.color}`}>{badge.label}</span>
                                                </span>
                                            </summary>
                                            <div className="space-y-2 border-t border-slate-200 p-3 text-sm text-slate-700">
                                                <p className="whitespace-pre-wrap [overflow-wrap:anywhere]">{segment.text}</p>
                                                {segment.votes_hoax && <p className="text-xs text-slate-600">Suara hoaks {segment.votes_hoax}</p>}
                                                {segment.status === "ambigu" && <p>Model antar-seed menghasilkan keputusan yang berbeda.</p>}
                                                {segment.reason && <p>{segment.reason}</p>}
                                                {assessed && (
                                                    <div className="rounded-xl border border-emerald-200/70 bg-white p-3" aria-busy={busy}>
                                                        {explanation ? (
                                                            <details open>
                                                                <summary className="mb-3 cursor-pointer text-xs font-semibold text-emerald-900">
                                                                    Kata yang memengaruhi hasil segmen ini (LIME)
                                                                </summary>
                                                                <LimeHighlighter
                                                                    text={explanation.teks_dijelaskan}
                                                                    tokens={explanation.tokens}
                                                                    topHoax={explanation.top_hoax_words}
                                                                    topFact={explanation.top_fact_words}
                                                                    prediction={segment.label ?? undefined}
                                                                    numSamples={typeof explanation.num_samples === "number" &&
                                                                        Number.isInteger(explanation.num_samples) && explanation.num_samples > 0
                                                                        ? explanation.num_samples : undefined}
                                                                    showChart={viewSettings.show_lime_chart}
                                                                    topWordsCount={viewSettings.lime_top_words}
                                                                />
                                                            </details>
                                                        ) : busy ? (
                                                            <div role="status" className="flex items-center gap-3 rounded-xl bg-emerald-900 p-3 text-emerald-50">
                                                                <LoaderCircle size={20} className="shrink-0 motion-safe:animate-spin" aria-hidden="true" />
                                                                <div>
                                                                    <p className="text-sm font-semibold">AI sedang menyusun penjelasan</p>
                                                                    <p className="text-xs text-emerald-100">Menghitung pengaruh kata untuk segmen ini.</p>
                                                                </div>
                                                            </div>
                                                        ) : (
                                                            <div className="flex flex-wrap items-center justify-between gap-2">
                                                                <div>
                                                                    <p className="text-xs font-semibold text-emerald-900">Kata yang memengaruhi hasil</p>
                                                                    {error ? (
                                                                        <p role="alert" className="text-xs text-rose-800">{error}</p>
                                                                    ) : (
                                                                        <p className="text-xs text-slate-600">
                                                                            {explainable && onRequestExplanation
                                                                                ? "LIME menunjukkan pengaruh kata pada segmen ini."
                                                                                : "Penjelasan LIME belum tersedia untuk segmen ini."}
                                                                        </p>
                                                                    )}
                                                                </div>
                                                                {explainable && onRequestExplanation && (
                                                                    <button
                                                                        type="button"
                                                                        onClick={() => { void onRequestExplanation(segment); }}
                                                                        disabled={explanationLoadingFor !== null}
                                                                        className="rounded-xl bg-emerald-800 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-900 focus-visible:outline-2 focus-visible:outline-emerald-700 disabled:opacity-40"
                                                                    >
                                                                        {error ? "Coba lagi" : "Tampilkan penjelasan"}
                                                                    </button>
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        </details>
                                    </li>
                                );
                            })}
                        </ol>
                    )}
                    <DisclaimerBanner />
                    <p className="text-xs text-slate-600">Hasil analisis naskah tersedia selama halaman terbuka.</p>
                </div>
        </section>
    );
}
