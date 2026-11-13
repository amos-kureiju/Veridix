"use client";

import { useState, useEffect, useRef } from "react";
import { apiClient } from "@/lib/apiClient";
import { AdminFeedbackItem } from "@/types/admin";
import { Sparkles, Loader2, XCircle } from "lucide-react";

interface RetrainTableProps {
    initialItems?: AdminFeedbackItem[];
    onRefresh?: () => void;
}

// Gunakan status yang benar-benar didukung skema backend
type TabFilter = "PENDING" | "RETRAINED" | "REVIEWED" | "DISMISSED";

export default function RetrainTable({ initialItems = [], onRefresh }: RetrainTableProps) {
    const [activeTab, setActiveTab] = useState<TabFilter>("PENDING");
    const [items, setItems] = useState<AdminFeedbackItem[]>(initialItems);
    const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

    // 1. PENCEGAHAN RENDER BERULANG: Bandingkan JSON atau panjang array, jangan salin membabi-buta
    const prevItemsRef = useRef(initialItems);
    useEffect(() => {
        if (JSON.stringify(prevItemsRef.current) !== JSON.stringify(initialItems)) {
            prevItemsRef.current = initialItems;
            setItems(initialItems);
        }
    }, [initialItems]);

    const filtered = items.filter((i) => i.status === activeTab);

    // 2. KONTRAK RESMI BACKEND: review_status & admin_notes
    const handleReviewAction = async (
        id: string,
        reviewStatus: "RETRAINED" | "DISMISSED",
        notes: string
    ) => {
        setActionLoadingId(id);
        try {
            await apiClient.put(`/api/v1/feedback/${id}/review`, {
                review_status: reviewStatus,  // <-- SESUAI BACKEND
                admin_notes: notes            // <-- SESUAI BACKEND
            });

            // Perbarui state lokal
            setItems((prev) =>
                prev.map((item) => (item.id === id ? { ...item, status: reviewStatus } : item))
            );
            onRefresh?.();
        } catch (err: any) {
            alert(err.response?.data?.detail || "Gagal memperbarui status kurasi ke server.");
        } finally {
            setActionLoadingId(null);
        }
    };

    return (
        <div className="space-y-4">
            {/* Tab Switcher */}
            <div className="flex flex-wrap gap-2 p-1 bg-white border border-slate-200/80 rounded-2xl w-fit shadow-2xs">
                <button
                    type="button"
                    onClick={() => setActiveTab("PENDING")}
                    className={`px-4 py-2 rounded-xl text-xs font-bold transition cursor-pointer ${activeTab === "PENDING" ? "bg-[#0b2520] text-white shadow-xs" : "text-slate-500 hover:text-slate-800"
                        }`}
                >
                    Menunggu Tinjauan ({items.filter((i) => i.status === "PENDING").length})
                </button>

                <button
                    type="button"
                    onClick={() => setActiveTab("RETRAINED")}
                    className={`px-4 py-2 rounded-xl text-xs font-bold transition cursor-pointer ${activeTab === "RETRAINED" ? "bg-[#0b2520] text-white shadow-xs" : "text-slate-500 hover:text-slate-800"
                        }`}
                >
                    Disetujui untuk Korpus Latih ({items.filter((i) => i.status === "RETRAINED").length})
                </button>

                <button
                    type="button"
                    onClick={() => setActiveTab("REVIEWED")}
                    className={`px-4 py-2 rounded-xl text-xs font-bold transition cursor-pointer ${activeTab === "REVIEWED" ? "bg-[#0b2520] text-white shadow-xs" : "text-slate-500 hover:text-slate-800"
                        }`}
                >
                    Sudah Ditinjau ({items.filter(i => i.status === "REVIEWED").length})
                </button>

                <button
                    type="button"
                    onClick={() => setActiveTab("DISMISSED")}
                    className={`px-4 py-2 rounded-xl text-xs font-bold transition cursor-pointer ${activeTab === "DISMISSED" ? "bg-[#0b2520] text-white shadow-xs" : "text-slate-500 hover:text-slate-800"
                        }`}
                >
                    Ditolak ({items.filter((i) => i.status === "DISMISSED").length})
                </button>
            </div>

            {/* Tabel */}
            <div className="bg-white border border-slate-200/80 rounded-3xl shadow-2xs overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                        <thead>
                            <tr className="border-b border-slate-100 bg-[#f8fafc] text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                                <th className="py-3.5 px-6">ID Deteksi</th>
                                <th className="py-3.5 px-6">Cuplikan Teks</th>
                                <th className="py-3.5 px-6">Vonis Model</th>
                                <th className="py-3.5 px-6">Klaim User</th>
                                <th className="py-3.5 px-6">Catatan Sanggahan</th>
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
                                            <span className="text-[11px] text-slate-400 font-mono">{item.detection_id}</span>
                                        </td>
                                        <td className="py-4 px-6 max-w-xs truncate text-slate-700">
                                            "{item.news_snippet}"
                                        </td>
                                        <td className="py-4 px-6 font-bold whitespace-nowrap text-slate-700">
                                            {item.model_verdict}
                                        </td>
                                        <td className="py-4 px-6 font-bold whitespace-nowrap text-slate-700">
                                            Klaim: {item.user_claim}
                                        </td>
                                        <td className="py-4 px-6 max-w-xs text-slate-600 italic">
                                            {item.user_note || "Tidak ada catatan."}
                                        </td>
                                        <td className="py-4 px-6 text-right whitespace-nowrap">
                                            {item.status === "PENDING" && (
                                                <div className="flex items-center justify-end gap-1.5">
                                                    <button
                                                        type="button"
                                                        disabled={actionLoadingId === item.id}
                                                        onClick={() =>
                                                            handleReviewAction(
                                                                item.id,
                                                                "RETRAINED",
                                                                "Disetujui kurator admin untuk korpus retraining berikutnya."
                                                            )
                                                        }
                                                        className="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl text-xs transition cursor-pointer disabled:opacity-50"
                                                    >
                                                        {actionLoadingId === item.id ? (
                                                            <Loader2 className="w-3 h-3 animate-spin" />
                                                        ) : (
                                                            <Sparkles className="w-3 h-3" />
                                                        )}
                                                        <span>Setujui Korpus</span>
                                                    </button>
                                                    <button
                                                        type="button"
                                                        disabled={actionLoadingId === item.id}
                                                        onClick={() =>
                                                            handleReviewAction(
                                                                item.id,
                                                                "DISMISSED",
                                                                "Sanggahan dinilai tidak valid."
                                                            )
                                                        }
                                                        className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl text-xs transition font-semibold cursor-pointer disabled:opacity-50"
                                                    >
                                                        Tolak
                                                    </button>
                                                </div>
                                            )}
                                            {item.status === "RETRAINED" && (
                                                <span className="text-purple-700 font-bold text-[11px] bg-purple-50 px-2.5 py-1 rounded-full border border-purple-200">
                                                    Masuk Korpus Retraining
                                                </span>
                                            )}
                                            {item.status === "DISMISSED" && (
                                                <span className="text-slate-400 text-[11px]">Sanggahan Ditolak</span>
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