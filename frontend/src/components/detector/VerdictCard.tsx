"use client";

import { useEffect, useRef, useState } from "react";
import { apiClient } from "@/lib/apiClient";
import {
    CheckCircle,
    AlertTriangle,
    XCircle,
    Download,
    HelpCircle,
    Clock,
    Sparkles,
    ShieldAlert
} from "lucide-react";
import { DetectionResult } from "@/types/detector";
import LimeHighlighter from "./LimeHighlighter";
import DisclaimerBanner from "./DisclaimerBanner";
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
            <div className="bg-white border border-slate-200/80 rounded-3xl p-10 shadow-2xs flex flex-col items-center justify-center text-center min-h-[460px]">
                <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center animate-bounce mb-3 border border-emerald-100">
                    <Sparkles className="w-6 h-6" />
                </div>
                <h3 className="text-base font-bold text-slate-800">Memproses Inferensi IndoBERT</h3>
                <p className="text-xs text-slate-400 mt-1 max-w-xs leading-relaxed">
                    Mengevaluasi representasi kontekstual teks melalui konsensus 3 seed model...
                </p>
            </div>
        );
    }

    // 2. Kondisi Belum Ada Masukan
    if (!result || !result.data) {
        return (
            <div className="bg-white border border-slate-200/80 rounded-3xl p-10 shadow-2xs flex flex-col items-center justify-center text-center min-h-[460px]">
                <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mb-3">
                    <HelpCircle className="w-6 h-6" />
                </div>
                <h3 className="text-base font-bold text-slate-700">Hasil Analisis Model</h3>
                <p className="text-xs text-slate-400 mt-1 max-w-sm leading-relaxed">
                    Tempelkan teks berita atau unggah tangkapan layar, lalu tekan tombol "Analisis" untuk melihat hasil evaluasi model.
                </p>
            </div>
        );
    }

    // ── 3. EKSTRAKSI KONTRAK DATA RESMI BACKEND (Prioritas 1) ─────────────────
    const d = result.data as any;

    // Baca status inferensi resmi (process_status dari API atau fallback status)
    const processStatus: string = (
        d.process_status ||
        d.status ||
        (d.prediction ? "dinilai" : "ditolak")
    ).toLowerCase();

    // Baca label pola resmi
    const rawLabel: string = (
        d.pattern_label ||
        d.label ||
        d.prediction ||
        ""
    ).trim().toUpperCase();

    // ── 4. PEMETAAN LABEL EKSPLISIT / EXACT MATCH (Prioritas 2 - Anti Terbalik) ─
    const isHoax = rawLabel === "BERPOLA HOAKS" || rawLabel === "HOAKS" || rawLabel === "HOAX";
    const isNonHoax = rawLabel === "TIDAK BERPOLA HOAKS" || rawLabel === "FAKTA" || rawLabel === "FACT";
    const isAmbiguous = processStatus === "ambigu" || rawLabel.includes("PERLU VERIFIKASI") || rawLabel === "PERLU KONFIRMASI";
    const isOutOfDomain = processStatus === "di_luar_domain" || rawLabel.includes("DI LUAR CAKUPAN");
    const isRejected = processStatus === "ditolak" || rawLabel === "TIDAK DAPAT DINILAI";

    const topic = d.sub_topik || d.political_topic || "";
    const votesHoax = d.votes_hoax || "";

    // Latensi riil (tanpa angka fiktif 0.38s)
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
            // Label tak dikenal -> Tampilkan netral (bukan otomatis Fakta)
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

    // Tombol penjelasan hanya untuk hasil yang punya ID dan berstatus dinilai/ambigu
    // (kepemilikan dan status tetap divalidasi backend: 404/409)
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

    // ── Penanganan Aman: Saring elemen null/rusak sebelum membaca atribut ──
    const rawTokensList = Array.isArray(d.explanation?.tokens) ? d.explanation.tokens : [];
    const limeAvailable = d.explanation?.explanation_available === true &&
        rawTokensList.some((t: any) => t && typeof t === "object" && typeof t.word === "string");

    // Token diteruskan apa adanya; sanitasi hanya dilakukan di LimeHighlighter
    const limeTokens = limeAvailable
        ? rawTokensList.filter((t: any) => t && typeof t === "object" && typeof t.word === "string")
        : [];

    // Kirimkan label 'HOAKS' murni ke LimeHighlighter agar tidak salah deteksi menjadi Fakta
    const limePredictionLabel = isHoax
        ? "HOAKS"
        : isAmbiguous
            ? "AMBIGU"
            : isNonHoax
                ? "FAKTA"
                : "NETRAL";

    return (
        <div className="bg-white border border-slate-200/80 rounded-3xl shadow-2xs p-6 space-y-5">

            {/* LAPIS 1: KEPUTUSAN MODEL & KONSENSUS SUARA */}
            <div className={`border rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3 ${theme.bg}`}>
                <div className="flex items-center gap-3 min-w-0">
                    <div className="p-2 bg-white/90 rounded-xl shadow-xs">
                        <IconVerdict className="w-6 h-6" />
                    </div>
                    <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider opacity-70 block">
                            Hasil analisis {topic ? `• Topik: ${topic}` : ""}
                        </span>
                        <h2 className="text-xl font-black tracking-tight leading-tight">
                            {theme.label}
                        </h2>
                    </div>
                </div>

                <div className="text-right shrink-0">
                    <span className={`inline-block whitespace-nowrap text-xs font-bold px-3 py-1 rounded-full ${theme.badge}`}>
                        {theme.badgeText}
                    </span>
                    <p className="text-[10px] opacity-70 mt-1 flex items-center justify-end gap-1 font-mono">
                        <Clock className="w-3 h-3" /> {latencyStr}
                    </p>
                </div>
            </div>

            {/* LAPIS 2: KETERANGAN EVALUASI SISTEM */}
            <div className="bg-slate-50 border border-slate-200/60 rounded-2xl p-3.5">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                    Keterangan Evaluasi Sistem
                </p>
                <p className="text-xs text-slate-700 leading-relaxed font-sans">
                    {narrative}
                </p>
            </div>

            {/* LAPIS 3: PENJELASAN BOBOT KATA (LIME, SESUAI PERMINTAAN) */}
            {limeAvailable ? (
                <div>
                    <button
                        type="button"
                        onClick={() => setShowLime((v) => !v)}
                        className="w-full flex items-center justify-between text-left mb-2"
                        aria-expanded={showLime}
                    >
                        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                            Kata yang memengaruhi hasil
                        </span>
                        <span className="text-[11px] font-semibold text-emerald-700">
                            {showLime ? "Sembunyikan" : "Tampilkan"}
                        </span>
                    </button>
                    {showLime && (
                        <LimeHighlighter
                            tokens={limeTokens}
                            topHoax={d.explanation?.top_hoax_words}
                            topFact={d.explanation?.top_fact_words}
                            prediction={limePredictionLabel}
                            numSamples={
                                Number.isInteger(d.explanation?.num_samples) && d.explanation.num_samples > 0
                                    ? d.explanation.num_samples
                                    : undefined
                            }
                            // JANGAN kirim angka fiktif jika backend tidak menyediakan skor
                            confidenceScore={
                                typeof d.confidence_score === "number" && !isNaN(d.confidence_score)
                                    ? d.confidence_score
                                    : undefined
                            }
                        />
                    )}
                </div>
            ) : (
                <div className="bg-slate-50/50 border border-dashed border-slate-200 rounded-xl p-3 text-center space-y-2">
                    {limeLoading ? (
                        <p className="text-[11px] text-slate-500">
                            Menghitung penjelasan LIME. Proses ini dapat memakan waktu satu menit atau lebih...
                        </p>
                    ) : (
                        <>
                            <p className="text-[11px] text-slate-400">
                                {limeError
                                    ? limeError
                                    : d.explanation?.error
                                        ? `Gagal mengekstrak LIME: ${d.explanation.error}`
                                        : canExplain
                                            ? "Penjelasan kata (LIME) tidak dihitung otomatis agar hasil klasifikasi tampil lebih cepat."
                                            : "Atribusi LIME tidak tersedia untuk status ini."}
                            </p>
                            {canExplain && onRequestExplanation && (
                                <button
                                    type="button"
                                    onClick={onRequestExplanation}
                                    disabled={!canAct}
                                    className="text-xs font-semibold text-emerald-700 hover:text-emerald-800 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 rounded-xl border border-emerald-200/60 transition disabled:opacity-40"
                                >
                                    {limeError ? "Coba lagi" : "Tampilkan penjelasan"}
                                </button>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* LAPIS 4: PENAFIAN (DISCLAIMER) MANDATORI */}
            <DisclaimerBanner />

            {/* FOOTER TOMBOL AKSI */}
            {feedbackSuccess === feedbackId && feedbackId && canAct && (
                <p role="status" className="text-xs text-emerald-700">
                    Terima kasih! Umpan balik Anda telah dikirim.
                </p>
            )}
            <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <button
                        type="button"
                        disabled
                        title="Unduh PDF belum tersedia"
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-xl transition disabled:opacity-40"
                    >
                        <Download className="w-3.5 h-3.5" />
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
                    className="text-xs font-semibold text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 px-3 py-1.5 rounded-xl border border-rose-200/60 transition disabled:opacity-40"
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
    );
}
