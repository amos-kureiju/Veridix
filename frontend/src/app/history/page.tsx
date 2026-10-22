"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { useHistory } from "@/hooks/useHistory";
import ConfirmDialog from "@/components/shared/ConfirmDialog";
import {
    Search,
    Download,
    Trash2,
    Eye,
    CheckCircle,
    XCircle,
    AlertTriangle,
    Lock,
    X,
    Loader2
} from "lucide-react";
import type { HistoryItem } from "@/types/detector";
import UserShell from "@/components/layout/UserShell";

export default function HistoryPage() {
    // 1. Panggil useHistory HANYA jika sesi sudah selesai diperiksa dan user sudah login
    const { user, ready, isGuest } = useAuth();
    const { items, loading, reload } = useHistory(ready && Boolean(user));

    // State Filter & Pencarian
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedVerdict, setSelectedVerdict] = useState("ALL");
    const [selectedTopic, setSelectedTopic] = useState("ALL");
    const [selectedTime, setSelectedTime] = useState("ALL");

    // State Modal Detail & Konfirmasi Hapus
    const [detailItem, setDetailItem] = useState<HistoryItem | null>(null);
    const [deleteId, setDeleteId] = useState<string | null>(null);

    // Data Dummy HANYA untuk Mode Tamu (Guest)
    const dummyHistory: HistoryItem[] = useMemo(() => [
        {
            id: "hist-demo-1",
            input_text: "KPU RI diklaim menetapkan sistem pemilu tertutup secara sepihak tanpa putusan resmi MK pada rapat tertutup kemarin malam.",
            full_text: "KPU RI diklaim menetapkan sistem pemilu tertutup secara sepihak tanpa putusan resmi MK pada rapat tertutup kemarin malam.",
            pattern_label: "BERPOLA HOAKS",
            prediction: "HOAKS",
            agreement_ratio: 0.94,
            confidence_score: 0.942,
            political_topic: "KPU & Pemilu",
            created_at: "2026-10-06T10:30:00Z",
        },
        {
            id: "hist-demo-2",
            input_text: "Presiden RI memimpin rapat terbatas mengenai penyaluran beras cadangan pemerintah di Istana Merdeka Jakarta bersama menteri terkait.",
            full_text: "Presiden RI memimpin rapat terbatas mengenai penyaluran beras cadangan pemerintah di Istana Merdeka Jakarta bersama menteri terkait.",
            pattern_label: "TIDAK BERPOLA HOAKS",
            prediction: "FAKTA",
            agreement_ratio: 0.88,
            confidence_score: 0.885,
            political_topic: "Kebijakan & Bansos",
            created_at: "2026-10-05T14:15:00Z",
        },
    ], []);

    // 2. Jika user login -> tampilkan data riil database (walaupun kosong []). Jika tamu -> tampilkan dummy.
    const displayItems = isGuest ? dummyHistory : items;

    // 3. Logika Filter (Aman dari undefined input_text)
    const filteredData = useMemo(() => {
        return displayItems.filter((item) => {
            const textContent = item.input_text || item.full_text || "";
            const topic = item.political_topic || "";
            const label = item.pattern_label || item.prediction || "";

            const matchSearch = textContent.toLowerCase().includes(searchTerm.toLowerCase()) ||
                topic.toLowerCase().includes(searchTerm.toLowerCase());

            const matchVerdict = selectedVerdict === "ALL" ||
                label.toUpperCase().includes(selectedVerdict.toUpperCase()) ||
                (selectedVerdict === "HOAKS" && label.includes("HOAKS")) ||
                (selectedVerdict === "FAKTA" && label.includes("TIDAK BERPOLA"));

            const matchTopic = selectedTopic === "ALL" || topic.toLowerCase().includes(selectedTopic.toLowerCase());

            return matchSearch && matchVerdict && matchTopic;
        });
    }, [displayItems, searchTerm, selectedVerdict, selectedTopic]);

    // Fungsi Ekspor CSV
    const handleExportCSV = () => {
        if (filteredData.length === 0) {
            alert("Tidak ada data riwayat untuk diekspor.");
            return;
        }
        const headers = ["ID", "Teks Berita", "Vonis Pola", "Skor Konsensus", "Topik", "Tanggal"];
        const rows = filteredData.map(d => [
            d.id,
            `"${(d.input_text || d.full_text || "").replace(/"/g, '""')}"`,
            d.pattern_label || d.prediction || "-",
            `${(((d.agreement_ratio ?? d.confidence_score) || 0) * 100).toFixed(1)}%`,
            `"${d.political_topic}"`,
            new Date(d.created_at).toLocaleString("id-ID")
        ]);
        const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `riwayat-deteksi-${new Date().toISOString().slice(0, 10)}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handleDeleteConfirm = () => {
        if (!deleteId) return;
        alert(`Entri riwayat ${deleteId} berhasil dihapus.`);
        setDeleteId(null);
    };

    return (
        <UserShell
            guest={isGuest}
            userName={user?.name}
            userRole={user?.role}
            onLogout={reload}
        >
            <div className="flex justify-end pb-2">
                <button
                    type="button"
                    onClick={handleExportCSV}
                    className="flex items-center gap-2 bg-[#0b2520] hover:bg-[#133730] text-white text-xs font-semibold px-4 py-2 rounded-xl shadow-xs transition"
                >
                    <span>Ekspor CSV</span>
                    <Download className="w-3.5 h-3.5" />
                </button>
            </div>

            {/* JIKA USER BERSTATUS TAMU (GUEST BANNER) */}
            {isGuest && (
                <div className="bg-amber-50/80 border border-amber-200 rounded-2xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-amber-100 rounded-xl text-amber-700">
                            <Lock className="w-4 h-4" />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-amber-900">Mode Tamu Aktif</p>
                            <p className="text-[11px] text-amber-700 mt-0.5">
                                Riwayat di bawah adalah data pratinjau demo. Masuk atau daftar akun agar setiap deteksi Anda tersimpan permanen di cloud.
                            </p>
                        </div>
                    </div>
                    <Link
                        href="/auth/login"
                        className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs rounded-xl transition shadow-xs shrink-0"
                    >
                        Masuk Akun
                    </Link>
                </div>
            )}

            {/* BARIS FILTER & PENCARIAN */}
            <div className="bg-white border border-slate-200/80 rounded-2xl p-4 shadow-[0_1px_3px_rgba(0,0,0,0.03)] space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                    <div className="relative md:col-span-1">
                        <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            type="text"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            placeholder="Cari kata kunci..."
                            className="w-full bg-[#f8fafc] border border-slate-200 pl-8 pr-3 py-2 rounded-xl text-xs text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition"
                        />
                    </div>

                    <div>
                        <select
                            value={selectedVerdict}
                            onChange={(e) => setSelectedVerdict(e.target.value)}
                            className="w-full bg-[#f8fafc] border border-slate-200 px-3 py-2 rounded-xl text-xs text-slate-700 focus:outline-none focus:border-emerald-500 transition"
                        >
                            <option value="ALL">Semua Vonis Pola</option>
                            <option value="HOAKS">Berpola Hoaks</option>
                            <option value="FAKTA">Tidak Berpola Hoaks</option>
                            <option value="PERLU KONFIRMASI">Perlu Konfirmasi</option>
                        </select>
                    </div>

                    <div>
                        <select
                            value={selectedTopic}
                            onChange={(e) => setSelectedTopic(e.target.value)}
                            className="w-full bg-[#f8fafc] border border-slate-200 px-3 py-2 rounded-xl text-xs text-slate-700 focus:outline-none focus:border-emerald-500 transition"
                        >
                            <option value="ALL">Semua Sub-Topik</option>
                            <option value="KPU">KPU & Pemilu</option>
                            <option value="DPR">DPR & Parlemen</option>
                            <option value="Kebijakan">Kebijakan & Bansos</option>
                            <option value="Pilpres">Pilpres / Pemilu</option>
                        </select>
                    </div>

                    <div>
                        <select
                            value={selectedTime}
                            onChange={(e) => setSelectedTime(e.target.value)}
                            className="w-full bg-[#f8fafc] border border-slate-200 px-3 py-2 rounded-xl text-xs text-slate-700 focus:outline-none focus:border-emerald-500 transition"
                        >
                            <option value="ALL">Semua Waktu</option>
                            <option value="TODAY">Hari Ini</option>
                            <option value="7DAYS">7 Hari Terakhir</option>
                            <option value="30DAYS">30 Hari Terakhir</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* TABEL DATA RIWAYAT */}
            <div className="bg-white border border-slate-200/80 rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.03)] overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                        <thead>
                            <tr className="border-b border-slate-100 bg-[#f8fafc]/80 text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                                <th className="py-3 px-4">Teks Naskah</th>
                                <th className="py-3 px-4">Sub-Topik</th>
                                <th className="py-3 px-4">Indikasi Pola</th>
                                <th className="py-3 px-4">Konsensus AI</th>
                                <th className="py-3 px-4">Waktu</th>
                                <th className="py-3 px-4 text-right">Aksi</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {loading ? (
                                <tr>
                                    <td colSpan={6} className="text-center py-12 text-slate-400">
                                        <div className="flex items-center justify-center gap-2">
                                            <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />
                                            <span>Memuat riwayat deteksi dari cloud...</span>
                                        </div>
                                    </td>
                                </tr>
                            ) : filteredData.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="text-center py-12 text-slate-400">
                                        Belum ada riwayat analisis berita. Naskah yang Anda analisis di beranda akan tersimpan otomatis di sini.
                                    </td>
                                </tr>
                            ) : (
                                filteredData.map((item) => {
                                    const label = item.pattern_label || item.prediction || "DINILAI";
                                    const isHoax = label.includes("HOAKS");
                                    const isFact = label.includes("FAKTA") || label.includes("TIDAK BERPOLA");
                                    const ratio = item.agreement_ratio ?? item.confidence_score ?? 0;

                                    return (
                                        <tr key={item.id} className="hover:bg-slate-50/60 transition group">
                                            <td className="py-3.5 px-4 font-medium text-slate-800 max-w-xs md:max-w-md truncate">
                                                {item.input_text || item.full_text}
                                            </td>

                                            <td className="py-3.5 px-4">
                                                <span className="inline-block bg-slate-100 text-slate-600 px-2.5 py-0.5 rounded-lg text-[11px] font-medium border border-slate-200/60">
                                                    {item.political_topic}
                                                </span>
                                            </td>

                                            <td className="py-3.5 px-4">
                                                <span
                                                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold ${isHoax
                                                        ? "bg-rose-50 text-rose-600 border border-rose-200/60"
                                                        : isFact
                                                            ? "bg-emerald-50 text-emerald-600 border border-emerald-200/60"
                                                            : "bg-amber-50 text-amber-600 border border-amber-200/60"
                                                        }`}
                                                >
                                                    {isHoax && <XCircle className="w-3.5 h-3.5" />}
                                                    {isFact && <CheckCircle className="w-3.5 h-3.5" />}
                                                    {!isHoax && !isFact && <AlertTriangle className="w-3.5 h-3.5" />}
                                                    {label}
                                                </span>
                                            </td>

                                            <td className="py-3.5 px-4 font-mono font-semibold text-slate-700">
                                                {(ratio * 100).toFixed(1)}%
                                            </td>

                                            <td className="py-3.5 px-4 text-slate-400 text-[11px] whitespace-nowrap">
                                                {new Date(item.created_at).toLocaleDateString("id-ID", {
                                                    day: "numeric",
                                                    month: "short",
                                                    year: "numeric",
                                                })}
                                            </td>

                                            <td className="py-3.5 px-4 text-right whitespace-nowrap">
                                                <div className="flex items-center justify-end gap-1">
                                                    <button
                                                        type="button"
                                                        onClick={() => setDetailItem(item)}
                                                        className="p-1.5 text-slate-400 hover:text-emerald-700 hover:bg-emerald-50 rounded-lg transition"
                                                        title="Lihat Detail Hasil"
                                                    >
                                                        <Eye className="w-4 h-4" />
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={() => setDeleteId(item.id)}
                                                        className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                                                        title="Hapus Riwayat"
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>

                <div className="py-3 px-4 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                    <span>Menampilkan {filteredData.length} entri riwayat</span>
                    <span>VERIDIX History Audit</span>
                </div>
            </div>

            {/* MODAL LIHAT DETAIL RIWAYAT LENGKAP */}
            {detailItem && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
                    <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4 animate-in fade-in zoom-in-95">
                        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                            <div>
                                <span className="text-[10px] font-bold uppercase text-slate-400">Detail Riwayat #{detailItem.id.slice(0, 8)}</span>
                                <h3 className="text-base font-bold text-slate-800">{detailItem.political_topic}</h3>
                            </div>
                            <button
                                type="button"
                                onClick={() => setDetailItem(null)}
                                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="space-y-3 text-xs">
                            <div>
                                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Teks Berita:</label>
                                <p className="bg-slate-50 p-3 rounded-xl text-slate-700 leading-relaxed border border-slate-200/60 max-h-40 overflow-y-auto">
                                    {detailItem.input_text || detailItem.full_text}
                                </p>
                            </div>

                            <div className="grid grid-cols-2 gap-3 pt-1">
                                <div className="bg-[#f8fafc] p-2.5 rounded-xl border border-slate-200/60">
                                    <span className="text-[10px] text-slate-400 block font-semibold uppercase">Pola Terdeteksi:</span>
                                    <span className="text-xs font-bold text-slate-800">{detailItem.pattern_label || detailItem.prediction}</span>
                                </div>
                                <div className="bg-[#f8fafc] p-2.5 rounded-xl border border-slate-200/60">
                                    <span className="text-[10px] text-slate-400 block font-semibold uppercase">Konsensus Model:</span>
                                    <span className="text-xs font-bold text-slate-800 font-mono">
                                        {(((detailItem.agreement_ratio ?? detailItem.confidence_score) || 0) * 100).toFixed(1)}%
                                    </span>
                                </div>
                            </div>

                            {/* Tampilkan Status Feedback Admin jika Ada */}
                            {detailItem.feedback && (
                                <div className="bg-emerald-50/70 border border-emerald-100 p-3 rounded-xl">
                                    <span className="text-[10px] font-bold uppercase text-emerald-800 block">Status Sanggahan User:</span>
                                    <div className="mt-1 flex items-center justify-between">
                                        <span className="font-semibold text-emerald-900">
                                            Status: {detailItem.feedback.review_status || "PENDING"}
                                        </span>
                                    </div>
                                    {detailItem.feedback.admin_notes && (
                                        <p className="mt-1 text-slate-600 text-[11px]">
                                            Catatan Admin: {detailItem.feedback.admin_notes}
                                        </p>
                                    )}
                                </div>
                            )}
                        </div>

                        <div className="pt-3 border-t border-slate-100 flex justify-end">
                            <button
                                type="button"
                                onClick={() => setDetailItem(null)}
                                className="px-4 py-2 bg-[#0b2520] hover:bg-[#133730] text-white font-semibold text-xs rounded-xl transition"
                            >
                                Tutup
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <ConfirmDialog
                open={!!deleteId}
                title="Hapus Riwayat Deteksi?"
                description="Apakah Anda yakin ingin menghapus data analisis ini? Tindakan ini tidak dapat dibatalkan."
                confirmLabel="Ya, Hapus"
                cancelLabel="Batal"
                onConfirm={handleDeleteConfirm}
                onCancel={() => setDeleteId(null)}
            />
        </UserShell>
    );
}