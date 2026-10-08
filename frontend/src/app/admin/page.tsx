"use client";

import { useState } from "react";
import { useAdminDashboard } from "@/hooks/useAdminDashboard";
import {
    ShieldAlert,
    CheckCircle,
    Clock,
    Sliders,
    ArrowUpRight,
    Eye,
    Download,
    Activity,
    Users,
} from "lucide-react";
import Link from "next/link";

/* Gaya bersama: satu warna hijau (emerald) + netral slate */
const CARD = "bg-white border border-slate-200/80 rounded-3xl shadow-2xs";
const CHIP = "w-8 h-8 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center border border-emerald-100";
const LABEL = "text-[11px] font-bold text-slate-400 uppercase tracking-wider";
const PILL = "text-xs font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200/60";

type Period = "week" | "month" | "year";
type RegPoint = { label: string; count: number };

const PERIODS: { key: Period; label: string; sub: string }[] = [
    { key: "week", label: "Minggu", sub: "Pendaftar 7 hari terakhir" },
    { key: "month", label: "Bulan", sub: "Pendaftar per minggu bulan ini" },
    { key: "year", label: "Tahun", sub: "Pendaftar per bulan tahun ini" },
];

/** Data contoh, hanya dipakai bila backend belum mengirim `stats.registrations` */
const SAMPLE_REG: Record<Period, RegPoint[]> = {
    week: [
        { label: "Sen", count: 6 }, { label: "Sel", count: 9 }, { label: "Rab", count: 7 },
        { label: "Kam", count: 12 }, { label: "Jum", count: 15 }, { label: "Sab", count: 8 }, { label: "Min", count: 5 },
    ],
    month: [
        { label: "M1", count: 38 }, { label: "M2", count: 52 }, { label: "M3", count: 47 }, { label: "M4", count: 64 },
    ],
    year: [
        { label: "Jan", count: 120 }, { label: "Feb", count: 98 }, { label: "Mar", count: 143 }, { label: "Apr", count: 131 },
        { label: "Mei", count: 170 }, { label: "Jun", count: 156 }, { label: "Jul", count: 190 }, { label: "Agu", count: 178 },
        { label: "Sep", count: 205 }, { label: "Okt", count: 88 }, { label: "Nov", count: 0 }, { label: "Des", count: 0 },
    ],
};

export default function AdminDashboardPage() {
    const { stats, recentLogs, loading } = useAdminDashboard();

    /* ---------- Data turunan ---------- */
    const logs = recentLogs ?? [];
    const chrono = [...logs].reverse(); // lama -> baru

    // 2) Pendaftaran akun baru (filter dinamis)
    const [period, setPeriod] = useState<Period>("week");

    // Backend cukup mengirim: stats.registrations = { week: [...], month: [...], year: [...] }
    const apiReg = (stats as unknown as { registrations?: Partial<Record<Period, RegPoint[]>> }).registrations;
    const apiSeries = apiReg?.[period];
    const isSample = !apiSeries || apiSeries.length === 0;
    const series: RegPoint[] = isSample ? SAMPLE_REG[period] : apiSeries!;

    const maxReg = Math.max(...series.map((w) => w.count), 1);
    const totalReg = series.reduce((a, w) => a + w.count, 0);
    const lastReg = series.length ? series[series.length - 1].count : 0;
    const prevReg = series.length > 1 ? series[series.length - 2].count : 0;
    const regDelta = prevReg > 0 ? ((lastReg - prevReg) / prevReg) * 100 : 0;
    const dense = series.length > 8; // mode rapat untuk 12 bulan

    // Mini bar kartu hoaks (8 log terakhir)
    const miniBars = chrono.slice(-8);

    return (
        <div className="space-y-6 pb-6">

            {/* 1. HERO BANNER */}
            <div className="relative overflow-hidden bg-gradient-to-r from-emerald-950 via-emerald-900 to-emerald-800 rounded-3xl p-6 sm:p-8 text-white shadow-md border border-emerald-900/50">
                <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#6ee7b7_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none" />
                <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-emerald-400/20 blur-3xl pointer-events-none" />

                <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <div>
                        <span className="text-[11px] font-bold tracking-widest text-emerald-300 uppercase">
                            METRIK MONITORING GLOBAL
                        </span>
                        <div className="flex items-baseline gap-3 mt-1">
                            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight font-sans">
                                {stats.total_detections_today.toLocaleString("id-ID")}
                            </h2>
                            <span className="inline-flex items-center gap-0.5 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-white/10 text-emerald-200 border border-white/15">
                                <ArrowUpRight className="w-3.5 h-3.5" />
                                +{stats.total_detections_delta}% hari ini
                            </span>
                        </div>
                        <p className="text-xs text-emerald-100/70 mt-2 max-w-md leading-relaxed">
                            Total artikel dan tangkapan layar politik yang telah diverifikasi oleh korpus IndoBERT dan OCR.
                        </p>
                    </div>

                    <div className="flex items-center gap-3 self-start md:self-auto">
                        <Link
                            href="/admin/threshold"
                            className="flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold px-4 py-2.5 rounded-xl border border-white/15 backdrop-blur-xs transition"
                        >
                            <Sliders className="w-3.5 h-3.5 text-emerald-300" />
                            <span>Threshold: {stats.active_threshold.toFixed(2)}</span>
                        </Link>

                        <Link
                            href="/admin/export"
                            className="flex items-center gap-2 bg-emerald-400 hover:bg-emerald-300 text-emerald-950 text-xs font-bold px-4 py-2.5 rounded-xl transition shadow-lg shadow-emerald-950/30"
                        >
                            <Download className="w-3.5 h-3.5" />
                            <span>Ekspor Rekap</span>
                        </Link>
                    </div>
                </div>
            </div>

            {/* 2. TIGA KARTU METRIK */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

                {/* Hoaks Terdeteksi */}
                <div className={`${CARD} p-6 flex flex-col justify-between`}>
                    <div>
                        <div className="flex items-center justify-between pb-3">
                            <span className={LABEL}>HOAKS TERDETEKSI</span>
                            <div className={CHIP}><ShieldAlert className="w-4 h-4" /></div>
                        </div>
                        <div className="flex items-baseline gap-2 mt-1">
                            <h3 className="text-2xl font-bold text-slate-900 font-sans">{stats.hoax_detected_today}</h3>
                            <span className={PILL}>{stats.hoax_ratio_percent}% rasio</span>
                        </div>
                    </div>

                    <div className="mt-5 pt-4 border-t border-slate-100 flex items-end gap-1.5 h-10 box-content">
                        {(miniBars.length ? miniBars.map((l) => ({ h: Math.max(l.confidence_score * 100, 15), hoax: l.prediction === "HOAKS" }))
                            : [40, 65, 30, 85, 95, 45, 75, 60].map((h, i) => ({ h, hoax: i === 4 }))
                        ).map((b, i) => (
                            <div
                                key={i}
                                style={{ height: `${b.h}%` }}
                                className={`flex-1 rounded-sm transition-all duration-700 ${b.hoax ? "bg-emerald-700" : "bg-emerald-200"}`}
                            />
                        ))}
                    </div>
                </div>

                {/* Feedback */}
                <div className={`${CARD} p-6 flex flex-col justify-between`}>
                    <div>
                        <div className="flex items-center justify-between pb-3">
                            <span className={LABEL}>SANGGAHAN USER (FEEDBACK)</span>
                            <div className={CHIP}><Clock className="w-4 h-4" /></div>
                        </div>
                        <div className="flex items-baseline gap-2 mt-1">
                            <h3 className="text-2xl font-bold text-slate-900 font-sans">{stats.pending_feedbacks}</h3>
                            <span className={PILL}>Menunggu Review</span>
                        </div>
                    </div>

                    <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between text-xs">
                        <span className="text-slate-400">Kandidat Dataset Baru</span>
                        <Link href="/admin/feedback" className="font-bold text-emerald-700 hover:underline">
                            Kelola Sekarang →
                        </Link>
                    </div>
                </div>

                {/* Pengguna Aktif */}
                <div className={`${CARD} p-6 flex flex-col justify-between`}>
                    <div>
                        <div className="flex items-center justify-between pb-3">
                            <span className={LABEL}>PENGGUNA AKTIF SISTEM</span>
                            <div className={CHIP}><Activity className="w-4 h-4" /></div>
                        </div>
                        <div className="flex items-baseline gap-2 mt-1">
                            <h3 className="text-2xl font-bold text-slate-900 font-sans">{stats.active_users_count}</h3>
                            <span className={PILL}>Online</span>
                        </div>
                    </div>

                    <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                        <span>Beban Server: Optimal (0.38s/inf)</span>
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    </div>
                </div>
            </div>

            {/* 3. GRAFIK BARU */}
            <div className="grid grid-cols-1 gap-6">

                {/* Pendaftaran akun baru */}
                <div className={`${CARD} p-6`}>
                    <div className="flex flex-wrap items-start justify-between gap-4">
                        <div className="flex items-center gap-3">
                            <div className={CHIP}><Users className="w-4 h-4" /></div>
                            <div>
                                <h3 className="text-sm font-bold text-slate-900 leading-tight flex items-center gap-2">
                                    Pendaftaran Akun Baru
                                    {isSample && (
                                        <span className="text-[9px] font-bold uppercase tracking-wider text-slate-500 bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded-md">
                                            Contoh
                                        </span>
                                    )}
                                </h3>
                                <p className="text-xs text-slate-400 mt-0.5">{PERIODS.find((p) => p.key === period)?.sub}</p>
                            </div>
                        </div>

                        {/* Filter dinamis */}
                        <div className="inline-flex rounded-xl bg-emerald-50 p-1 border border-emerald-100">
                            {PERIODS.map((p) => (
                                <button
                                    key={p.key}
                                    type="button"
                                    onClick={() => setPeriod(p.key)}
                                    className={`px-3 py-1 text-[11px] font-bold rounded-lg transition ${period === p.key
                                        ? "bg-emerald-700 text-white shadow-sm"
                                        : "text-emerald-700 hover:bg-emerald-100"
                                        }`}
                                >
                                    {p.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Ringkasan */}
                    <div className="mt-4 flex flex-wrap items-baseline gap-3">
                        <p className="text-2xl font-extrabold text-slate-900 leading-none">{totalReg.toLocaleString("id-ID")}</p>
                        <span className="text-xs text-slate-400">akun baru</span>
                        <span className={`text-[11px] font-bold ${regDelta >= 0 ? "text-emerald-700" : "text-slate-500"}`}>
                            {regDelta >= 0 ? "▲" : "▼"} {Math.abs(regDelta).toFixed(1)}% vs periode sebelumnya
                        </span>
                    </div>

                    {/* Bar chart */}
                    <div className={`mt-5 flex items-end h-40 ${dense ? "gap-1.5" : "gap-3"}`}>
                        {series.map((w, i) => {
                            const isLast = i === series.length - 1;
                            return (
                                <div key={w.label} className="flex-1 h-full flex flex-col justify-end items-center gap-1.5 group">
                                    {!dense && <span className="text-[11px] font-bold text-slate-600">{w.count}</span>}
                                    <div
                                        title={`${w.label}: ${w.count} akun baru`}
                                        style={{ height: `${Math.max((w.count / maxReg) * 100, 6)}%` }}
                                        className={`w-full rounded-t-lg transition-all duration-700 ${isLast
                                            ? "bg-gradient-to-t from-emerald-700 to-emerald-500"
                                            : "bg-emerald-100 group-hover:bg-emerald-200"
                                            }`}
                                    />
                                    <span className="text-[10px] font-semibold text-slate-400">{w.label}</span>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* 4. TABEL LOG */}
            <div className={`${CARD} overflow-hidden`}>

                <div className="p-6 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                        <h3 className="text-base font-bold text-slate-900 leading-tight">Log Inferensi Terkini</h3>
                        <p className="text-xs text-slate-400 mt-0.5">Aktivitas deteksi masyarakat yang masuk secara real-time.</p>
                    </div>

                    <Link
                        href="/admin/logs"
                        className="px-3.5 py-1.5 text-xs font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-100 rounded-xl transition"
                    >
                        Lihat Semua Log
                    </Link>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                        <thead>
                            <tr className="border-b border-slate-100 bg-emerald-50/60 text-emerald-700 font-bold uppercase tracking-wider text-[10px]">
                                <th className="py-3.5 px-6">Identitas Pengguna</th>
                                <th className="py-3.5 px-6">Cuplikan Berita</th>
                                <th className="py-3.5 px-6">Sub-Topik</th>
                                <th className="py-3.5 px-6">Vonis IndoBERT</th>
                                <th className="py-3.5 px-6">Keyakinan</th>
                                <th className="py-3.5 px-6 text-right">Aksi</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {logs.length === 0 && (
                                <tr>
                                    <td colSpan={6} className="py-10 text-center text-slate-400">
                                        {loading ? "Memuat log..." : "Belum ada log inferensi."}
                                    </td>
                                </tr>
                            )}
                            {logs.map((log) => {
                                const isHoax = log.prediction === "HOAKS";
                                return (
                                    <tr key={log.id} className="hover:bg-emerald-50/50 transition">
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
                                                ? "bg-emerald-900 text-white"
                                                : "bg-emerald-50 text-emerald-700 border border-emerald-200/60"
                                                }`}>
                                                {isHoax ? <ShieldAlert className="w-3 h-3" /> : <CheckCircle className="w-3 h-3" />}
                                                {log.prediction}
                                            </span>
                                        </td>
                                        <td className="py-4 px-6">
                                            <div className="flex items-center gap-2.5">
                                                <span className="font-mono font-semibold text-slate-700 w-12">
                                                    {(log.confidence_score * 100).toFixed(1)}%
                                                </span>
                                                <div className="h-1.5 w-16 rounded-full bg-slate-100 overflow-hidden">
                                                    <div
                                                        className={`h-full rounded-full ${isHoax ? "bg-emerald-800" : "bg-emerald-400"}`}
                                                        style={{ width: `${Math.min(log.confidence_score * 100, 100)}%` }}
                                                    />
                                                </div>
                                            </div>
                                        </td>
                                        <td className="py-4 px-6 text-right whitespace-nowrap">
                                            <button
                                                type="button"
                                                onClick={() => alert(`Inspeksi Log: ${log.id}`)}
                                                className="p-1.5 text-slate-400 hover:text-emerald-800 hover:bg-emerald-50 rounded-lg transition"
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