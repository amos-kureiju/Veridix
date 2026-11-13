"use client";

import { FeedbackItem } from "@/types/detector";
import { Clock, CheckCircle2, ShieldAlert, CheckCircle } from "lucide-react";

interface FeedbackCardProps {
    item: FeedbackItem;
}

// 1. HELPER EKSPEKTASI LABEL (Anti Terbalik & Anti Substring Bug)
const isExactHoax = (label?: string | null): boolean => {
    const s = (label || "").trim().toUpperCase();
    return (s === "BERPOLA HOAKS" || s === "HOAKS" || s === "HOAX") && !s.includes("TIDAK");
};

const isExactFact = (label?: string | null): boolean => {
    const s = (label || "").trim().toUpperCase();
    return s === "TIDAK BERPOLA HOAKS" || s === "FAKTA" || s === "FACT";
};

export default function FeedbackCard({ item }: FeedbackCardProps) {
    // 2. STATUS BADGE JUJUR (Selaras dengan kurasi admin, bukan klaim retraining fiktif)
    const renderStatusBadge = (status: FeedbackItem["status"] | string) => {
        const normalized = (status || "").toUpperCase();
        switch (normalized) {
            case "RETRAINED":
                return (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-purple-50 text-purple-700 border border-purple-200/60 shadow-xs">
                        <CheckCircle2 className="w-3 h-3 text-purple-600" />
                        Disetujui untuk Korpus Latih
                    </span>
                );
            case "REVIEWED":
                return (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200/60 shadow-xs">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        Sudah Ditinjau
                    </span>
                );
            case "DISMISSED":
                return (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-slate-100 text-slate-600 border border-slate-200/60 shadow-xs">
                        Sanggahan Ditolak
                    </span>
                );
            case "PENDING":
                return (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200/60 shadow-xs">
                        <Clock className="w-3 h-3 text-amber-600" />
                        Menunggu Tinjauan
                    </span>
                );
            default:
                // PERBAIKAN: Tampilkan status netral jika nilai tidak dikenal
                return (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-slate-100 text-slate-500 border border-slate-200 shadow-xs">
                        Status: {status || "Tidak Diketahui"}
                    </span>
                );
        }
    };

    const isModelHoax = isExactHoax(item.model_verdict);
    const isModelFact = isExactFact(item.model_verdict);

    const isUserHoax = isExactHoax(item.user_claim);
    const isUserFact = isExactFact(item.user_claim);

    return (
        <div className="bg-white border border-slate-200/80 rounded-2xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.03)] hover:shadow-md transition-all space-y-4 font-sans">

            {/* 1. Header Kartu: ID Masukan, Waktu, dan Status Peninjauan */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2 text-xs">
                    <span className="font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded-lg border border-slate-200/60 font-mono">
                        #{item.id}
                    </span>
                    <span className="text-slate-300">•</span>
                    <span className="text-slate-400 text-[11px]">
                        {new Date(item.created_at).toLocaleDateString("id-ID", {
                            day: "numeric",
                            month: "long",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                        })} WIB
                    </span>
                </div>
                <div>
                    {renderStatusBadge(item.status)}
                </div>
            </div>

            {/* 2. Cuplikan Teks Berita yang Dikoreksi */}
            <div className="bg-[#f8fafc] border border-slate-200/70 rounded-xl p-3 text-xs text-slate-700 leading-relaxed">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                    Cuplikan Berita yang Dikoreksi:
                </span>
                <p className="italic text-slate-800">
                    "{item.news_snippet}"
                </p>
            </div>

            {/* 3. Komparasi Visual: Vonis Model vs Klaim Koreksi Pengguna (Grid Utuh) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                {/* Kolom Vonis IndoBERT */}
                <div className="bg-slate-50 border border-slate-200/60 rounded-xl p-3">
                    <span className="text-[10px] font-bold uppercase text-slate-400 block tracking-wider">
                        Vonis Awal IndoBERT:
                    </span>
                    <div className="flex items-center gap-1.5 mt-1">
                        {isModelHoax && <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />}
                        {isModelFact && <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />}
                        <span
                            className={`font-bold ${isModelHoax
                                    ? "text-rose-600"
                                    : isModelFact
                                        ? "text-emerald-600"
                                        : "text-amber-600"
                                }`}
                        >
                            {item.model_verdict}
                        </span>
                    </div>
                </div>

                {/* Kolom Koreksi User */}
                <div className="bg-slate-50/80 border border-slate-200/60 rounded-xl p-3">
                    <span className="text-[10px] font-bold uppercase text-slate-400 block tracking-wider">
                        Klaim Koreksi Anda:
                    </span>
                    <div className="flex items-center gap-1.5 mt-1">
                        <span className="font-bold text-slate-800">
                            Menurut Anda:{" "}
                            <span
                                className={`font-extrabold ${isUserHoax
                                        ? "text-rose-600"
                                        : isUserFact
                                            ? "text-emerald-600"
                                            : "text-amber-600"
                                    }`}
                            >
                                {item.user_claim}
                            </span>
                        </span>
                    </div>
                </div>
            </div>

            {/* 4. Catatan Sanggahan / Sumber Verifikasi Pengguna */}
            {item.user_note && (
                <div className="text-xs text-slate-600 bg-amber-50/40 border border-amber-200/50 rounded-xl p-3">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800 block mb-1">
                        Catatan Sanggahan / Bukti Klarifikasi Anda:
                    </span>
                    <p className="text-slate-700 leading-relaxed font-sans">
                        "{item.user_note}"
                    </p>
                </div>
            )}

        </div>
    );
}