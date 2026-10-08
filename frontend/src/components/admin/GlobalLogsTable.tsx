" use client";

import { useState, useMemo } from "react";
import { AdminLogItem } from "@/types/admin";
import {
    Search,
    Filter,
    Download,
    Eye,
    ShieldAlert,
    CheckCircle,
    AlertTriangle,
    Clock,
    X,
    Layers,
    Sparkles,
} from "lucide-react";

interface GlobalLogsTableProps {
    logs: AdminLogItem[];
}

export default function GlobalLogsTable({ logs }: GlobalLogsTableProps) {
    const [search, setSearch] = useState("");
    const [verdictFilter, setVerdictFilter] = useState("ALL");
    const [topicFilter, setTopicFilter] = useState("ALL");
    const [selectedLog, setSelectedLog] = useState<AdminLogItem | null>(null);

    const filteredLogs = useMemo(() => {
        return logs.filter((item) => {
            const matchSearch = item.user_identifier.toLowerCase().includes(search.toLowerCase()) ||
                item.text_snippet.toLowerCase().includes(search.toLowerCase());
            const matchVerdict = verdictFilter === "ALL" || item.prediction === verdictFilter;
            const matchTopic = topicFilter === "ALL" || item.political_topic.toLowerCase().includes(topicFilter.toLowerCase());
            return matchSearch && matchVerdict && matchTopic;
        });
    }, [logs, search, verdictFilter, topicFilter]);

    const handleExportCSV = () => {
        const headers = ["ID", "User Identifier", "Cuplikan Teks", "Topik", "Vonis", "Confidence", "Waktu"];
        const rows = filteredLogs.map(l => [
            l.id,
            `"${l.user_identifier}"`,
            `"${l.text_snippet.replace(/"/g, '""')}"`,
            `"${l.political_topic}"`,
            l.prediction,
            `${(l.confidence_score * 100).toFixed(1)}%`,
            l.created_at
        ]);
        const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `veridix-global-logs-${new Date().toISOString().slice(0, 10)}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    return (
        <div className="space-y-4">
            {/* Baris Filter & Ekspor */}
            <div className="bg-white border border-slate-200/80 rounded-2xl p-4 shadow-2xs flex flex-col md:flex-row gap-3 items-center justify-between">
                <div className="flex flex-1 flex-col sm:flex-row gap-2 w-full">
                    <div className="relative flex-1">
                        <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            type="text"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            placeholder="Cari email, IP tamu, atau isi teks..."
                            className="w-full bg-[#f8fafc] border border-slate-200 pl-8 pr-3 py-2 rounded-xl text-xs focus:outline-none focus:border-slate-400"
                        />
                    </div>

                    <select
                        value={verdictFilter}
                        onChange={(e) => setVerdictFilter(e.target.value)}
                        className="bg-[#f8fafc] border border-slate-200 px-3 py-2 rounded-xl text-xs text-slate-700 focus:outline-none"
                    >
                        <option value="ALL">Semua Vonis</option>
                        <option value="HOAKS">Vonis: HOAKS</option>
                        <option value="FAKTA">Vonis: FAKTA</option>
                        <option value="PERLU KONFIRMASI">Vonis: PERLU KONFIRMASI</option>
                    </select>

                    <select
                        value={topicFilter}
                        onChange={(e) => setTopicFilter(e.target.value)}
                        className="bg-[#f8fafc] border border-slate-200 px-3 py-2 rounded-xl text-xs text-slate-700 focus:outline-none"
                    >
                        <option value="ALL">Semua Sub-Topik</option>
                        <option value="KPU">KPU & Pemilu</option>
                        <option value="DPR">DPR & Parlemen</option>
                        <option value="Kebijakan">Kebijakan & Bansos</option>
                    </select>
                </div>

                <button
                    type="button"
                    onClick={handleExportCSV}
                    className="flex items-center gap-1.5 px-4 py-2 bg-[#0b2520] hover:bg-[#133730] text-white font-semibold text-xs rounded-xl transition shrink-0"
                >
                    <Download className="w-3.5 h-3.5" />
                    <span>Ekspor CSV</span>
                </button>
            </div>

            {/* Tabel Data Log */}
            <div className="bg-white border border-slate-200/80 rounded-3xl shadow-2xs overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                        <thead>
                            <tr className="border-b border-slate-100 bg-[#f8fafc] text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                                <th className="py-3.5 px-6">ID & Identitas User</th>
                                <th className="py-3.5 px-6">Cuplikan Teks</th>
                                <th className="py-3.5 px-6">Sub-Topik</th>
                                <th className="py-3.5 px-6">Vonis IndoBERT</th>
                                <th className="py-3.5 px-6">Confidence</th>
                                <th className="py-3.5 px-6">Latency</th>
                                <th className="py-3.5 px-6 text-right">Inspeksi</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {filteredLogs.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="text-center py-10 text-slate-400">
                                        Tidak ada log inferensi yang sesuai dengan kriteria filter.
                                    </td>
                                </tr>
                            ) : (
                                filteredLogs.map((log) => {
                                    const isHoax = log.prediction === "HOAKS";
                                    const isFact = log.prediction === "FAKTA";
                                    return (
                                        <tr key={log.id} className="hover:bg-slate-50/70 transition">
                                            <td className="py-3.5 px-6 whitespace-nowrap">
                                                <span className="font-bold text-slate-800 font-mono block">#{log.id}</span>
                                                <span className="text-[11px] text-slate-400">{log.user_identifier}</span>
                                            </td>
                                            <td className="py-3.5 px-6 max-w-xs font-medium text-slate-700 truncate">
                                                {log.text_snippet}
                                            </td>
                                            <td className="py-3.5 px-6">
                                                <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded-lg text-[11px] font-medium border border-slate-200">
                                                    {log.political_topic}
                                                </span>
                                            </td>
                                            <td className="py-3.5 px-6 whitespace-nowrap">
                                                <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold ${isHoax ? "bg-rose-50 text-rose-600 border border-rose-200/60" :
                                                        isFact ? "bg-emerald-50 text-emerald-600 border border-emerald-200/60" :
                                                            "bg-amber-50 text-amber-700 border border-amber-200/60"
                                                    }`}>
                                                    {isHoax && <ShieldAlert className="w-3 h-3" />}
                                                    {isFact && <CheckCircle className="w-3 h-3" />}
                                                    {!isHoax && !isFact && <AlertTriangle className="w-3 h-3" />}
                                                    {log.prediction}
                                                </span>
                                            </td>
                                            <td className="py-3.5 px-6 font-mono font-bold text-slate-800">
                                                {(log.confidence_score * 100).toFixed(1)}%
                                            </td>
                                            <td className="py-3.5 px-6 font-mono text-slate-400 text-[11px]">
                                                {log.inference_time || 0.38}s
                                            </td>
                                            <td className="py-3.5 px-6 text-right whitespace-nowrap">
                                                <button
                                                    type="button"
                                                    onClick={() => setSelectedLog(log)}
                                                    className="p-1.5 text-slate-400 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition"
                                                    title="Inspeksi Teknis LIME"
                                                >
                                                    <Eye className="w-4 h-4" />
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Modal Detail Inspeksi Teknis LIME */}
            {selectedLog && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
                    <div className="bg-white rounded-3xl max-w-xl w-full p-6 shadow-2xl border border-slate-200 space-y-4 animate-in fade-in zoom-in-95">
                        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                            <div className="flex items-center gap-2">
                                <Layers className="w-4 h-4 text-emerald-600" />
                                <h3 className="text-sm font-bold text-slate-900">Inspeksi Teknis Inferensi #{selectedLog.id}</h3>
                            </div>
                            <button type="button" onClick={() => setSelectedLog(null)} className="text-slate-400 hover:text-slate-700">
                                <X className="w-4 h-4" />
                            </button>
                        </div>

                        <div className="space-y-3 text-xs">
                            <div>
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">User Identifier:</span>
                                <p className="font-mono bg-slate-50 p-2 rounded-xl text-slate-700">{selectedLog.user_identifier}</p>
                            </div>

                            <div>
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Masukan Teks Penuh:</span>
                                <p className="bg-[#f8fafc] p-3 rounded-xl text-slate-800 leading-relaxed max-h-36 overflow-y-auto border border-slate-200/60">
                                    {selectedLog.full_text || selectedLog.text_snippet}
                                </p>
                            </div>

                            <div className="grid grid-cols-2 gap-3 pt-1">
                                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/60">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase block">Vonis Klasifikasi:</span>
                                    <span className="text-xs font-bold text-slate-900 mt-0.5 block">{selectedLog.prediction}</span>
                                </div>
                                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/60">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase block">Skor Softmax:</span>
                                    <span className="text-xs font-bold text-slate-900 font-mono mt-0.5 block">{(selectedLog.confidence_score * 100).toFixed(2)}%</span>
                                </div>
                            </div>
                        </div>

                        <div className="pt-2 flex justify-end">
                            <button
                                type="button"
                                onClick={() => setSelectedLog(null)}
                                className="px-4 py-2 bg-[#0b2520] text-white rounded-xl text-xs font-semibold"
                            >
                                Tutup Inspeksi
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}