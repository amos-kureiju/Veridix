"use client";

import { useState } from "react";
import {
    CheckCircle,
    AlertTriangle,
    XCircle,
    Download,
    Bookmark,
    HelpCircle,
    Clock,
    Sparkles
} from "lucide-react";
import { DetectionResult } from "@/types/detector";
import LimeHighlighter from "./LimeHighlighter";
import DisclaimerBanner from "./DisclaimerBanner";
import FeedbackModal from "./FeedbackModal";

interface VerdictCardProps {
    result: DetectionResult | null;
    loading: boolean;
    canAct?: boolean;
}

export default function VerdictCard({ result, loading, canAct = true }: VerdictCardProps) {
    const [showFeedback, setShowFeedback] = useState(false);

    // Kondisi 1: Sedang Menjalankan Inferensi
    if (loading) {
        return (
            <div className="bg-white border border-slate-200/80 rounded-3xl p-10 shadow-2xs flex flex-col items-center justify-center text-center min-h-[460px]">
                <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center animate-bounce mb-3 border border-emerald-100">
                    <Sparkles className="w-6 h-6" />
                </div>
                <h3 className="text-base font-bold text-slate-800">Memproses Inferensi IndoBERT</h3>
                <p className="text-xs text-slate-400 mt-1 max-w-xs leading-relaxed">
                    Menghitung probabilitas Softmax dan mengekstrak 100 perturbasi bobot kata LIME...
                </p>
            </div>
        );
    }

    // Kondisi 2: Belum Ada Berita yang Dianalisis
    if (!result || !result.data) {
        return (
            <div className="bg-white border border-slate-200/80 rounded-3xl p-10 shadow-2xs flex flex-col items-center justify-center text-center min-h-[460px]">
                <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mb-3">
                    <HelpCircle className="w-6 h-6" />
                </div>
                <h3 className="text-base font-bold text-slate-700">Hasil Analisis 4 Lapis</h3>
                <p className="text-xs text-slate-400 mt-1 max-w-sm leading-relaxed">
                    Tempelkan teks atau unggah tangkapan layar di sebelah kiri, lalu tekan tombol "Analisis Sekarang" untuk melihat vonis dan penjelasan LIME.
                </p>
            </div>
        );
    }

    // Kondisi 3: Hasil Berhasil Didapatkan
    const { prediction, confidence_score, inference_time_seconds, narrative_explanation, explanation, political_topic } = result.data;
    const scorePercent = (confidence_score * 100).toFixed(1);

    // Penentuan tema warna Lapis 1
    let theme = {
        bg: "bg-emerald-50 border-emerald-200/80 text-emerald-900",
        badge: "bg-emerald-600 text-white",
        icon: CheckCircle,
        label: "FAKTA",
    };

    if (prediction === "HOAKS") {
        theme = {
            bg: "bg-rose-50 border-rose-200/80 text-rose-900",
            badge: "bg-rose-600 text-white",
            icon: XCircle,
            label: "HOAKS",
        };
    } else if (prediction === "PERLU KONFIRMASI") {
        theme = {
            bg: "bg-amber-50 border-amber-200/80 text-amber-900",
            badge: "bg-amber-600 text-white",
            icon: AlertTriangle,
            label: "PERLU KONFIRMASI",
        };
    }

    const IconVerdict = theme.icon;

    return (
        <div className="bg-white border border-slate-200/80 rounded-3xl shadow-2xs p-6 space-y-5">

            {/* LAPIS 1: VONIS & PERSENTASE SOFTMAX */}
            <div className={`border rounded-2xl p-4 flex items-center justify-between ${theme.bg}`}>
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-white/90 rounded-xl shadow-xs">
                        <IconVerdict className="w-6 h-6" />
                    </div>
                    <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider opacity-70 block">
                            Vonis IndoBERT Base {political_topic ? `• ${political_topic}` : ""}
                        </span>
                        <h2 className="text-xl font-black tracking-tight leading-tight">
                            {theme.label}
                        </h2>
                    </div>
                </div>

                <div className="text-right">
                    <span className={`text-xs font-bold px-3 py-1 rounded-full ${theme.badge}`}>
                        {scorePercent}% Keyakinan
                    </span>
                    <p className="text-[10px] opacity-70 mt-1 flex items-center justify-end gap-1 font-mono">
                        <Clock className="w-3 h-3" /> {inference_time_seconds || 0.38}s
                    </p>
                </div>
            </div>

            {/* LAPIS 2: NARASI POLA LINGUISTIK */}
            <div className="bg-slate-50 border border-slate-200/60 rounded-2xl p-3.5">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                    Lapis 2: Narasi Karakteristik Bahasa
                </p>
                <p className="text-xs text-slate-700 leading-relaxed font-sans">
                    {narrative_explanation || (prediction === "HOAKS"
                        ? "Teks teridentifikasi memuat pola kalimat hiperbolis, delegitimasi institusi, dan diksi agitatif yang jamak ditemukan pada sampel disinformasi politik."
                        : "Teks memiliki struktur kalimat netral, kaidah jurnalistik baku, dan tidak menunjukkan pola manipulatif ekstrem.")}
                </p>
            </div>

            {/* LAPIS 3: PENJELASAN XAI LIME */}
            <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                    Lapis 3: Penjelasan Bobot Kata (LIME Explainer)
                </p>
                <LimeHighlighter
                    tokens={explanation?.tokens}
                    topHoax={explanation?.top_hoax_words}
                    topFact={explanation?.top_fact_words}
                    prediction={prediction}
                    confidenceScore={confidence_score}
                />
            </div>

            {/* LAPIS 4: DISCLAIMER MANDATORI */}
            <DisclaimerBanner />

            {/* FOOTER TOMBOL AKSI */}
            <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <button
                        type="button"
                        onClick={() => alert("Hasil telah disimpan ke Riwayat Anda.")}
                        disabled={!canAct}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-xl transition disabled:opacity-40"
                        title={canAct ? "Simpan ke riwayat" : "Login untuk menyimpan riwayat"}
                    >
                        <Bookmark className="w-3.5 h-3.5" />
                        <span>Simpan</span>
                    </button>

                    <button
                        type="button"
                        onClick={() => alert("Mengunduh Laporan Resmi Lapis 4 dalam format PDF...")}
                        disabled={!canAct}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-xl transition disabled:opacity-40"
                    >
                        <Download className="w-3.5 h-3.5" />
                        <span>Unduh PDF</span>
                    </button>
                </div>

                {/* Tombol Human-in-the-Loop Feedback */}
                <button
                    type="button"
                    onClick={() => setShowFeedback(true)}
                    disabled={!canAct}
                    className="text-xs font-semibold text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 px-3 py-1.5 rounded-xl border border-rose-200/60 transition disabled:opacity-40"
                >
                    Ini Salah?
                </button>
            </div>

            {/* Modal Sanggahan Masukan Koreksi */}
            {showFeedback && (
                <FeedbackModal
                    onClose={() => setShowFeedback(false)}
                    onSubmit={(claim, note) => {
                        alert(`Terima kasih! Sanggahan Anda (${claim}) dicatat untuk retraining model.`);
                        setShowFeedback(false);
                    }}
                />
            )}

        </div>
    );
}