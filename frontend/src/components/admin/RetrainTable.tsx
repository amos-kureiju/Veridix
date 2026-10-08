"use client";

import { useState } from "react";
import { AdminFeedbackItem } from "@/types/admin";
import { CheckCircle2, XCircle, RefreshCw, Layers, Sparkles } from "lucide-react";

interface RetrainTableProps {
    initialItems?: AdminFeedbackItem[];
}

export default function RetrainTable({ initialItems = [] }: RetrainTableProps) {
    const [activeTab, setActiveTab] = useState<"PENDING" | "REVIEWED" | "RETRAINED">("PENDING");

    // Data simulasi feedback
    const [items, setItems] = useState<AdminFeedbackItem[]>([
        {
            id: "FB-881",
            detection_id: "DET-1102",
            user_email: "tony.robert@analisis.id",
            news_snippet: "KPU RI mengumumkan penetapan hasil pemungutan suara ulang serentak di distrik Papua...",
            model_verdict: "HOAKS",
            user_claim: "FAKTA",
            user_note: "KPU Pusat telah menggelar rilis pers resmi di YouTube pukul 14.00 WIB kemarin.",
            status: "PENDING",
            created_at: "2026-10-06T10:00:00Z",
        },
        {
            id: "FB-880",
            detection_id: "DET-1105",
            user_email: "claribel.sefira@mail.com",
            news_snippet: "Kementerian Keuangan merilis rincian pagu anggaran bansos darurat akhir tahun...",
            model_verdict: "PERLU KONFIRMASI",
            user_claim: "HOAKS",
            user_note: "Format nomor surat yang beredar di Telegram adalah edaran palsu bertanggal lampau.",
            status: "RETRAINED",
            created_at: "2026-10-05T12:00:00Z",
        },
    ]);

    const filtered = items.filter(i => i.status === activeTab);

    const handleMarkRetrain = (id: string) => {
        setItems(prev => prev.map(i => i.id === id ? { ...i, status: "RETRAINED" } : i));
        alert(`Feedback #${id} berhasil ditandai sebagai korpus retraining model IndoBERT.`);
    };

    const handleDismiss = (id: string) => {
        setItems(prev => prev.map(i => i.id === id ? { ...i, status: "REVIEWED" } : i));
    };

    return (
        <div className="space-y-4">
            {/* Tab Switcher */}
            <div className="flex gap-2 p-1 bg-white border border-slate-200/80 rounded-2xl w-fit shadow-2xs">
                <button
                    type="button"
                    onClick={() => setActiveTab("PENDING")}
                    className={`px-4 py-2 rounded-xl text-xs font-bold transition ${activeTab === "PENDING" ? "bg-[#0b2520] text-white shadow-xs" : "text-slate-500 hover:text-slate-800"
                        }`}
                >
                    Menunggu Tinjauan ({items.filter(i => i.status === "PENDING").length})
                </button>
                <button
                    type="button"
                    onClick={() => setActiveTab("RETRAINED")}
                    className={`px-4 py-2 rounded-xl text-xs font-bold transition ${activeTab === "RETRAINED" ? "bg-[#0b2520] text-white shadow-xs" : "text-slate-500 hover:text-slate-800"
                        }`}
                >
                    Ditandai untuk Retraining ({items.filter(i => i.status === "RETRAINED").length})
                </button>
                <button
                    type="button"
                    onClick={() => setActiveTab("REVIEWED")}
                    className={`px-4 py-2 rounded-xl text-xs font-bold transition ${activeTab === "REVIEWED" ? "bg-[#0b2520] text-white shadow-xs" : "text-slate-500 hover:text-slate-800"
                        }`}
                >
                    Sudah Ditinjau ({items.filter(i => i.status === "REVIEWED").length})
                </button>
            </div>

            {/* Tabel Feedback */}
            <div className="bg-white border border-slate-200/80 rounded-3xl shadow-2xs overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                        <thead>
                            <tr className="border-b border-slate-100 bg-[#f8fafc] text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                                <th className="py-3.5 px-6">Pelapor</th>
                                <th className="py-3.5 px-6">Cuplikan Teks</th>
                                <th className="py-3.5 px-6">Vonis Model</th>
                                <th className="py-3.5 px-6">Klaim User</th>
                                <th className="py-3.5 px-6">Catatan / Bukti Sanggahan</th>
                                <th className="py-3.5 px-6 text-right">Aksi Kurasi</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {filtered.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="text-center py-10 text-slate-400">
                                        Tidak ada antrean masukan pada tab ini.
                                    </td>
                                </tr>
                            ) : (
                                filtered.map((item) => (
                                    <tr key={item.id} className="hover:bg-slate-50/70 transition">
                                        <td className="py-4 px-6 whitespace-nowrap">
                                            <span className="font-bold text-slate-900 block font-mono">#{item.id}</span>
                                            <span className="text-[11px] text-slate-400">{item.user_email}</span>
                                        </td>
                                        <td className="py-4 px-6 max-w-xs truncate text-slate-700">
                                            "{item.news_snippet}"
                                        </td>
                                        <td className="py-4 px-6 font-bold text-rose-600 whitespace-nowrap">
                                            {item.model_verdict}
                                        </td>
                                        <td className="py-4 px-6 font-bold text-emerald-600 whitespace-nowrap">
                                            Menurut User: {item.user_claim}
                                        </td>
                                        <td className="py-4 px-6 max-w-xs text-slate-600 italic">
                                            {item.user_note || "Tidak ada catatan."}
                                        </td>
                                        <td className="py-4 px-6 text-right whitespace-nowrap">
                                            {item.status === "PENDING" && (
                                                <div className="flex items-center justify-end gap-1.5">
                                                    <button
                                                        type="button"
                                                        onClick={() => handleMarkRetrain(item.id)}
                                                        className="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl text-xs transition"
                                                    >
                                                        <Sparkles className="w-3 h-3" />
                                                        <span>Retraining</span>
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={() => handleDismiss(item.id)}
                                                        className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl text-xs transition font-semibold"
                                                    >
                                                        Abaikan
                                                    </button>
                                                </div>
                                            )}
                                            {item.status === "RETRAINED" && (
                                                <span className="text-emerald-700 font-bold text-[11px] bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
                                                    Masuk Antrean Dataset
                                                </span>
                                            )}
                                            {item.status === "REVIEWED" && (
                                                <span className="text-slate-400 text-[11px]">Selesai Ditinjau</span>
                                            )}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}