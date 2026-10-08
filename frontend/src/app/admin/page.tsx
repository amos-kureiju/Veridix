"use client";

import { useAdminDashboard } from "@/hooks/useAdminDashboard";
import {
    ShieldAlert,
    CheckCircle,
    Clock,
    Sliders,
    ArrowUpRight,
    Eye,
    Filter,
    Download,
    Activity,
    Layers
} from "lucide-react";
import Link from "next/link";

export default function AdminDashboardPage() {
    const { stats, recentLogs, loading } = useAdminDashboard();

    return (
        <div className="space-y-6 pb-6">

            {/* 1. HERO BANNER GLOBAL (GAYA CAZURA OVERVIEW) */}
            <div className="relative overflow-hidden bg-gradient-to-r from-emerald-950 via-[#0b2520] to-slate-900 rounded-3xl p-6 sm:p-8 text-white shadow-md border border-emerald-900/50">

                {/* Latar Belakang Garis Halus */}
                <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#10b981_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none" />

                <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <div>
                        <span className="text-[11px] font-bold tracking-widest text-emerald-400 uppercase">
                            METRIK MONITORING GLOBAL
                        </span>
                        <div className="flex items-baseline gap-3 mt-1">
                            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight font-sans">
                                {stats.total_detections_today.toLocaleString("id-ID")}
                            </h2>
                            <span className="inline-flex items-center gap-0.5 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
                                <ArrowUpRight className="w-3.5 h-3.5" />
                                +{stats.total_detections_delta}% hari ini
                            </span>
                        </div>
                        <p className="text-xs text-emerald-200/70 mt-2 max-w-md leading-relaxed">
                            Total artikel dan tangkapan layar politik yang telah diverifikasi oleh korpus IndoBERT dan OCR.
                        </p>
                    </div>

                    <div className="flex items-center gap-3 self-start md:self-auto">
                        <Link
                            href="/admin/threshold"
                            className="flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold px-4 py-2.5 rounded-xl border border-white/15 backdrop-blur-xs transition"
                        >
                            <Sliders className="w-3.5 h-3.5 text-emerald-400" />
                            <span>Threshold: {stats.active_threshold.toFixed(2)}</span>
                        </Link>

                        <Link
                            href="/admin/export"
                            className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold px-4 py-2.5 rounded-xl transition shadow-lg shadow-emerald-500/20"
                        >
                            <Download className="w-3.5 h-3.5" />
                            <span>Ekspor Rekap</span>
                        </Link>
                    </div>
                </div>
            </div>

            {/* 2. TIGA KARTU METRIK DENGAN MINI CHART (ALA CAZURA INCOMES & EXPENSES) */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

                {/* Kartu 1: Hoaks Terdeteksi */}
                <div className="bg-white border border-slate-200/80 rounded-3xl p-6 shadow-2xs flex flex-col justify-between">
                    <div>
                        <div className="flex items-center justify-between pb-3">
                            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                                HOAKS TERDETEKSI
                            </span>
                            <div className="w-8 h-8 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center border border-rose-100">
                                <ShieldAlert className="w-4 h-4" />
                            </div>
                        </div>

                        <div className="flex items-baseline gap-2 mt-1">
                            <h3 className="text-2xl font-bold text-slate-900 font-sans">{stats.hoax_detected_today}</h3>
                            <span className="text-xs font-bold text-rose-600 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200/60">
                                {stats.hoax_ratio_percent}% rasio
                            </span>
                        </div>
                    </div>

                    {/* Mini Bar Visualizer */}
                    <div className="mt-5 pt-4 border-t border-slate-100 flex items-end gap-1.5 h-10">
                        {[40, 65, 30, 85, 95, 45, 75, 60].map((h, i) => (
                            <div
                                key={i}
                                style={{ height: `${h}%` }}
                                className={`flex-1 rounded-sm ${i === 4 ? "bg-rose-500" : "bg-rose-100"}`}
                            />
                        ))}
                    </div>
                </div>

                {/* Kartu 2: Masukan Menunggu Tinjauan (Active Learning) */}
                <div className="bg-white border border-slate-200/80 rounded-3xl p-6 shadow-2xs flex flex-col justify-between">
                    <div>
                        <div className="flex items-center justify-between pb-3">
                            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                                SANGGAHAN USER (FEEDBACK)
                            </span>
                            <div className="w-8 h-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center border border-amber-100">
                                <Clock className="w-4 h-4" />
                            </div>
                        </div>

                        <div className="flex items-baseline gap-2 mt-1">
                            <h3 className="text-2xl font-bold text-slate-900 font-sans">{stats.pending_feedbacks}</h3>
                            <span className="text-xs font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200/60">
                                Menunggu Review
                            </span>
                        </div>
                    </div>

                    <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between text-xs">
                        <span className="text-slate-400">Kandidat Dataset Baru</span>
                        <Link href="/admin/feedback" className="font-bold text-emerald-700 hover:underline">
                            Kelola Sekarang →
                        </Link>
                    </div>
                </div>

                {/* Kartu 3: Pengguna Aktif & Kapasitas Sesi */}
                <div className="bg-white border border-slate-200/80 rounded-3xl p-6 shadow-2xs flex flex-col justify-between">
                    <div>
                        <div className="flex items-center justify-between pb-3">
                            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                                PENGGUNA AKTIF SISTEM
                            </span>
                            <div className="w-8 h-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-100">
                                <Activity className="w-4 h-4" />
                            </div>
                        </div>

                        <div className="flex items-baseline gap-2 mt-1">
                            <h3 className="text-2xl font-bold text-slate-900 font-sans">{stats.active_users_count}</h3>
                            <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200/60">
                                Online
                            </span>
                        </div>
                    </div>

                    <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                        <span>Beban Server: Optimal (0.38s/inf)</span>
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    </div>
                </div>

            </div>

            {/* 3. TABEL 10 LOG TERKINI (ALA RECENT TRANSACTIONS CAZURA) */}
            <div className="bg-white border border-slate-200/80 rounded-3xl shadow-2xs overflow-hidden">

                {/* Header Tabel */}
                <div className="p-6 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                        <h3 className="text-base font-bold text-slate-900 leading-tight">Log Inferensi Terkini</h3>
                        <p className="text-xs text-slate-400 mt-0.5">Aktivitas deteksi masyarakat yang masuk secara real-time.</p>
                    </div>

                    <div className="flex items-center gap-2">
                        <Link
                            href="/admin/logs"
                            className="px-3.5 py-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200/70 rounded-xl transition"
                        >
                            Lihat Semua Log
                        </Link>
                    </div>
                </div>

                {/* Tabel Data */}
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                        <thead>
                            <tr className="border-b border-slate-100 bg-[#f8fafc] text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                                <th className="py-3.5 px-6">Identitas Pengguna</th>
                                <th className="py-3.5 px-6">Cuplikan Berita</th>
                                <th className="py-3.5 px-6">Sub-Topik</th>
                                <th className="py-3.5 px-6">Vonis IndoBERT</th>
                                <th className="py-3.5 px-6">Keyakinan</th>
                                <th className="py-3.5 px-6 text-right">Aksi</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {recentLogs.map((log) => {
                                const isHoax = log.prediction === "HOAKS";
                                return (
                                    <tr key={log.id} className="hover:bg-slate-50/70 transition">
                                        <td className="py-4 px-6 font-mono text-slate-600 whitespace-nowrap">
                                            {log.user_identifier}
                                        </td>
                                        <td className="py-4 px-6 font-medium text-slate-800 max-w-xs truncate">
                                            {log.text_snippet}
                                        </td>
                                        <td className="py-4 px-6">
                                            <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded-lg text-[11px] font-medium border border-slate-200">
                                                {log.political_topic}
                                            </span>
                                        </td>
                                        <td className="py-4 px-6">
                                            <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold ${isHoax
                                                    ? "bg-rose-50 text-rose-600 border border-rose-200/60"
                                                    : "bg-emerald-50 text-emerald-600 border border-emerald-200/60"
                                                }`}>
                                                {isHoax ? <ShieldAlert className="w-3 h-3" /> : <CheckCircle className="w-3 h-3" />}
                                                {log.prediction}
                                            </span>
                                        </td>
                                        <td className="py-4 px-6 font-mono font-semibold text-slate-700">
                                            {(log.confidence_score * 100).toFixed(1)}%
                                        </td>
                                        <td className="py-4 px-6 text-right whitespace-nowrap">
                                            <button
                                                type="button"
                                                onClick={() => alert(`Inspeksi Log: ${log.id}`)}
                                                className="p-1.5 text-slate-400 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition"
                                                title="Inspeksi LIME"
                                            >
                                                <Eye className="w-4 h-4" />
                                            </button>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>

            </div>

        </div>
    );
}