"use client";

import { useEffect, useRef, useState } from "react";
import { apiClient } from "@/lib/apiClient";
import { DEFAULT_SETTINGS, SETTINGS_KEY, readUserSettings } from "@/lib/userSettings";
import {
    CheckCircle,
    AlertTriangle,
    XCircle,
    Download,
    HelpCircle,
    Clock,
    ShieldAlert,
    Scissors
} from "lucide-react";
import { DetectionResult } from "@/types/detector";
import LimeHighlighter from "./LimeHighlighter";
import DisclaimerBanner from "./DisclaimerBanner";
import AIAnalysisIcon from "@/components/shared/AIAnalysisIcon";
import FeedbackModal from "./FeedbackModal";

interface VerdictCardProps {
    result: DetectionResult | null;
    loading: boolean;
    canAct?: boolean;
    onRequestExplanation?: () => void;
    limeLoading?: boolean;
    limeError?: string | null;
    onFeedbackSubmitted?: () => void | Promise<void>;
}

// Kelas bersama agar semua kondisi panel hasil seragam dengan panel input
const panelClass =
    "flex min-w-0 flex-col overflow-hidden rounded-3xl border border-emerald-200/70 bg-[#f1f8f4] shadow-[0_12px_36px_rgba(6,78,59,0.07)]";

function PanelHeader({ subtitle }: { subtitle: string }) {
    return (
        <header className="flex items-center gap-3 bg-gradient-to-r from-emerald-950 to-emerald-800 px-5 py-4 text-white sm:px-6">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-white text-emerald-800 shadow-sm">
                <AIAnalysisIcon className="h-7 w-7" />
            </span>
            <div className="min-w-0">
                <h2 className="text-base font-semibold tracking-tight">Hasil analisis</h2>
                <p className="mt-0.5 text-xs text-emerald-200">{subtitle}</p>
            </div>
        </header>
    );
}

export default function VerdictCard({
    result,
    loading,
    canAct = true,
    onRequestExplanation,
    limeLoading = false,
    limeError = null,
    onFeedbackSubmitted,
}: VerdictCardProps) {
    const [feedbackForId, setFeedbackForId] = useState<string | null>(null);
    const [feedbackSuccess, setFeedbackSuccess] = useState<string | null>(null);
    const [showLime, setShowLime] = useState(true);
    const [showAnalyzedText, setShowAnalyzedText] = useState(false);
    const [viewSettings, setViewSettings] = useState({ ...DEFAULT_SETTINGS });

    // Pengaman window untuk menghindari kegagalan pada lingkungan test runner
    useEffect(() => {
        if (typeof window === "undefined") return;
        const sync = () => setViewSettings(readUserSettings());
        const onStorage = (e: StorageEvent) => { if (e.key === SETTINGS_KEY || e.key === null) sync(); };
        sync();
        window.addEventListener("storage", onStorage);
        window.addEventListener("veridix:settings-changed", sync);
        return () => {
            window.removeEventListener("storage", onStorage);
            window.removeEventListener("veridix:settings-changed", sync);
        };
    }, []);

    const feedbackId = result?.data?.id;
    const feedbackStatus = (result?.data?.process_status || (result?.data?.prediction ? "dinilai" : "ditolak")).toLowerCase();
    const feedbackTarget = !loading && canAct && typeof feedbackId === "string" && feedbackId.trim() &&
        (feedbackStatus === "dinilai" || feedbackStatus === "ambigu") ? feedbackId : null;
    const feedbackTargetRef = useRef<string | null>(feedbackTarget);

    useEffect(() => {
        feedbackTargetRef.current = feedbackTarget;
        setFeedbackForId(null);
        return () => { feedbackTargetRef.current = null; };
    }, [feedbackTarget]);

    useEffect(() => { setFeedbackSuccess(null); }, [feedbackId]);

    // 1. Kondisi Sedang Memproses
    if (loading) {
        return (
            <section className={`${panelClass} min-h-[460px]`}>
                <PanelHeader subtitle="Sedang memproses naskah" />
                <div
                    role="status"
                    aria-live="polite"
                    className="relative flex flex-1 flex-col items-center justify-center overflow-hidden px-6 py-10 text-center"
                >
                    {/* Keyframe lokal untuk animasi analisis */}
                    <style>{`
                        @keyframes vx-main-scan { 0% { top: -12%; opacity: 0; } 15% { opacity: 1; } 85% { opacity: 1; } 100% { top: 100%; opacity: 0; } }
                        @keyframes vx-main-glow { 0%, 100% { opacity: .35; transform: scale(1); } 50% { opacity: .75; transform: scale(1.1); } }
                        @keyframes vx-main-line { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }
                        @keyframes vx-main-dot { 0%, 80%, 100% { opacity: .25; transform: translateY(0); } 40% { opacity: 1; transform: translateY(-3px); } }
                        @media (prefers-reduced-motion: reduce) {
                            .vx-main-anim { animation: none !important; }
                        }
                    `}</style>

                    {/* Cahaya latar yang berdenyut di belakang logo */}
                    <span
                        aria-hidden="true"
                        className="vx-main-anim pointer-events-none absolute left-1/2 top-[34%] h-48 w-48 -translate-x-1/2 -translate-y-1/2 rounded-full bg-emerald-400/25 blur-3xl"
                        style={{ animation: "vx-main-glow 2.6s ease-in-out infinite" }}
                    />

                    {/* Logo otak dalam tile persegi dengan garis pemindai */}
                    <div
                        aria-hidden="true"
                        className="relative mb-7 flex h-24 w-24 items-center justify-center overflow-hidden rounded-3xl bg-gradient-to-br from-emerald-950 to-emerald-800 text-emerald-100 shadow-xl shadow-emerald-900/25 ring-1 ring-emerald-300/30"
                    >
                        <AIAnalysisIcon className="h-14 w-14" />
                        <span
                            className="vx-main-anim absolute inset-x-0 h-10 bg-gradient-to-b from-transparent via-emerald-300/55 to-transparent"
                            style={{ animation: "vx-main-scan 1.9s ease-in-out infinite" }}
                        />
                        <span className="absolute left-2 top-2 h-3 w-3 rounded-tl-lg border-l-2 border-t-2 border-emerald-300/80" />
                        <span className="absolute right-2 top-2 h-3 w-3 rounded-tr-lg border-r-2 border-t-2 border-emerald-300/80" />
                        <span className="absolute bottom-2 left-2 h-3 w-3 rounded-bl-lg border-b-2 border-l-2 border-emerald-300/80" />
                        <span className="absolute bottom-2 right-2 h-3 w-3 rounded-br-lg border-b-2 border-r-2 border-emerald-300/80" />
                    </div>

                    <h3 className="relative flex items-center gap-2 text-lg font-semibold tracking-tight text-emerald-950">
                        Naskah Anda sedang diproses
                        <span aria-hidden="true" className="flex items-center gap-1">
                            {[0, 1, 2].map((i) => (
                                <span
                                    key={i}
                                    className="vx-main-anim h-1.5 w-1.5 rounded-full bg-emerald-600"
                                    style={{ animation: `vx-main-dot 1.2s ease-in-out ${i * 0.15}s infinite` }}
                                />
                            ))}
                        </span>
                    </h3>

                    <p className="relative mt-2 max-w-xs text-sm leading-relaxed text-slate-600">
                        Hasil analisis akan tampil setelah pemrosesan selesai.
                    </p>

                    {/* Garis teks yang sedang dibaca model (indeterminate, bukan persentase) */}
                    <div aria-hidden="true" className="relative mt-7 w-full max-w-xs space-y-2.5">
                        {["w-full", "w-11/12", "w-4/5", "w-3/5"].map((w, i) => (
                            <span
                                key={i}
                                className={`relative block h-2.5 overflow-hidden rounded-full bg-emerald-200/60 ${w}`}
                            >
                                <span
                                    className="vx-main-anim absolute inset-0 bg-gradient-to-r from-transparent via-emerald-500/50 to-transparent"
                                    style={{ animation: `vx-main-line 1.7s ease-in-out ${i * 0.15}s infinite` }}
                                />
                            </span>
                        ))}
                    </div>
                </div>
            </section>
        );
    }

    // 2. Kondisi Belum Ada Masukan
    if (!result || !result.data) {
        return (
            <section className={`${panelClass} min-h-[420px]`}>
                <PanelHeader subtitle="Pola bahasa dan penjelasan model" />

                <div className="flex flex-1 flex-col items-center justify-center px-6 py-10 text-center">
                    <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-200 bg-white text-emerald-700 shadow-sm">
                        <AIAnalysisIcon className="h-9 w-9" />
                    </span>
                    <h3 className="text-xl font-semibold text-emerald-950">
                        Hasil akan muncul di sini
                    </h3>
                    <p className="mt-3 max-w-sm text-sm leading-relaxed text-slate-600">
                        Tambahkan berita melalui panel input. Untuk gambar,
                        periksa teks hasil OCR sebelum memilih Analisis Sekarang.
                    </p>
                </div>

                <footer className="border-t border-emerald-200/70 bg-white/60 px-6 py-4 text-xs leading-relaxed text-slate-600">
                    Hasil menunjukkan kemiripan pola bahasa, bukan pembuktian
                    kebenaran berita.
                </footer>
            </section>
        );
    }

    // ── 3. EKSTRAKSI KONTRAK DATA RESMI BACKEND ──────────────────────────────
    const d = result.data as any;

    const processStatus: string = (
        d.process_status ||
        d.status ||
        (d.prediction ? "dinilai" : "ditolak")
    ).toLowerCase();

    const rawLabel: string = (
        d.pattern_label ||
        d.label ||
        d.prediction ||
        ""
    ).trim().toUpperCase();

    // ── 4. PEMETAAN LABEL EKSPLISIT ──────────────────────────────────────────
    const isHoax = rawLabel === "BERPOLA HOAKS" || rawLabel === "HOAKS" || rawLabel === "HOAX";
    const isNonHoax = rawLabel === "TIDAK BERPOLA HOAKS" || rawLabel === "FAKTA" || rawLabel === "FACT";
    const isAmbiguous = processStatus === "ambigu" || rawLabel.includes("PERLU VERIFIKASI") || rawLabel === "PERLU KONFIRMASI";
    const isOutOfDomain = processStatus === "di_luar_domain" || rawLabel.includes("DI LUAR CAKUPAN");
    const isRejected = processStatus === "ditolak" || rawLabel === "TIDAK DAPAT DINILAI";

    const modelAssessed = processStatus === "dinilai" || processStatus === "ambigu";
    const isTruncated = d.terpotong === true;
    const truncationUnknown = modelAssessed && typeof d.terpotong !== "boolean";
    const hasAnalyzedText = typeof d.teks_dinilai === "string" && d.teks_dinilai.trim() !== "";
    const displaySnippet = hasAnalyzedText ? d.teks_dinilai : "";


    const topic = d.sub_topik || d.political_topic || "";
    const votesHoax = d.votes_hoax || "";

    let consensusLabel: string | null = null;
    if (
        modelAssessed &&
        typeof d.agreement_ratio === "number" &&
        Number.isFinite(d.agreement_ratio) &&
        d.agreement_ratio >= 0 &&
        d.agreement_ratio <= 1
    ) {
        const decisions: unknown[] = d.seed_decisions && typeof d.seed_decisions === "object" &&
            !Array.isArray(d.seed_decisions) ? Object.values(d.seed_decisions) : [];
        if (decisions.length > 0 && decisions.every(value => value === 0 || value === 1)) {
            const hoaxVotes = decisions.filter(value => value === 1).length;
            const agreeingVotes = Math.max(hoaxVotes, decisions.length - hoaxVotes);
            consensusLabel = Math.abs(agreeingVotes / decisions.length - d.agreement_ratio) < 1e-6
                ? `Kesepakatan seed: ${agreeingVotes}/${decisions.length}`
                : "Kesepakatan seed: data tidak konsisten";
        } else {
            consensusLabel = `Kesepakatan seed: ${(d.agreement_ratio * 100).toFixed(1)}%`;
        }
    }

    const latencyStr = d.latency_seconds !== undefined
        ? `${d.latency_seconds}s`
        : (d.inference_time_seconds !== undefined ? `${d.inference_time_seconds}s` : "-");

    // ── 5. PENENTUAN TEMA KARTU ──────────────────────────────────────────────
    let theme = {
        bg: "bg-slate-50 border-slate-200 text-slate-800",
        badge: "bg-slate-600 text-white",
        icon: AlertTriangle,
        label: rawLabel || "TIDAK DAPAT DINILAI",
        badgeText: "Ditolak"
    };

    if (processStatus === "dinilai") {
        if (isHoax) {
            theme = {
                bg: "bg-rose-50 border-rose-200/80 text-rose-900",
                badge: "bg-rose-600 text-white",
                icon: XCircle,
                label: "BERPOLA HOAKS",
                badgeText: votesHoax ? `Suara hoaks: ${votesHoax}` : "Terindikasi"
            };
        } else if (isNonHoax) {
            theme = {
                bg: "bg-emerald-50 border-emerald-200/80 text-emerald-900",
                badge: "bg-emerald-600 text-white",
                icon: CheckCircle,
                label: "TIDAK BERPOLA HOAKS",
                badgeText: votesHoax ? `Suara hoaks: ${votesHoax}` : "Terindikasi"
            };
        } else {
            theme = {
                bg: "bg-slate-100 border-slate-300 text-slate-800",
                badge: "bg-slate-500 text-white",
                icon: HelpCircle,
                label: rawLabel || "STATUS TIDAK DIKENAL",
                badgeText: "Perlu Verifikasi"
            };
        }
    } else if (isAmbiguous) {
        theme = {
            bg: "bg-amber-50 border-amber-200/80 text-amber-900",
            badge: "bg-amber-600 text-white",
            icon: AlertTriangle,
            label: "PERLU VERIFIKASI",
            badgeText: votesHoax ? `Suara hoaks: ${votesHoax}` : "Ambigu"
        };
    } else if (isOutOfDomain) {
        theme = {
            bg: "bg-blue-50 border-blue-200/80 text-blue-900",
            badge: "bg-blue-600 text-white",
            icon: ShieldAlert,
            label: "DI LUAR CAKUPAN POLITIK",
            badgeText: "Non-Politik"
        };
    } else if (isRejected) {
        theme = {
            bg: "bg-slate-100 border-slate-300 text-slate-800",
            badge: "bg-slate-500 text-white",
            icon: AlertTriangle,
            label: "TIDAK DAPAT DINILAI",
            badgeText: "Input Ditolak"
        };
    }

    const IconVerdict = theme.icon;

    const canExplain = Boolean(d.id) && (processStatus === "dinilai" || processStatus === "ambigu");
    const canFeedback = Boolean(feedbackTarget) && (isHoax || isNonHoax || isAmbiguous);

    // ── 6. NARASI KETERANGAN SISTEM ──────────────────────────────────────────
    let narrative = d.narrative_text || d.narrative_explanation || d.reason;
    if (!narrative) {
        if (isRejected) {
            narrative = "Teks tidak memenuhi syarat kelayakan analisis sistem (kosong, kurang dari 10 kata, atau didominasi simbol).";
        } else if (isOutOfDomain) {
            narrative = "Teks berada di luar domain isu politik Indonesia yang digunakan untuk melatih sistem.";
        } else if (isAmbiguous) {
            narrative = `Model mendeteksi divergensi antar-seed (${votesHoax ? `suara hoaks: ${votesHoax}` : 'suara tidak bulat'}). Teks memerlukan verifikasi manual.`;
        } else if (isHoax) {
            narrative = "Teks teridentifikasi memiliki kemiripan karakteristik linguistik dengan pola klaim disinformasi historis pada korpus latih.";
        } else if (isNonHoax) {
            narrative = "Teks menunjukkan karakteristik yang konsisten dengan struktur penulisan berita faktual pada korpus latih.";
        } else {
            narrative = "Hasil evaluasi tidak dapat disimpulkan secara otomatis.";
        }
    }

    const rawTokensList = Array.isArray(d.explanation?.tokens) ? d.explanation.tokens : [];
    const limeAvailable = d.explanation?.explanation_available === true &&
        rawTokensList.some((t: any) => t && typeof t === "object" && typeof t.word === "string");

    const limeTokens = limeAvailable
        ? rawTokensList.filter((t: any) => t && typeof t === "object" && typeof t.word === "string")
        : [];

    const limePredictionLabel = isHoax
        ? "HOAKS"
        : isAmbiguous
            ? "AMBIGU"
            : isNonHoax
                ? "FAKTA"
                : "NETRAL";

    return (
        <section className={panelClass}>
            <PanelHeader subtitle="Pola bahasa dan penjelasan model" />

            <div className="space-y-5 p-5 sm:p-6">

                {/* LAPIS 1: KEPUTUSAN MODEL & KONSENSUS SUARA */}
                <div className={`flex flex-wrap items-center justify-between gap-3 rounded-2xl border p-4 shadow-sm ${theme.bg}`}>
                    <div className="flex min-w-0 items-center gap-3">
                        <div className="rounded-xl bg-white/90 p-2 shadow-xs">
                            <IconVerdict className="h-6 w-6" />
                        </div>
                        <div className="min-w-0">
                            <span className="block text-[11px] font-semibold opacity-70">
                                Keputusan model {topic ? `• Topik: ${topic}` : ""}
                            </span>
                            <h3 className="text-xl font-black leading-tight tracking-tight">
                                {theme.label}
                            </h3>
                        </div>
                    </div>

                    <div className="shrink-0 text-right">
                        <span className={`inline-block whitespace-nowrap rounded-full px-3 py-1 text-xs font-bold ${theme.badge}`}>
                            {theme.badgeText}
                        </span>
                        {consensusLabel && (
                            <p
                                className="mt-1 text-[11px] font-semibold opacity-85"
                                title="Menunjukkan konsensus antar-seed model, bukan akurasi atau probabilitas kebenaran berita."
                            >
                                {consensusLabel}
                            </p>
                        )}
                        <p className="mt-1 flex items-center justify-end gap-1 font-mono text-[10px] opacity-70">
                            <Clock className="h-3 w-3" /> {latencyStr}
                        </p>
                    </div>
                </div>

                {/* Peringatan Pemotongan Teks Transparan */}
                {(isTruncated || truncationUnknown) && (
                    <div className="space-y-2 rounded-2xl border border-amber-300/80 bg-amber-50 p-4">
                        <div className="flex items-start gap-2.5">
                            <Scissors className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                            <div className="flex-1">
                                <div className="flex items-center justify-between gap-2">
                                    <h4 className="text-xs font-bold text-amber-900">
                                        {isTruncated
                                            ? "Naskah berita terpotong untuk analisis"
                                            : "Status pemotongan belum diketahui"}
                                    </h4>
                                    {hasAnalyzedText && (
                                        <button
                                            type="button"
                                            onClick={() => setShowAnalyzedText(!showAnalyzedText)}
                                            className="shrink-0 cursor-pointer text-[11px] font-semibold text-amber-800 underline hover:text-amber-950"
                                        >
                                            {showAnalyzedText ? "Tutup naskah" : "Lihat teks praproses"}
                                        </button>
                                    )}
                                </div>
                                <p className="mt-1 text-[11px] leading-relaxed text-amber-900/90">
                                    {isTruncated
                                        ? "Sebagian naskah dipotong pada praproses atau tokenisasi."
                                        : "Metadata belum cukup untuk memastikan apakah seluruh naskah masuk model."}
                                    {hasAnalyzedText
                                        ? " Teks praproses berada sebelum batas tokenizer, sehingga belum tentu seluruhnya masuk model."
                                        : " Teks hasil praproses tidak tersedia untuk hasil ini."}
                                </p>
                            </div>
                        </div>

                        {showAnalyzedText && hasAnalyzedText && (
                            <div className="mt-2 border-t border-amber-200/60 pt-2">
                                <span className="mb-1 block text-[11px] font-bold text-amber-800">
                                    Teks hasil praproses sebelum batas tokenizer:
                                </span>
                                <div className="max-h-32 overflow-y-auto whitespace-pre-wrap rounded-xl border border-amber-200/60 bg-white p-3 font-mono text-[11px] leading-relaxed text-slate-700">
                                    {displaySnippet}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* LAPIS 2: KETERANGAN EVALUASI SISTEM */}
                <div className="rounded-2xl border border-emerald-200/60 bg-white p-4 shadow-sm">
                    <p className="mb-1 text-[11px] font-bold text-emerald-800">
                        Penjelasan hasil
                    </p>
                    <p className="font-sans text-sm leading-relaxed text-slate-700">
                        {narrative}
                    </p>
                </div>

                {/* LAPIS 3: PENJELASAN BOBOT KATA (LIME, SESUAI PERMINTAAN) */}
                {limeAvailable ? (
                    <div className="rounded-2xl border border-emerald-200/60 bg-white p-4 shadow-sm">
                        <button
                            type="button"
                            onClick={() => setShowLime((v) => !v)}
                            className="mb-2 flex w-full items-center justify-between text-left"
                            aria-expanded={showLime}
                        >
                            <span className="text-xs font-bold text-emerald-900">
                                Kata yang memengaruhi hasil
                            </span>
                            <span className="rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700">
                                {showLime ? "Sembunyikan" : "Tampilkan"}
                            </span>
                        </button>
                        {showLime && (
                            <LimeHighlighter
                                tokens={limeTokens}
                                text={d.explanation?.teks_dijelaskan || d.teks_dinilai || undefined}
                                topHoax={d.explanation?.top_hoax_words}
                                topFact={d.explanation?.top_fact_words}
                                showChart={viewSettings.show_lime_chart}
                                topWordsCount={viewSettings.lime_top_words ?? 3}
                                prediction={limePredictionLabel}
                                numSamples={
                                    Number.isInteger(d.explanation?.num_samples) && d.explanation.num_samples > 0
                                        ? d.explanation.num_samples
                                        : undefined
                                }
                                confidenceScore={
                                    typeof d.confidence_score === "number" && Number.isFinite(d.confidence_score)
                                        ? d.confidence_score
                                        : undefined
                                }
                            />
                        )}
                    </div>
                ) : (
                    <div className="space-y-3 rounded-2xl border border-dashed border-emerald-300/80 bg-white/70 p-4">
                        {limeLoading ? (
                            <div
                                role="status"
                                aria-live="polite"
                                className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-emerald-950 via-emerald-900 to-emerald-800 p-4 text-left shadow-lg shadow-emerald-950/15"
                            >
                                {/* Keyframe lokal untuk animasi analisis */}
                                <style>{`
                                    @keyframes vx-scan { 0% { top: -10%; opacity: 0; } 15% { opacity: 1; } 85% { opacity: 1; } 100% { top: 100%; opacity: 0; } }
                                    @keyframes vx-glow { 0%, 100% { opacity: .35; transform: scale(1); } 50% { opacity: .8; transform: scale(1.12); } }
                                    @keyframes vx-shimmer { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }
                                    @keyframes vx-dot { 0%, 80%, 100% { opacity: .25; transform: translateY(0); } 40% { opacity: 1; transform: translateY(-3px); } }
                                    @media (prefers-reduced-motion: reduce) {
                                        .vx-anim, .vx-anim::after { animation: none !important; }
                                    }
                                `}</style>

                                {/* Cahaya latar yang berdenyut */}
                                <span
                                    aria-hidden="true"
                                    className="vx-anim pointer-events-none absolute -left-6 -top-6 h-32 w-32 rounded-full bg-emerald-400/30 blur-2xl"
                                    style={{ animation: "vx-glow 2.4s ease-in-out infinite" }}
                                />

                                <div className="relative flex items-center gap-4">
                                    {/* Logo otak tanpa lingkaran: tile persegi dengan garis pemindai */}
                                    <span
                                        aria-hidden="true"
                                        className="relative flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-white/10 text-emerald-100 ring-1 ring-emerald-300/30 backdrop-blur-sm"
                                    >
                                        <AIAnalysisIcon className="h-9 w-9" />
                                        <span
                                            className="vx-anim absolute inset-x-0 h-6 bg-gradient-to-b from-transparent via-emerald-300/50 to-transparent"
                                            style={{ animation: "vx-scan 1.8s ease-in-out infinite" }}
                                        />
                                        <span className="absolute left-1.5 top-1.5 h-2 w-2 rounded-tl-md border-l-2 border-t-2 border-emerald-300/80" />
                                        <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-tr-md border-r-2 border-t-2 border-emerald-300/80" />
                                        <span className="absolute bottom-1.5 left-1.5 h-2 w-2 rounded-bl-md border-b-2 border-l-2 border-emerald-300/80" />
                                        <span className="absolute bottom-1.5 right-1.5 h-2 w-2 rounded-br-md border-b-2 border-r-2 border-emerald-300/80" />
                                    </span>

                                    <div className="min-w-0 flex-1">
                                        <p className="flex items-center gap-2 text-sm font-semibold text-white">
                                            AI sedang menyusun penjelasan
                                            <span aria-hidden="true" className="flex items-center gap-1">
                                                {[0, 1, 2].map((i) => (
                                                    <span
                                                        key={i}
                                                        className="vx-anim h-1.5 w-1.5 rounded-full bg-emerald-300"
                                                        style={{ animation: `vx-dot 1.2s ease-in-out ${i * 0.15}s infinite` }}
                                                    />
                                                ))}
                                            </span>
                                        </p>
                                        <p className="mt-1 text-[11px] leading-relaxed text-emerald-100/80">
                                            Menghitung pengaruh kata terhadap hasil model. Waktu proses dapat bervariasi.
                                        </p>
                                    </div>
                                </div>

                                {/* Placeholder kata yang sedang dianalisis (indeterminate, bukan persentase) */}
                                <div aria-hidden="true" className="relative mt-4 flex flex-wrap gap-2">
                                    {["w-14", "w-20", "w-12", "w-24", "w-16", "w-10"].map((w, i) => (
                                        <span
                                            key={i}
                                            className={`relative h-5 overflow-hidden rounded-md bg-white/10 ${w}`}
                                        >
                                            <span
                                                className="vx-anim absolute inset-0 bg-gradient-to-r from-transparent via-emerald-300/40 to-transparent"
                                                style={{ animation: `vx-shimmer 1.6s ease-in-out ${i * 0.12}s infinite` }}
                                            />
                                        </span>
                                    ))}
                                </div>
                            </div>
                        ) : (
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                <div className="min-w-0">
                                    <p className="text-xs font-bold text-emerald-900">Kata yang memengaruhi hasil</p>
                                    <p className={`mt-1 text-[11px] leading-relaxed ${limeError || d.explanation?.error ? "font-medium text-rose-700" : "text-slate-600"}`}>
                                        {limeError
                                            ? limeError
                                            : d.explanation?.error
                                                ? `Gagal mengekstrak LIME: ${d.explanation.error}`
                                                : canExplain
                                                    ? "Penjelasan kata (LIME) tidak dihitung otomatis agar hasil klasifikasi tampil lebih cepat."
                                                    : "Atribusi LIME tidak tersedia untuk status ini."}
                                    </p>
                                </div>
                                {canExplain && onRequestExplanation && (
                                    <button
                                        type="button"
                                        onClick={onRequestExplanation}
                                        disabled={!canAct}
                                        className="shrink-0 rounded-xl bg-emerald-800 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-emerald-900 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-emerald-500/25 disabled:opacity-40"
                                    >
                                        {limeError ? "Coba lagi" : "Tampilkan penjelasan"}
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {/* LAPIS 4: PENAFIAN (DISCLAIMER) MANDATORI */}
                <DisclaimerBanner />

                {/* FOOTER TOMBOL AKSI */}
                {feedbackSuccess === feedbackId && feedbackId && canAct && (
                    <p role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-800">
                        Terima kasih! Umpan balik Anda telah dikirim.
                    </p>
                )}
                <div className="flex items-center justify-between border-t border-emerald-200/60 pt-4">
                    <div className="flex items-center gap-2">
                        <button
                            type="button"
                            disabled
                            title="Unduh PDF belum tersedia"
                            className="flex items-center gap-1.5 rounded-xl border border-emerald-200 bg-white px-3 py-1.5 text-xs font-semibold text-emerald-800 transition disabled:opacity-40"
                        >
                            <Download className="h-3.5 w-3.5" />
                            <span>Unduh PDF</span>
                        </button>
                    </div>

                    <button
                        type="button"
                        onClick={() => {
                            if (!canFeedback) return;
                            setFeedbackSuccess(null);
                            setFeedbackForId(feedbackTarget);
                        }}
                        disabled={!canFeedback}
                        className="rounded-xl border border-rose-200/70 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 transition hover:bg-rose-100 disabled:opacity-40"
                    >
                        Beri masukan
                    </button>
                </div>

                {/* Modal Umpan Balik */}
                {feedbackTarget && feedbackForId === feedbackTarget && (
                    <FeedbackModal
                        key={feedbackTarget}
                        onClose={() => setFeedbackForId(current => current === feedbackTarget ? null : current)}
                        onSubmit={async (claim, note) => {
                            const targetId = feedbackTarget;
                            if (!canFeedback || feedbackTargetRef.current !== targetId) return;
                            const modelLabel = isAmbiguous ? "PERLU KONFIRMASI"
                                : isHoax ? "BERPOLA HOAKS" : "TIDAK BERPOLA HOAKS";
                            const response = await apiClient.post<{ status: string }>("/api/v1/feedback", {
                                detection_id: targetId,
                                is_agreed: claim === modelLabel,
                                claimed_label: claim,
                                user_notes: note.trim() || null,
                            });
                            if (response.data?.status !== "success") {
                                throw new Error("Pengiriman umpan balik belum dikonfirmasi server.");
                            }
                            if (feedbackTargetRef.current !== targetId) return;
                            setFeedbackForId(current => current === targetId ? null : current);
                            setFeedbackSuccess(targetId);
                            try {
                                await onFeedbackSubmitted?.();
                            } catch {
                                // Feedback sudah tersimpan; kegagalan memuat ulang statistik tidak boleh mengirimnya ulang.
                            }
                        }}
                    />
                )}

            </div>
        </section>
    );
}